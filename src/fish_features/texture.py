import numpy as np


def glcm_properties(p):
    i, j = np.indices(p.shape)
    mi, mj = (i*p).sum(), (j*p).sum()
    vi, vj = (((i-mi)**2)*p).sum(), (((j-mj)**2)*p).sum()
    corr = 1.0 if vi*vj < 1e-20 else (((i-mi)*(j-mj)*p).sum() / np.sqrt(vi*vj))
    positive = p[p > 0]
    return [float((p*p).sum()), float(((i-j)**2*p).sum()),
            float((p/(1+(i-j)**2)).sum()), float(corr),
            float(-(positive*np.log2(positive)).sum())]


def glcm_features(gray, mask, config):
    q = gray.astype(np.int32) * config.gray_levels // 256
    height, width = gray.shape
    values, pair_counts = [], []
    for dr, dc in config.glcm_offsets:
        r0, r1 = max(0, -dr), min(height, height-dr)
        c0, c1 = max(0, -dc), min(width, width-dc)
        a, b = q[r0:r1, c0:c1], q[r0+dr:r1+dr, c0+dc:c1+dc]
        valid = (mask[r0:r1, c0:c1] > 0) & (mask[r0+dr:r1+dr, c0+dc:c1+dc] > 0)
        n = int(valid.sum())
        if n == 0:
            raise ValueError("GLCM khong co cap pixel hop le")
        counts = np.bincount(a[valid]*config.gray_levels+b[valid],
                             minlength=config.gray_levels**2).reshape(config.gray_levels, -1)
        values.extend(glcm_properties(counts / n))
        pair_counts.append(n)
    return np.array(values), pair_counts


def uniform_lut():
    # 58 ma uniform tang dan theo ma thap phan; non-uniform -> 58.
    lut = np.full(256, 58, dtype=np.uint8)
    label = 0
    for code in range(256):
        bits = [(code >> p) & 1 for p in range(8)]
        if sum(bits[p] != bits[(p+1) % 8] for p in range(8)) <= 2:
            lut[code] = label
            label += 1
    return lut


def circular_lbp(gray, mask, radius=1):
    # Noi suy bilinear chinh xac bang NumPy; chi giu tam ma toan bo
    # pixel co trong so noi suy duong deu thuoc mask, tranh lan nen.
    yy, xx = np.indices(gray.shape)
    codes = np.zeros(gray.shape, dtype=np.uint8)
    valid = mask.astype(bool).copy()
    height, width = gray.shape
    for p in range(8):
        dx = round(radius*np.cos(2*np.pi*p/8), 12)
        dy = round(-radius*np.sin(2*np.pi*p/8), 12)
        sx, sy = xx+dx, yy+dy
        x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
        wx, wy = sx-x0, sy-y0
        sample = np.zeros(gray.shape, dtype=float)
        for ox, oy, weight in ((0, 0, (1-wx)*(1-wy)), (1, 0, wx*(1-wy)),
                               (0, 1, (1-wx)*wy), (1, 1, wx*wy)):
            x, y = x0+ox, y0+oy
            inside = (x >= 0) & (x < width) & (y >= 0) & (y < height)
            xc, yc = np.clip(x, 0, width-1), np.clip(y, 0, height-1)
            valid &= (weight <= 1e-12) | (inside & (mask[yc, xc] > 0))
            sample += weight*gray[yc, xc]
        codes |= ((sample >= gray-1e-10).astype(np.uint8) << p)
    if not valid.any():
        raise ValueError("LBP khong co lan can hop le")
    raw_hist = np.bincount(codes[valid], minlength=256).astype(float)
    raw_hist /= raw_hist.sum()
    hist = np.bincount(uniform_lut(), weights=raw_hist, minlength=59)
    return hist, raw_hist, int(valid.sum())
