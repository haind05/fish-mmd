import base64
from pathlib import Path
import time
import cv2
import numpy as np
from .extractor import extract_array
from .preprocessing import segment
from .retrieval import database_index, read_profile

MAX_UPLOAD = 10 * 1024 * 1024


def prepare_image(raw, config, flip=False, background="none", preview_artifacts=None):
    if not raw or len(raw) > MAX_UPLOAD:
        raise ValueError("Anh truy van phai tu 1 byte den 10 MiB")
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None or image.dtype != np.uint8:
        raise ValueError("Can anh PNG/JPEG/WebP 8-bit doc duoc")
    if image.shape[0]*image.shape[1] > 20_000_000:
        raise ValueError("Anh vuot 20 megapixel")
    original_shape = list(image.shape[:2][::-1])
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        alpha = image[:, :, 3:].astype(float)/255
        image = np.rint(image[:, :, :3]*alpha+255*(1-alpha)).astype(np.uint8)
    elif image.shape[2] != 3:
        raise ValueError("So kenh anh khong ho tro")
    if background not in ("none", "rmbg2"):
        raise ValueError("Che do tach nen phai la none hoac rmbg2")
    background_info = {"method": "none", "applied": False}
    if background == "rmbg2":
        from .background import remove_background
        before = image.copy()
        image, alpha, background_info = remove_background(image)
        background_info["applied"] = True
        if preview_artifacts is not None:
            # Chi dung anh nho cho preview, khong gui lai upload 20MP trong JSON.
            scale = min(1, 640/before.shape[1], 320/before.shape[0])
            size = (max(1, round(before.shape[1]*scale)), max(1, round(before.shape[0]*scale)))
            preview_artifacts["uploaded"] = cv2.resize(before, size, interpolation=cv2.INTER_AREA)
            preview_artifacts["rmbg_alpha"] = cv2.resize(np.rint(alpha*255).astype(np.uint8), size, interpolation=cv2.INTER_AREA)
    target_w, target_h = config.expected_width, config.expected_height
    resized = image.shape[:2] != (target_h, target_w)
    if resized:
        scale = min(target_w/image.shape[1], target_h/image.shape[0])
        w, h = max(1, round(image.shape[1]*scale)), max(1, round(image.shape[0]*scale))
        small = cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        image = np.full((target_h, target_w, 3), 255, np.uint8)
        x, y = (target_w-w)//2, (target_h-h)//2
        image[y:y+h, x:x+w] = small
    if flip:
        image = cv2.flip(image, 1)
    return image, {"original_size": original_shape, "canvas_size": [target_w, target_h],
                   "background_removal": background_info,
                   "letterboxed": resized, "flipped_horizontal": bool(flip),
                   "orientation": "User supplies one fish, white background, head left; no automatic head detection"}


def png_data(image):
    return "data:image/png;base64,"+base64.b64encode(cv2.imencode(".png", image)[1]).decode()


def search_bytes(raw, filename="query.png", flip=False, profile_path=None, index=None, background="none"):
    start = time.perf_counter()
    profile = read_profile(profile_path)
    index = index or database_index(profile["feature_config_id"])
    if index.config.config_id != profile["feature_config_id"]:
        raise ValueError("Cau hinh query va gallery khong khop")
    artifacts = {}
    image, preparation = prepare_image(raw, index.config, flip, background, artifacts)
    record = extract_array(image, raw, Path(filename).name, index.config)
    extracted = time.perf_counter()
    result = index.rank(record, profile)
    finished = time.perf_counter()
    mask, contour, bbox, _, _ = segment(image, index.config.white_threshold)
    overlay = image.copy()
    cv2.drawContours(overlay, [contour], -1, (30, 70, 240), 1)
    x, y, w, h = bbox
    cv2.rectangle(overlay, (x, y), (x+w-1, y+h-1), (0, 150, 95), 1)
    return {**result, "query": record, "preparation": preparation,
        "previews": {**{k: png_data(v) for k, v in artifacts.items()},
                     "original": png_data(image), "mask": png_data(mask*255), "contour": png_data(overlay)},
        "profile": profile, "feature_config": index.config.as_dict(), "dimensions": index.config.dimensions,
        "gallery_fingerprint": index.fingerprint, "gallery_count": len(index.records),
        "normalizers": index.scalers,
        "timing_ms": {"prepare_extract_and_index": round((extracted-start)*1000, 2),
                      "ranking": round((finished-extracted)*1000, 2), "through_ranking": round((finished-start)*1000, 2)}}
