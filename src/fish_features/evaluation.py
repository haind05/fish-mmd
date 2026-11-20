"""Danh gia holdout; khong fit scaler tren query, khong chon trong so bang test."""
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import time
import numpy as np
from .database import GROUPS
from .retrieval import Index, fetch_records, fingerprint, read_profile


def split_records(records, seed=42):
    by_species = defaultdict(list)
    for r in records:
        if r["species_code"] is None:
            raise ValueError("Danh gia can nhan species_code")
        by_species[r["species_code"]].append(r)
    rng = np.random.default_rng(seed)
    gallery, validation, test = [], [], []
    for label in sorted(by_species):
        members = sorted(by_species[label], key=lambda r: r["path"])
        order = rng.permutation(len(members))
        ordered = [members[int(i)] for i in order]
        if len(ordered) >= 3:
            test.append(ordered[0]); validation.append(ordered[1]); gallery.extend(ordered[2:])
        elif len(ordered) == 2:
            test.append(ordered[0]); gallery.append(ordered[1])
        else:
            gallery.extend(ordered)
    return sorted(gallery, key=lambda r: r["path"]), validation, test


def metrics(relevance, relevant_count, k=5):
    relevance = np.asarray(relevance[:k], dtype=float)
    hits = int(relevance.sum())
    positions = np.arange(1, len(relevance)+1)
    precisions = np.cumsum(relevance)/positions
    ideal = np.sum(1/np.log2(np.arange(1, min(relevant_count, k)+1)+1))
    return {"precision_at_5": hits/k, "recall_at_5": hits/relevant_count if relevant_count else 0,
        "hit_at_5": float(hits > 0),
        "ap_at_5": float(np.sum(precisions*relevance)/min(relevant_count, k)) if relevant_count else 0,
        "ndcg_at_5": float(np.sum(relevance/np.log2(positions+1))/ideal) if ideal else 0}


def weights(color, shape, texture):
    return {"hsv": color*.5, "spatial_hsv": color*.375, "color_moments": color*.125,
        "geometry": shape/3, "fourier": shape*.5, "contour_profile": shape/6,
        "glcm": texture*.5, "ulbp": texture*.5}


def candidate_profiles():
    return {name: weights(c, s, t) for name, c, s, t in [
        ("color_only", 1, 0, 0), ("shape_only", 0, 1, 0), ("texture_only", 0, 0, 1),
        ("balanced", 1/3, 1/3, 1/3), ("base_40_30_30", .4, .3, .3),
        ("color_60", .6, .2, .2), ("shape_60", .2, .6, .2), ("texture_60", .2, .2, .6) ]}


def assess(index, queries, candidates):
    aggregates = {name: [] for name in candidates}
    details = {name: [] for name in candidates}
    for q in queries:
        ds, _ = index.distances(q)
        mask = np.array([r["pixel_sha256"] != q["pixel_sha256"] for r in index.records])
        allowed = np.flatnonzero(mask)
        relevant_count = sum(r["species_code"] == q["species_code"] and bool(mask[i]) for i, r in enumerate(index.records))
        if relevant_count == 0:
            continue
        for name, ws in candidates.items():
            distance = sum(ws[k]*ds[k] for k in GROUPS)
            order = allowed[np.argsort(distance[allowed], kind="stable")][:5]
            relevance = [index.records[i]["species_code"] == q["species_code"] for i in order]
            m = metrics(relevance, relevant_count)
            aggregates[name].append(m)
            details[name].append({"query": q["path"], "species_code": q["species_code"],
                "relevant_in_gallery": relevant_count, **m,
                "top5": [{"path": index.records[i]["path"], "relevant": bool(rel), "distance": float(distance[i])}
                         for i, rel in zip(order, relevance)]})
    summaries = {}
    for name, values in aggregates.items():
        summaries[name] = {"queries": len(values), **({key: float(np.mean([m[key] for m in values])) for key in values[0]} if values else {})}
    return summaries, details


def evaluate(output="outputs/evaluation", profile_path=None):
    start = time.perf_counter()
    profile = read_profile(profile_path)
    records, config = fetch_records(profile["feature_config_id"])
    gallery, validation, test = split_records(records)
    if not validation or not test or len(gallery) < 5:
        raise ValueError("Khong du gallery/validation/test de danh gia")
    index = Index(gallery, config)
    candidates = candidate_profiles()
    validation_metrics, validation_details = assess(index, validation, candidates)
    # max giu thu tu candidate khi bang diem; chi dung validation.
    selected = max(candidates, key=lambda key: validation_metrics[key]["ap_at_5"])
    test_candidates = {"selected": candidates[selected], **{k: candidates[k] for k in ("color_only", "shape_only", "texture_only", "balanced")}}
    test_metrics, test_details = assess(index, test, test_candidates)
    selected_profile = deepcopy(profile)
    selected_profile["weights"] = candidates[selected]
    selected_profile["selection"] = {"method": "max_validation_map_at_5", "candidate": selected, "seed": 42,
        "dataset_fingerprint": fingerprint(records, config.config_id)}
    counts = Counter(r["species_code"] for r in records)
    # Gia lap loai chua co trong gallery: bo tat ca anh cung ma loai.
    unseen_examples = []
    for q in test[:3]:
        unseen_index = Index([r for r in gallery if r["species_code"] != q["species_code"]], config)
        result = unseen_index.rank(q, selected_profile)
        unseen_examples.append({"query": q["path"], "held_out_species": q["species_code"],
            "gallery_count": len(unseen_index.records),
            "results": [{k: r[k] for k in ("path", "distance", "similarity")} for r in result["results"]]})
    report = {"protocol": "species_stratified_holdout_v1", "seed": 42, "relevance": "same species_code from filename (proxy for visual similarity)",
        "feature_config_id": config.config_id, "feature_config": config.as_dict(),
        "dataset_fingerprint": fingerprint(records, config.config_id),
        "split_counts": {"all": len(records), "gallery": len(gallery), "validation": len(validation), "test": len(test),
            "species": len(counts), "singleton_species_gallery_only": sum(n == 1 for n in counts.values())},
        "selection_metric": "validation mean AP@5, denominator min(relevant_in_gallery,5)",
        "candidate_weights": candidates, "validation": validation_metrics, "selected_candidate": selected,
        "selected_profile": selected_profile, "test": test_metrics,
        "gallery_normalizers": index.scalers,
        "unseen_species_examples": unseen_examples,
        "seconds": round(time.perf_counter()-start, 3)}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in {"summary.json": report, "selected_profile.json": selected_profile,
        "splits.json": {"gallery": [r["path"] for r in gallery], "validation": [r["path"] for r in validation], "test": [r["path"] for r in test]},
        "validation_queries.json": validation_details, "test_queries.json": test_details}.items():
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report
