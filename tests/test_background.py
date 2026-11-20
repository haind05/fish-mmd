import cv2
import numpy as np
import pytest
from fish_features import background
from fish_features.config import Config
from fish_features.query import prepare_image


def test_soft_alpha_compositing_on_white():
    bgr = np.full((2, 3, 3), [20, 40, 80], dtype=np.uint8)
    alpha = np.array([[0, .5, 1], [0, .5, 1]], dtype=float)
    result = background.composite_white(bgr, alpha)
    np.testing.assert_array_equal(result[0, 0], [255, 255, 255])
    np.testing.assert_array_equal(result[0, 2], [20, 40, 80])
    np.testing.assert_array_equal(result[0, 1], np.rint((np.array([20, 40, 80])+255)/2).astype(np.uint8))
    with pytest.raises(ValueError):
        background.composite_white(bgr, np.full((2, 3), np.nan))


def test_rmbg_runs_before_letterbox_and_preserves_original_preview(monkeypatch):
    image = np.full((100, 200, 3), 160, np.uint8)
    image[30:70, 40:160] = [10, 60, 120]
    alpha = np.zeros((100, 200), float)
    alpha[30:70, 40:160] = 1
    def fake_model(bgr):
        assert bgr.shape == image.shape  # Truy van chua letterbox.
        np.testing.assert_array_equal(bgr, image)
        return background.composite_white(bgr, alpha), alpha, {'method':'rmbg2'}
    monkeypatch.setattr(background, 'remove_background', fake_model)
    artifacts = {}
    raw = cv2.imencode('.png', image)[1].tobytes()
    output, prep = prepare_image(raw, Config(), background='rmbg2', preview_artifacts=artifacts)
    assert output.shape == (320, 640, 3)
    assert prep['background_removal']['applied']
    assert np.all(output[0] == 255)
    np.testing.assert_array_equal(artifacts['uploaded'], image)
    assert artifacts['rmbg_alpha'][50, 60] == 255


def test_standard_input_does_not_import_or_call_model(monkeypatch):
    def fail(*args):
        raise AssertionError('Must not call model')
    monkeypatch.setattr(background, 'remove_background', fail)
    image = np.full((320, 640, 3), 255, np.uint8)
    raw = cv2.imencode('.png', image)[1].tobytes()
    output, prep = prepare_image(raw, Config())
    np.testing.assert_array_equal(output, image)
    assert prep['background_removal']['method'] == 'none'


def test_missing_model_never_silently_uses_white_threshold(monkeypatch):
    def fail(*args):
        raise background.BackgroundUnavailable('Please log in locally')
    monkeypatch.setattr(background, 'remove_background', fail)
    raw = cv2.imencode('.png', np.full((100, 200, 3), 160, np.uint8))[1].tobytes()
    with pytest.raises(background.BackgroundUnavailable):
        prepare_image(raw, Config(), background='rmbg2')


def test_profile_matches_reference_method():
    profile = background.profile()
    assert profile['model_id'] == 'briaai/RMBG-2.0'
    assert profile['input_size'] == [1024, 1024]
    assert profile['mean'] == [.485, .456, .406]
    assert profile['std'] == [.229, .224, .225]
    assert profile['device'] == 'cpu'
    assert len(profile['revision']) == 40


def test_inference_adapter_with_torch_stub_not_pretrained_weights(monkeypatch):
    torch = pytest.importorskip('torch')
    transforms = pytest.importorskip('torchvision.transforms')
    config = background.profile()
    class StubModel:
        def __call__(self, tensor):
            assert tensor.shape == (1, 3, 1024, 1024)
            expected_red = (120/255-config['mean'][0])/config['std'][0]
            assert np.isclose(tensor[0, 0, 0, 0].item(), expected_red)
            logits = torch.full((1, 1, 1024, 1024), -20.)
            logits[:, :, 256:768, 256:768] = 20.
            return [logits]
    transform = transforms.Compose([transforms.Resize((1024, 1024)), transforms.ToTensor(),
        transforms.Normalize(config['mean'], config['std'])])
    monkeypatch.setattr(background, '_runtime', (StubModel(), transform, torch, transforms))
    bgr = np.full((100, 200, 3), [20, 60, 120], np.uint8)
    result, alpha, metadata = background.remove_background(bgr)
    assert result.shape == bgr.shape and alpha.shape == bgr.shape[:2]
    np.testing.assert_array_equal(result[50, 100], bgr[50, 100])
    np.testing.assert_array_equal(result[0, 0], [255, 255, 255])
    assert metadata['model_id'] == 'briaai/RMBG-2.0'
