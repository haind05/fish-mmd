import cv2
import numpy as np
import pytest
from fish_features.config import Config
from fish_features.texture import glcm_features, glcm_properties, circular_lbp, uniform_lut
from fish_features.preprocessing import segment
from fish_features.shape import shape_features, resample_contour
from fish_features.color import color_features, color_moments


def test_glcm_report_example():
    # Bang 4, trang 16: (0,1),(1,2),(2,3),(3,0), moi cap 1/4.
    p = np.zeros((4, 4))
    p[np.arange(4), [1, 2, 3, 0]] = .25
    np.testing.assert_allclose(glcm_properties(p), [.25, 3, .4, -.2, 2])


def test_glcm_excludes_background_pairs():
    gray = np.array([[0, 0, 255], [0, 0, 255]], dtype=np.uint8)
    mask = np.array([[1, 1, 0], [1, 1, 0]], dtype=np.uint8)
    values, counts = glcm_features(gray, mask, Config(glcm_offsets=((0, 1),)))
    np.testing.assert_allclose(values, [1, 0, 1, 1, 0])
    assert counts == [2]


def test_lbp_uniform_mapping_and_constant_patch():
    lut = uniform_lut()
    assert len(set(lut.tolist())) == 59
    assert np.count_nonzero(lut == 58) == 198
    gray = np.full((7, 7), 80, dtype=np.uint8)
    hist, raw, n = circular_lbp(gray, np.ones_like(gray))
    assert n == 25
    assert raw[255] == 1 and hist[lut[255]] == 1


def test_lbp_bilinear_known_patch():
    # R=1: cac diem cheo dung noi suy, khong lam tron toa do.
    gray = np.array([[0, 20, 0], [36, 60, 94], [0, 118, 0]], dtype=np.uint8)
    _, raw, n = circular_lbp(gray, np.ones_like(gray))
    assert n == 1
    # Cheo tren-phai ~28.76; duoi-phai ~49.05 <60.
    # Chi ben phai (94) va ben duoi (118) >=60.
    assert raw[1+64] == 1


def test_segmentation_fills_hole_and_discards_noise():
    image = np.full((30, 40, 3), 255, dtype=np.uint8)
    image[5:25, 5:35] = 20
    image[10:15, 10:15] = 255
    image[1, 1] = 0
    mask, _, bbox, _, _ = segment(image, 245)
    assert mask.sum() == 600 and bbox == (5, 5, 30, 20)
    with pytest.raises(ValueError):
        segment(np.full_like(image, 255), 245)


def test_geometry_raster_area_and_profile():
    mask = np.zeros((40, 60), np.uint8)
    mask[10:30, 5:55] = 1
    contour = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0][0]
    geo, profile, fd, _, meta = shape_features(mask, contour, (5, 10, 50, 20), Config())
    np.testing.assert_allclose(geo, [2.5, 1, 1])
    assert meta["area"] == 1000 and np.isclose(profile.mean(), 1)
    assert len(fd) == 10 and np.isfinite(fd).all()
    a = resample_contour(contour, 256)
    b = resample_contour(np.roll(contour[::-1], 13, axis=0), 256)
    np.testing.assert_allclose(a, b)


def test_color_order_signed_cube_root_and_spatial_coverage():
    # Phan bo lech am: 3 pixel sang + 1 pixel toi.
    pixels = np.array([[255, 0, 0]]*3 + [[0, 0, 0]], dtype=np.uint8)
    moments = color_moments(pixels)
    assert moments[0] == .75 and moments[6] < 0
    image = np.full((20, 30, 3), (0, 0, 255), dtype=np.uint8)
    mask = np.ones((20, 30), dtype=np.uint8)
    hsv, cm, spatial, counts = color_features(image, mask, (0, 0, 30, 20), Config())
    assert np.argmax(hsv) == 15  # H=0, S=3, V=3.
    assert cm[0] == 1 and cm[2] == 0  # RGB, khong phai BGR.
    assert sum(counts) == mask.sum()
    np.testing.assert_allclose(spatial.reshape(6, 192).sum(axis=1), 1)


def test_empty_spatial_cells_are_zero_not_nan():
    image = np.full((20, 30, 3), 128, dtype=np.uint8)
    mask = np.zeros((20, 30), np.uint8)
    mask[1, 1] = 1
    _, _, spatial, counts = color_features(image, mask, (0, 0, 30, 20), Config())
    assert counts.count(0) == 5 and np.isfinite(spatial).all()


def test_config_identity_survives_json_roundtrip():
    import json
    c = Config()
    restored = Config(**json.loads(json.dumps(c.as_dict())))
    assert c.config_id == restored.config_id
