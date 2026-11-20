from pathlib import Path
import hashlib
import re
import cv2
import numpy as np
from .preprocessing import read_image, segment
from .texture import circular_lbp, glcm_features
from .shape import shape_features
from .color import color_features


def extract(path, root, config, artifacts=None):
    image, raw = read_image(path, config)
    mask, contour, bbox, warnings, retained = segment(image, config.white_threshold)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    glcm, pairs = glcm_features(gray, mask, config)
    ulbp, raw_lbp, valid_centers = circular_lbp(gray, mask, config.lbp_radius)
    geo, profile, fd, points, shape_meta = shape_features(mask, contour, bbox, config)
    hsv, moments, spatial, region_counts = color_features(image, mask, bbox, config)
    if 0 in region_counts:
        warnings.append("empty_spatial_region")
    groups = dict(glcm=glcm, ulbp=ulbp, geometry=geo, contour_profile=profile,
                  fourier=fd, hsv=hsv, color_moments=moments, spatial_hsv=spatial)
    for name, values in groups.items():
        if len(values) != config.dimensions[name] or not np.isfinite(values).all():
            raise ValueError(f"Vector {name} khong hop le")
    match = re.fullmatch(r"species_(\d+)_(.+)_(\d+)\.[^.]+", Path(path).name)
    record = {"path": Path(path).relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "pixel_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
        "width": image.shape[1], "height": image.shape[0],
        "species_code": int(match[1]) if match else None,
        "species_name": match[2].replace("_", " ") if match else None,
        "source_image_id": match[3] if match else None,
        "config_id": config.config_id,
        "features": {k: v.tolist() for k, v in groups.items()},
        "metadata": {**shape_meta, "bbox_xywh": list(bbox), "occupancy": float(mask.mean()),
            "retained_component_fraction": retained, "glcm_pair_counts": pairs,
            "lbp_valid_centers": valid_centers, "spatial_pixel_counts": region_counts,
            "warnings": warnings}}
    if artifacts is not None:
        folder = Path(artifacts) / Path(record["path"]).with_suffix("")
        folder.mkdir(parents=True, exist_ok=True)
        cv2.imencode(".png", mask*255)[1].tofile(str(folder / "mask.png"))
        overlay = image.copy()
        cv2.drawContours(overlay, [contour], -1, (0, 0, 255), 1)
        x, y, w, h = bbox
        cv2.rectangle(overlay, (x, y), (x+w-1, y+h-1), (0, 180, 0), 1)
        cv2.imencode(".png", overlay)[1].tofile(str(folder / "contour.png"))
        np.savez_compressed(folder / "intermediates.npz", contour_xy=points, circular_lbp=raw_lbp, **groups)
    return record
