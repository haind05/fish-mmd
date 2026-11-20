import cv2
import numpy as np


def color_moments(rgb_pixels):
    pixels = rgb_pixels.astype(float) / 255
    mean = pixels.mean(axis=0)
    delta = pixels-mean
    return np.r_[mean, np.sqrt((delta**2).mean(axis=0)), np.cbrt((delta**3).mean(axis=0))]


def color_features(bgr, mask, bbox, config):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.int32)
    nh, ns, nv = config.hsv_bins
    index = ((hsv[:, :, 0]*nh//180)*ns + hsv[:, :, 1]*ns//256)*nv + hsv[:, :, 2]*nv//256
    bins = nh*ns*nv

    def histogram(region):
        counts = np.bincount(index[region], minlength=bins).astype(float)
        return counts / counts.sum() if counts.sum() else counts

    global_hist = histogram(mask.astype(bool))
    moments = color_moments(bgr[mask > 0][:, ::-1])
    x, y, w, h = bbox
    cols, rows = config.spatial_columns, config.spatial_rows
    if w < cols or h < rows:
        raise ValueError("Bounding box nho hon luoi spatial")
    xs = [x + k*(w//cols) for k in range(cols)] + [x+w]
    ys = [y + k*(h//rows) for k in range(rows)] + [y+h]
    histograms, counts = [], []
    for row in range(rows):
        for col in range(cols):
            region = np.zeros_like(mask, dtype=bool)
            region[ys[row]:ys[row+1], xs[col]:xs[col+1]] = mask[ys[row]:ys[row+1], xs[col]:xs[col+1]] > 0
            counts.append(int(region.sum()))
            histograms.append(histogram(region))
    return global_hist, moments, np.concatenate(histograms), counts
