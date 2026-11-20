from dataclasses import asdict, dataclass
import hashlib
import json


@dataclass(frozen=True)
class Config:
    algorithm_version: str = "1.0.0"
    expected_width: int = 640
    expected_height: int = 320
    white_threshold: int = 245
    gray_levels: int = 32
    glcm_offsets: tuple = ((0, 1), (-1, 1), (-1, 0), (-1, -1))
    lbp_points: int = 8
    lbp_radius: int = 1
    contour_samples: int = 256
    fourier_count: int = 10
    hsv_bins: tuple = (12, 4, 4)
    spatial_columns: int = 3
    spatial_rows: int = 2

    def __post_init__(self):
        if not 1 <= self.white_threshold <= 255:
            raise ValueError("white_threshold must be in [1,255]")
        if not 2 <= self.gray_levels <= 256:
            raise ValueError("gray_levels must be in [2,256]")
        if self.lbp_points != 8 or self.lbp_radius < 1:
            raise ValueError("LBP uses P=8 and integer R>=1")
        if not 1 <= self.fourier_count < self.contour_samples // 2:
            raise ValueError("Invalid Fourier count")
        if len(self.hsv_bins) != 3 or min(self.hsv_bins) < 1:
            raise ValueError("HSV needs three positive bin counts")
        if min(self.spatial_columns, self.spatial_rows) < 1:
            raise ValueError("Invalid spatial grid")
        if not self.glcm_offsets or any(dr == dc == 0 for dr, dc in self.glcm_offsets):
            raise ValueError("GLCM needs nonzero offsets")

    def as_dict(self):
        return asdict(self)

    @property
    def config_id(self):
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode()).hexdigest()

    @property
    def dimensions(self):
        h = self.hsv_bins[0] * self.hsv_bins[1] * self.hsv_bins[2]
        return {"glcm": 5 * len(self.glcm_offsets), "ulbp": 59,
                "geometry": 3, "contour_profile": self.contour_samples,
                "fourier": self.fourier_count, "hsv": h,
                "color_moments": 9, "spatial_hsv": h * self.spatial_columns * self.spatial_rows}

    @classmethod
    def read(cls, path=None):
        if path is None:
            return cls()
        with open(path, encoding="utf-8") as f:
            return cls(**json.load(f))
