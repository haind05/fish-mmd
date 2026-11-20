import cv2
import numpy as np


def resample_contour(contour, count):
    points = contour[:, 0, :].astype(float)
    # Duong bao di tu trai qua phan lung den duoi: clockwise tren anh (y xuong).
    signed = np.sum(points[:, 0]*np.roll(points[:, 1], -1) -
                    np.roll(points[:, 0], -1)*points[:, 1])
    if signed < 0:
        points = points[::-1]
    # Diem trai nhat, neu trung x thi chon y nho nhat.
    start = np.lexsort((points[:, 1], points[:, 0]))[0]
    points = np.roll(points, -int(start), axis=0)
    closed = np.vstack([points, points[0]])
    lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
    target = np.linspace(0, lengths[-1], count, endpoint=False)
    return np.column_stack([np.interp(target, lengths, closed[:, k]) for k in (0, 1)])


def shape_features(mask, contour, bbox, config):
    _, _, w, h = bbox
    area = int(mask.sum())
    hull_mask = np.zeros_like(mask)
    cv2.drawContours(hull_mask, [cv2.convexHull(contour)], -1, 1, cv2.FILLED)
    hull_area = int(hull_mask.sum())
    geo = np.array([w/h, area/hull_area, area/(w*h)])
    yy, xx = np.nonzero(mask)
    center = np.array([xx.mean(), yy.mean()])
    points = resample_contour(contour, config.contour_samples)
    distances = np.linalg.norm(points-center, axis=1)
    profile = distances / distances.mean()
    z = points[:, 0] + 1j*points[:, 1]
    spectrum = np.fft.fft(z) / len(z)
    scale = abs(spectrum[1])
    if scale < 1e-8:
        raise ValueError("|F1| qua nho de chuan hoa Fourier")
    fd = np.abs(spectrum[2:2+config.fourier_count]) / scale
    return geo, profile, fd, points, {"area": area, "hull_area": hull_area,
        "centroid": center.tolist(), "fourier_scale": float(scale)}
