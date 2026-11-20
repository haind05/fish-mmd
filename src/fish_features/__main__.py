import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import time
import zipfile
import cv2
import numpy as np
from .config import Config
from .extractor import extract


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def unpack(archive, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            # ZIP cua du an co thu muc images/: bo 1 cap nay.
            parts = Path(info.filename).parts
            relative = Path(*parts[1:]) if parts[0] == "images" else Path(*parts)
            target = (output / relative).resolve()
            if not target.is_relative_to(output):
                raise ValueError("Duong dan ZIP vuot ngoai thu muc dich")
            if target.exists():
                if target.read_bytes() != z.read(info):
                    raise ValueError(f"Khong ghi de file khac noi dung: {target}")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(info))
            count += 1
    return {"files": count, "output": str(output)}


def batch(args):
    config = Config.read(args.config)
    root, output = Path(args.images), Path(args.output)
    if not root.is_dir():
        raise ValueError(f"Khong tim thay thu muc anh: {root}")
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("limit must be positive")
        files = files[:args.limit]
    if not files:
        raise ValueError("Thu muc khong co anh")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "config.json", {"config_id": config.config_id, "parameters": config.as_dict(),
        "dimensions": config.dimensions, "runtime": {"python": platform.python_version(), "numpy": np.__version__, "opencv": cv2.__version__}})
    start = time.perf_counter()
    errors, warnings, pixel_hashes, species = [], Counter(), Counter(), set()
    success = 0
    temporary = output / "features.jsonl.tmp"
    with temporary.open("w", encoding="utf-8") as stream:
        for i, path in enumerate(files):
            try:
                record = extract(path, root, config, output / "samples" if i < args.samples else None)
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+"\n")
                success += 1
                warnings.update(record["metadata"]["warnings"])
                pixel_hashes[record["pixel_sha256"]] += 1
                if record["species_code"] is not None:
                    species.add(record["species_code"])
            except (ValueError, OSError, cv2.error) as exc:
                errors.append({"path": path.relative_to(root).as_posix(), "error": str(exc)})
            if (i+1) % 100 == 0:
                print(f"{i+1}/{len(files)} images", flush=True)
    temporary.replace(output / "features.jsonl")
    report = {"total": len(files), "success": success, "failed": len(errors), "species_from_filenames": len(species),
              "unique_pixel_hashes": len(pixel_hashes), "duplicate_pixel_groups": sum(n > 1 for n in pixel_hashes.values()),
              "warning_counts": dict(warnings), "seconds": round(time.perf_counter()-start, 3),
              "config_id": config.config_id, "dimensions": config.dimensions, "errors": errors}
    write_json(output / "summary.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description="Muc 3: trich rut dac trung va PostgreSQL")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("unpack")
    p.add_argument("--archive", default="images.zip")
    p.add_argument("--output", default="data/images")
    p = sub.add_parser("extract")
    p.add_argument("--images", default="data/images")
    p.add_argument("--output", default="outputs/default")
    p.add_argument("--config")
    p.add_argument("--limit", type=int)
    p.add_argument("--samples", type=int, default=5)
    p = sub.add_parser("db-init")
    p.add_argument("--schema", default="sql/schema.sql")
    p = sub.add_parser("db-load")
    p.add_argument("--input", default="outputs/default/features.jsonl")
    sub.add_parser("db-stats")
    p = sub.add_parser("db-inspect")
    p.add_argument("path", help="Duong dan tuong doi trong data/images")
    p = sub.add_parser("search", help="Anh truy van -> top 5 va chi tiet diem")
    p.add_argument("image")
    p.add_argument("--profile")
    p.add_argument("--flip", action="store_true")
    p.add_argument("--background", choices=["none", "rmbg2"], default="none")
    p.add_argument("--output", default="outputs/query.json")
    p = sub.add_parser("evaluate", help="Danh gia gallery/validation/test tach biet")
    p.add_argument("--output", default="outputs/evaluation")
    p.add_argument("--profile")
    p = sub.add_parser("bg-check", help="Kiem tra dependency, dang nhap va model RMBG-2.0")
    p.add_argument("--load", action="store_true", help="Tai va nap model bang credential Hugging Face local")
    args = parser.parse_args()
    try:
        if args.command == "unpack":
            print(json.dumps(unpack(args.archive, args.output), indent=2))
        elif args.command == "extract":
            return batch(args)
        elif args.command == "search":
            from .query import search_bytes
            result = search_bytes(Path(args.image).read_bytes(), Path(args.image).name, args.flip, args.profile, background=args.background)
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, result)
            print(json.dumps({"results": [{k: r[k] for k in ("rank", "path", "similarity", "distance")} for r in result["results"]],
                              "output": args.output, "profile": result["profile"]}, indent=2))
        elif args.command == "evaluate":
            from .evaluation import evaluate
            report = evaluate(args.output, args.profile)
            print(json.dumps({k: report[k] for k in ("split_counts", "selected_candidate", "validation", "test", "seconds")}, indent=2))
        elif args.command == "bg-check":
            from .background import status, warmup
            print(json.dumps(warmup() if args.load else status(), ensure_ascii=False, indent=2))
        else:
            from . import database as db
            if args.command == "db-init":
                db.initialize(args.schema)
                print("Schema ready")
            elif args.command == "db-load":
                print(f"Loaded {db.load_file(args.input)} feature sets")
            elif args.command == "db-stats":
                print(json.dumps(db.stats(), indent=2))
            elif args.command == "db-inspect":
                print(json.dumps(db.inspect_image(args.path), default=str, indent=2))
        return 0
    except Exception as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
