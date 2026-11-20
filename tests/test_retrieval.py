from copy import deepcopy
import cv2
import numpy as np
import pytest
from fish_features.config import Config
from fish_features.database import GROUPS
from fish_features.evaluation import metrics, split_records
from fish_features.extractor import extract_array
from fish_features.query import prepare_image
from fish_features.retrieval import Index, hellinger, read_profile


def records(count=7):
    c = Config()
    rows = []
    for i in range(count):
        f = {k: np.zeros(d).tolist() for k, d in c.dimensions.items()}
        f['hsv'][i % 192] = 1
        f['ulbp'][i % 59] = 1
        f['spatial_hsv'] = np.tile(f['hsv'], 6).tolist()
        f['geometry'] = [float(i+1), .5, .4]
        f['fourier'] = [i*.1]*10
        f['glcm'] = [i*.1]*20
        rows.append(dict(image_id=i, path=f'{i:02}.png', species_code=i//3,
            species_name='test', pixel_sha256=str(i), sha256=str(i), features=f, metadata={}))
    return rows, c


def test_hellinger_identical_and_disjoint():
    assert hellinger(np.array([1., 0]), np.array([1., 0])) == 0
    assert hellinger(np.array([1., 0]), np.array([0., 1])) == 1
    assert 0 < hellinger(np.array([.5, .5]), np.array([1., 0])) < 1


def test_self_is_zero_and_query_does_not_change_scalers():
    rows, config = records()
    index = Index(rows, config)
    previous = deepcopy(index.scalers)
    distances, _ = index.distances(rows[0])
    assert all(d[0] == 0 for d in distances.values())
    outlier = deepcopy(rows[0]); outlier['features']['geometry'][0] = 1e6
    index.distances(outlier)
    assert index.scalers == previous
    assert index.scalers['geometry']['std'][1] == 1


def test_rank_excludes_same_pixels_and_contributions_sum():
    rows, config = records()
    index = Index(rows, config)
    output = index.rank(rows[0], read_profile())
    assert len(output['results']) == 5
    assert output['excluded_identical'] == 1
    assert all(r['image_id'] != 0 for r in output['results'])
    distances = [r['distance'] for r in output['results']]
    assert distances == sorted(distances)
    for r in output['results']:
        assert np.isclose(sum(v['contribution'] for v in r['components'].values()), r['distance'])
        assert np.isclose(r['similarity'], 1-r['distance'])


def test_ranking_does_not_use_species_labels():
    rows, config = records()
    original = Index(rows, config).rank(rows[0], read_profile())
    for r in rows:
        r['species_code'] = 999
    changed = Index(rows, config).rank(rows[0], read_profile())
    assert [r['path'] for r in original['results']] == [r['path'] for r in changed['results']]


def test_spatial_empty_regions_skip_both_empty_and_penalize_one_empty():
    rows, config = records()
    # Chi vung dau co pixel trong gallery; query chi vung thu 2 co pixel.
    rows[0]['features']['spatial_hsv'] = [0.]*1152
    rows[0]['features']['spatial_hsv'][0] = 1
    query = deepcopy(rows[0])
    query['features']['spatial_hsv'] = [0.]*1152
    query['features']['spatial_hsv'][192] = 1
    ds, _ = Index(rows, config).distances(query)
    assert ds['spatial_hsv'][0] == 1
    query['features']['spatial_hsv'] = rows[0]['features']['spatial_hsv']
    ds, _ = Index(rows, config).distances(query)
    assert ds['spatial_hsv'][0] == 0


def test_holdout_split_is_disjoint_reproducible_and_has_relevant_gallery():
    rows, _ = records(10)
    a = split_records(rows)
    b = split_records(rows)
    assert a == b
    sets = [{r['path'] for r in subset} for subset in a]
    assert not sets[0] & sets[1] and not sets[0] & sets[2] and not sets[1] & sets[2]
    assert len(set.union(*sets)) == 10
    assert all(any(q['species_code'] == g['species_code'] for g in a[0]) for q in a[1]+a[2])


def test_metrics_hand_calculation():
    m = metrics([True, False, True, False, False], 3)
    assert m['precision_at_5'] == .4
    assert m['recall_at_5'] == 2/3
    assert np.isclose(m['ap_at_5'], (1+2/3)/3)
    assert m['hit_at_5'] == 1
    assert metrics([False]*5, 2)['ap_at_5'] == 0


def test_prepare_query_preserves_aspect_alpha_and_flip():
    c = Config()
    rgba = np.zeros((100, 100, 4), np.uint8)
    rgba[:, :50] = [0, 0, 255, 255]
    raw = cv2.imencode('.png', rgba)[1].tobytes()
    image, prep = prepare_image(raw, c)
    assert image.shape == (320, 640, 3) and prep['letterboxed']
    assert np.all(image[:, :160] == 255)
    assert np.all(image[:, 322:] == 255)  # Bo qua 2 cot noi suy sat bien do/trang.
    flipped, _ = prepare_image(raw, c, True)
    np.testing.assert_array_equal(flipped, image[:, ::-1])
    with pytest.raises(ValueError):
        prepare_image(b'not an image', c)


def test_extract_query_array_matches_dataset_contract():
    c = Config()
    image = np.full((320, 640, 3), 255, np.uint8)
    cv2.ellipse(image, (320, 160), (200, 80), 0, 0, 360, (50, 80, 130), -1)
    r = extract_array(image, b'bytes', 'query.png', c)
    assert r['config_id'] == c.config_id
    assert all(len(r['features'][k]) == c.dimensions[k] for k in GROUPS)
