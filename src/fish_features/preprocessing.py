from pathlib import Path
import cv2
import numpy as np


def read_image(path, config):
    # imdecode ho tro duong dan Unicode tren Windows.
    raw = Path(path).read_bytes()
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError("Khong giai ma duoc anh")
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Can anh RGB 8-bit, 3 kenh (khong alpha)")
    if image.shape[:2] != (config.expected_height, config.expected_width):
        raise ValueError(f"Sai kich thuoc: {image.shape[:2]}")
    return image, raw


def segment(image, threshold):
    candidate = np.any(image < threshold, axis=2).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, connectivity=8)
    if count < 2:
        raise ValueError("Khong tim thay vung ca")
    largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    component = (labels == largest).astype(np.uint8)
    # Padding bao dam seed flood-fill luon la nen, ke ca ca cham goc anh.
    padded = np.pad(component, 1)
    flooded = padded.copy()
    cv2.floodFill(flooded, None, (0, 0), 1)
    mask = (padded | (1 - flooded))[1:-1, 1:-1].astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contours, key=cv2.contourArea)
    if len(contour) < 4 or cv2.contourArea(contour) <= 0:
        raise ValueError("Contour suy bien")
    bbox = cv2.boundingRect(contour)
    warnings = []
    x, y, w, h = bbox
    if x == 0 or y == 0 or x+w == image.shape[1] or y+h == image.shape[0]:
        warnings.append("mask_touches_border")
    retained = int(component.sum()) / int(candidate.sum())
    if retained < .98:
        warnings.append("discarded_components_over_2_percent")
    occupancy = float(mask.mean())
    if not .05 <= occupancy <= .8:
        warnings.append("unusual_occupancy")
    return mask, contour, bbox, warnings, retained
