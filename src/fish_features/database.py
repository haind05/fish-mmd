import json
import os
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb

GROUPS = ("glcm", "ulbp", "geometry", "contour_profile", "fourier", "hsv", "color_moments", "spatial_hsv")


def connect():
    return psycopg.connect(os.environ.get("DATABASE_URL", "postgresql://fish:fish_local@127.0.0.1:5433/fish_features"), connect_timeout=10)


def initialize(schema):
    with connect() as conn:
        conn.execute(Path(schema).read_text(encoding="utf-8"))


def load_file(path):
    path = Path(path)
    config = json.loads((path.parent / "config.json").read_text(encoding="utf-8"))
    from .config import Config
    obj = Config(**config["parameters"])
    if obj.config_id != config["config_id"] or obj.dimensions != config["dimensions"]:
        raise ValueError("Config manifest khong hop le")
    count = 0
    # Mot transaction cho toan bo dot nap: loi se rollback, khong nap nua chung.
    with connect() as conn:
        conn.execute("INSERT INTO extraction_configs(config_id,parameters,dimensions) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                     (obj.config_id, Jsonb(obj.as_dict()), Jsonb(obj.dimensions)))
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                r = json.loads(line)
                if r["config_id"] != obj.config_id:
                    raise ValueError("Config cua ban ghi khong khop")
                row = conn.execute("""INSERT INTO images(relative_path,sha256,pixel_sha256,width,height,species_code,species_name,source_image_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(relative_path) DO UPDATE SET
                    sha256=excluded.sha256,pixel_sha256=excluded.pixel_sha256,width=excluded.width,height=excluded.height,
                    species_code=excluded.species_code,species_name=excluded.species_name,
                    source_image_id=excluded.source_image_id,updated_at=now() RETURNING image_id""",
                    tuple(r[k] for k in ("path","sha256","pixel_sha256","width","height","species_code","species_name","source_image_id"))).fetchone()
                # Anh doi noi dung thi moi dac trung cu cua anh nay deu het hieu luc.
                conn.execute("DELETE FROM image_features WHERE image_id=%s AND source_sha256<>%s", (row[0], r["sha256"]))
                conn.execute("""INSERT INTO image_features(image_id,config_id,source_sha256,glcm,ulbp,geometry,contour_profile,fourier,hsv,color_moments,spatial_hsv,metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(image_id,config_id) DO UPDATE SET
                    source_sha256=excluded.source_sha256,glcm=excluded.glcm,ulbp=excluded.ulbp,
                    geometry=excluded.geometry,contour_profile=excluded.contour_profile,fourier=excluded.fourier,
                    hsv=excluded.hsv,color_moments=excluded.color_moments,spatial_hsv=excluded.spatial_hsv,
                    metadata=excluded.metadata,extracted_at=now()""",
                    (row[0], obj.config_id, r["sha256"], *(r["features"][k] for k in GROUPS), Jsonb(r["metadata"])))
                count += 1
    return count


def stats():
    with connect() as conn:
        images, species = conn.execute("SELECT count(*),count(DISTINCT species_code) FROM images").fetchone()
        sets = conn.execute("SELECT config_id,count(*) FROM feature_catalog GROUP BY config_id").fetchall()
        return {"images": images, "species": species, "feature_sets": dict(sets)}


def inspect_image(relative_path):
    with connect() as conn:
        from psycopg.rows import dict_row
        conn.row_factory = dict_row
        return conn.execute("""SELECT i.relative_path,f.* FROM images i JOIN image_features f USING(image_id)
                              WHERE i.relative_path=%s AND i.sha256=f.source_sha256""", (relative_path,)).fetchall()
