"""CBIR: khoang cach tung nhom, chuan hoa gallery, xep hang co giai thich."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import numpy as np
from psycopg.rows import dict_row
from .config import Config
from .database import GROUPS, connect

PROFILE_PATH = Path(__file__).with_name("retrieval_profile.json")
STANDARDIZED = ("glcm", "geometry", "fourier", "color_moments")


def read_profile(path=None):
    profile = json.loads(Path(path or PROFILE_PATH).read_text(encoding="utf-8"))
    weights = profile["weights"]
    if set(weights) != set(GROUPS) or not all(np.isfinite(v) and v >= 0 for v in weights.values()):
        raise ValueError("Trong so phai huu han, khong am va du 8 nhom")
    if not np.isclose(sum(weights.values()), 1):
        raise ValueError("Tong trong so phai bang 1")
    if profile["top_k"] != 5 or profile["normalization"] != "gallery_population_std_rms_then_r_over_1_plus_r":
        raise ValueError("Cau hinh truy hoi khong duoc ho tro")
    return profile


def fetch_records(config_id):
    with connect() as conn:
        conn.row_factory = dict_row
        config_row = conn.execute("SELECT parameters FROM extraction_configs WHERE config_id=%s", (config_id,)).fetchone()
        if not config_row:
            raise ValueError("Chua co cau hinh dac trung trong CSDL; hay chay db-load")
        records = conn.execute("""SELECT i.image_id,i.relative_path AS path,i.species_code,i.species_name,
            i.pixel_sha256,i.sha256,f.glcm,f.ulbp,f.geometry,f.contour_profile,f.fourier,f.hsv,
            f.color_moments,f.spatial_hsv,f.metadata FROM images i JOIN image_features f USING(image_id)
            WHERE f.config_id=%s AND f.source_sha256=i.sha256 ORDER BY i.relative_path""", (config_id,)).fetchall()
    for record in records:
        record["features"] = {k: record.pop(k) for k in GROUPS}
    config = Config(**config_row["parameters"])
    if config.config_id != config_id:
        raise ValueError("Ma cau hinh khong khop tham so")
    return records, config


def fingerprint(records, config_id):
    value = [(r["path"], r["sha256"]) for r in records]
    return hashlib.sha256(json.dumps([config_id, value], sort_keys=True).encode()).hexdigest()


class Index:
    def __init__(self, records, config):
        if not records:
            raise ValueError("Gallery chua co dac trung")
        self.records, self.config = records, config
        self.fingerprint = fingerprint(records, config.config_id)
        self.arrays = {k: np.asarray([r["features"][k] for r in records], dtype=float) for k in GROUPS}
        for k, a in self.arrays.items():
            if a.shape != (len(records), config.dimensions[k]) or not np.isfinite(a).all():
                raise ValueError(f"Gallery co vector {k} khong hop le")
        self.scalers = {}
        for k in STANDARDIZED:
            a = self.arrays[k]
            std = a.std(axis=0, ddof=0)
            self.scalers[k] = {"mean": a.mean(axis=0).tolist(), "std": np.where(std < 1e-8, 1, std).tolist()}

    def distances(self, query):
        vectors = query["features"]
        result = {}
        raw = {}
        for key in GROUPS:
            q = np.asarray(vectors[key], dtype=float)
            if q.shape != (self.config.dimensions[key],) or not np.isfinite(q).all():
                raise ValueError(f"Query co vector {key} khong hop le")
            a = self.arrays[key]
            if key in ("hsv", "ulbp"):
                d = hellinger(a, q)
            elif key == "spatial_hsv":
                bins = self.config.dimensions["hsv"]
                aa, qq = a.reshape(len(a), -1, bins), q.reshape(-1, bins)
                valid_a, valid_q = aa.sum(axis=2) > 0, qq.sum(axis=1) > 0
                both = valid_a & valid_q
                union = valid_a | valid_q
                per_region = np.where(both, hellinger(aa, qq), 1.0)
                d = (per_region*union).sum(axis=1) / np.maximum(union.sum(axis=1), 1)
                d = np.where(union.any(axis=1), d, 1.0)
            else:
                delta = a-q
                if key in STANDARDIZED:
                    delta /= np.asarray(self.scalers[key]["std"])
                rms = np.sqrt(np.mean(delta**2, axis=1))
                raw[key] = rms
                d = rms/(1+rms)
            result[key] = np.clip(d, 0, 1)
        return result, raw

    def rank(self, query, profile):
        distances, raw = self.distances(query)
        score = sum(profile["weights"][k]*distances[k] for k in GROUPS)
        candidates = np.ones(len(self.records), dtype=bool)
        if profile.get("exclude_identical_pixels", True):
            candidates &= np.array([r["pixel_sha256"] != query["pixel_sha256"] for r in self.records])
        indices = np.flatnonzero(candidates)
        # self.records da sap xep path: stable sort de ket qua lap lai khi bang diem.
        indices = indices[np.argsort(score[indices], kind="stable")][:profile["top_k"]]
        results = []
        for rank, i in enumerate(indices, 1):
            record = self.records[i]
            components = {k: {"distance": float(distances[k][i]), "weight": profile["weights"][k],
                "contribution": float(profile["weights"][k]*distances[k][i]),
                **({"raw_rms": float(raw[k][i])} if k in raw else {})} for k in GROUPS}
            results.append({"rank": rank, "image_id": record["image_id"], "path": record["path"],
                "species_name": record["species_name"], "distance": float(score[i]),
                "similarity": float(1-score[i]), "components": components,
                "features": record["features"], "metadata": record["metadata"]})
        return {"results": results, "candidate_count": int(candidates.sum()),
                "excluded_identical": int((~candidates).sum())}


def hellinger(a, b):
    # Euclidean cua sqrt(hist)/sqrt(2), on dinh hon sqrt(1-affinity) khi gan 0.
    return np.sqrt(np.sum((np.sqrt(np.maximum(a, 0))-np.sqrt(np.maximum(b, 0)))**2, axis=-1)/2)


@lru_cache(maxsize=2)
def _cached_index(config_id, revision):
    return Index(*fetch_records(config_id))


def database_index(config_id):
    with connect() as conn:
        revision = conn.execute("""SELECT count(*),max(f.extracted_at),max(i.updated_at) FROM image_features f
            JOIN images i USING(image_id) WHERE f.config_id=%s AND f.source_sha256=i.sha256""", (config_id,)).fetchone()
    return _cached_index(config_id, revision)
