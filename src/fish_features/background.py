"""RMBG-2.0 -> alpha matte -> nen trang, theo repo tham chieu cua DucHai278.

Khong doc token tu source, khong tu dong doi model neu thieu quyen truy cap.
Tai model bang credential Hugging Face local; anh duoc infer tren may nay.
"""
import importlib.util
import json
from pathlib import Path
import threading
import time
import numpy as np

PROFILE_PATH = Path(__file__).with_name("background_profile.json")
_lock = threading.Lock()
_runtime = None


class BackgroundUnavailable(RuntimeError):
    pass


def profile():
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def status():
    config = profile()
    dependencies = all(importlib.util.find_spec(m) is not None for m in ("torch", "torchvision", "transformers", "PIL", "timm", "kornia", "einops"))
    logged_in, cached = False, False
    if importlib.util.find_spec("huggingface_hub"):
        from huggingface_hub import get_token, try_to_load_from_cache
        logged_in = bool(get_token())
        cached = isinstance(try_to_load_from_cache(config["model_id"], "model.safetensors", revision=config["revision"]), str)
    if _runtime is not None:
        state, message = "loaded", "RMBG-2.0 đã nạp, xử lý ảnh trên máy local."
    elif not dependencies:
        state, message = "missing_dependencies", "Cần cài requirements-background.txt để dùng RMBG-2.0."
    elif not cached and not logged_in:
        state, message = "needs_login", "Chưa có model hoặc đăng nhập Hugging Face. Cấp quyền RMBG-2.0, chạy .venv/Scripts/hf auth login rồi khởi động lại web."
    else:
        state, message = "not_loaded", "Chưa nạp model. Lần đầu cần tải trọng số; quyền truy cập được kiểm tra khi nạp."
    return {"state": state, "message": message, "dependencies_installed": dependencies,
            "login_available": logged_in, "weights_cached": cached, "profile": config}


def _load():
    global _runtime
    if _runtime is not None:
        return _runtime
    availability = status()
    if availability["state"] in ("missing_dependencies", "needs_login"):
        raise BackgroundUnavailable(availability["message"])
    config = profile()
    try:
        import torch
        from torchvision import transforms
        from transformers import AutoModelForImageSegmentation
        torch.set_num_threads(config["cpu_threads"])
        torch.set_float32_matmul_precision("high")
        model = AutoModelForImageSegmentation.from_pretrained(
            config["model_id"], revision=config["revision"], code_revision=config["revision"],
            trust_remote_code=True).to(config["device"]).eval()
        transform = transforms.Compose([
            transforms.Resize(tuple(config["input_size"])), transforms.ToTensor(),
            transforms.Normalize(config["mean"], config["std"])])
        _runtime = (model, transform, torch, transforms)
        return _runtime
    except Exception as exc:
        # Khong tra log cua thu vien ra HTTP: co the chua thong tin xac thuc.
        name = type(exc).__name__
        raise BackgroundUnavailable(
            f"Không nạp được RMBG-2.0 ({name}). Hãy cấp quyền tại huggingface.co/briaai/RMBG-2.0, "
            "chạy .venv/Scripts/hf auth login trên máy và thử lại. "
            "Chi tiết: docs/background-removal.md. Không cần gửi token vào chat.") from None


def warmup():
    with _lock:
        _load()
    return status()


def composite_white(bgr, alpha):
    if alpha.shape != bgr.shape[:2] or not np.isfinite(alpha).all():
        raise ValueError("Mat na RMBG khong hop le")
    alpha = np.clip(alpha, 0, 1)
    # Tuong duong paste(image, mask=mask) tren nen trang trong repo tham chieu.
    return np.rint(bgr*alpha[:, :, None]+255*(1-alpha[:, :, None])).astype(np.uint8)


def remove_background(bgr):
    start = time.perf_counter()
    config = profile()
    with _lock:
        model, transform, torch, transforms = _load()
        from PIL import Image
        image = Image.fromarray(bgr[:, :, ::-1])
        tensor = transform(image).unsqueeze(0).to(config["device"])
        try:
            with torch.inference_mode():
                prediction = model(tensor)[-1].sigmoid().cpu()
            mask = transforms.ToPILImage()(prediction[0].squeeze()).resize(image.size)
            alpha = np.asarray(mask, dtype=np.float32)/255
        except Exception as exc:
            raise BackgroundUnavailable(f"RMBG-2.0 không xử lý được ảnh ({type(exc).__name__}). Kiểm tra bộ nhớ và cấu hình model.") from None
    if not np.any(alpha >= .5):
        raise ValueError("RMBG-2.0 không tìm thấy chủ thể đủ rõ. Hãy thử ảnh cá khác.")
    output = composite_white(bgr, alpha)
    return output, alpha, {**config, "method": "rmbg2", "inference_size": config["input_size"],
        "alpha_coverage_at_0_5": float((alpha >= .5).mean()),
        "elapsed_ms": round((time.perf_counter()-start)*1000, 2),
        "processing": "local", "postprocess": "soft alpha matte on white, before canvas letterbox"}
