"""Chay voi RUN_DB_TESTS=1 sau db-init; moi test rollback du lieu tam."""
import os
import numpy as np
import psycopg
import pytest
from psycopg.types.json import Jsonb
from fish_features.config import Config
from fish_features.database import connect, GROUPS

pytestmark = pytest.mark.skipif(os.environ.get("RUN_DB_TESTS") != "1", reason="Can PostgreSQL Docker + RUN_DB_TESTS=1")


@pytest.fixture
def database():
    conn = connect()
    config = Config(algorithm_version="integration-test")
    conn.execute("INSERT INTO extraction_configs(config_id,parameters,dimensions) VALUES (%s,%s,%s)",
                 (config.config_id, Jsonb(config.as_dict()), Jsonb(config.dimensions)))
    image_id = conn.execute("""INSERT INTO images(relative_path,sha256,pixel_sha256,width,height)
        VALUES ('__integration_test__.png',%s,%s,640,320) RETURNING image_id""", ("a"*64, "b"*64)).fetchone()[0]
    yield conn, config, image_id
    conn.rollback()
    conn.close()


def insert_features(conn, config, image_id, override=None):
    values = {k: np.zeros(config.dimensions[k]).tolist() for k in GROUPS}
    values.update(override or {})
    conn.execute("""INSERT INTO image_features(image_id,config_id,source_sha256,glcm,ulbp,geometry,
        contour_profile,fourier,hsv,color_moments,spatial_hsv,metadata)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (image_id, config.config_id, "a"*64, *(values[k] for k in GROUPS), Jsonb({})))


@pytest.mark.parametrize("invalid", [[0.0], [0.0]*58+[float("nan")], [0.0]*58+[None]])
def test_sql_rejects_invalid_vector(database, invalid):
    conn, config, image_id = database
    with pytest.raises(psycopg.errors.RaiseException):
        insert_features(conn, config, image_id, {"ulbp": invalid})


def test_foreign_key_and_cascade(database):
    conn, config, image_id = database
    insert_features(conn, config, image_id)
    assert conn.execute("SELECT count(*) FROM image_features WHERE image_id=%s", (image_id,)).fetchone()[0] == 1
    conn.execute("DELETE FROM images WHERE image_id=%s", (image_id,))
    assert conn.execute("SELECT count(*) FROM image_features WHERE image_id=%s", (image_id,)).fetchone()[0] == 0
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insert_features(conn, config, image_id)
