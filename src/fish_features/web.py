"""Giao dien kiem tra local: python -m fish_features.web."""
import argparse
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import cv2
import numpy as np
from psycopg.rows import dict_row
from .database import connect
from .preprocessing import segment
from .query import MAX_UPLOAD, search_bytes
from .retrieval import read_profile
from .background import BackgroundUnavailable, status as background_status

STATIC = Path(__file__).parent / "web_static"


def overview():
    with connect() as conn:
        images, species = conn.execute("SELECT count(*),count(DISTINCT species_code) FROM images").fetchone()
        count = conn.execute("SELECT count(*) FROM feature_catalog").fetchone()[0]
        conn.row_factory = dict_row
        configs = conn.execute("SELECT config_id,parameters,dimensions FROM extraction_configs ORDER BY created_at").fetchall()
        species_rows = conn.execute("SELECT species_code,species_name,count(*) AS count FROM images GROUP BY species_code,species_name ORDER BY species_name NULLS LAST").fetchall()
    return dict(images=images, species=species, feature_sets=count, configs=configs, species_options=species_rows)


def gallery(query):
    page = max(1, int(query.get("page", ["1"])[0]))
    text = query.get("q", [""])[0].strip()[:200]
    species = query.get("species", [""])[0]
    conditions, params = [], []
    if text:
        conditions.append("(relative_path ILIKE %s OR species_name ILIKE %s)")
        params.extend([f"%{text}%", f"%{text}%"])
    if species:
        conditions.append("species_code=%s")
        params.append(int(species))
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    with connect() as conn:
        total = conn.execute("SELECT count(*) FROM images"+where, params).fetchone()[0]
        page = min(page, max(1, (total+23)//24))
        conn.row_factory = dict_row
        rows = conn.execute("""SELECT image_id,relative_path,species_name,species_code,width,height,
            (SELECT count(*) FROM image_features f WHERE f.image_id=images.image_id AND f.source_sha256=images.sha256) AS feature_count
            FROM images"""+where+" ORDER BY relative_path LIMIT 24 OFFSET %s", params+[(page-1)*24]).fetchall()
    return dict(items=rows, total=total, page=page, pages=max(1, (total+23)//24))


def detail(image_id):
    with connect() as conn:
        conn.row_factory = dict_row
        image = conn.execute("SELECT * FROM images WHERE image_id=%s", (image_id,)).fetchone()
        if image is None:
            raise FileNotFoundError("Khong tim thay anh")
        features = conn.execute("""SELECT f.*,c.parameters,c.dimensions FROM image_features f
            JOIN extraction_configs c USING(config_id)
            WHERE image_id=%s AND source_sha256=%s ORDER BY extracted_at DESC""", (image_id, image["sha256"])).fetchall()
    return dict(image=image, features=features)


def resolve_image(root, relative):
    target = (Path(root).resolve() / relative).resolve()
    if not target.is_relative_to(Path(root).resolve()) or not target.is_file():
        raise FileNotFoundError("Khong tim thay file anh trong dataset")
    return target


@lru_cache(maxsize=128)
def image_preview(path, mtime, kind, threshold):
    bgr = cv2.imdecode(np.frombuffer(Path(path).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Khong doc duoc anh")
    if kind != "original":
        mask, contour, bbox, _, _ = segment(bgr, threshold)
        if kind == "mask":
            bgr = cv2.cvtColor(mask*255, cv2.COLOR_GRAY2BGR)
        else:
            bgr = bgr.copy()
            cv2.drawContours(bgr, [contour], -1, (30, 70, 240), 1)
            x, y, w, h = bbox
            cv2.rectangle(bgr, (x, y), (x+w-1, y+h-1), (0, 150, 95), 1)
    return cv2.imencode(".png", bgr)[1].tobytes()


class Handler(BaseHTTPRequestHandler):
    def respond(self, data, content_type="application/json; charset=utf-8", status=200):
        if content_type.startswith("application/json"):
            data = json.dumps(data, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        try:
            if url.path in ("/", "/app.js", "/style.css", "/retrieval.js", "/retrieval.css"):
                filename, mime = {"/": ("index.html", "text/html; charset=utf-8"),
                    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                    "/retrieval.js": ("retrieval.js", "text/javascript; charset=utf-8"),
                    "/retrieval.css": ("retrieval.css", "text/css; charset=utf-8"),
                    "/style.css": ("style.css", "text/css; charset=utf-8")}[url.path]
                self.respond((STATIC / filename).read_bytes(), mime)
            elif url.path == "/api/overview":
                self.respond(overview())
            elif url.path == "/api/retrieval-config":
                self.respond(read_profile())
            elif url.path == "/api/background-status":
                self.respond(background_status())
            elif url.path == "/api/evaluation":
                report = Path(__file__).resolve().parents[2] / "docs/task4_evaluation.json"
                if not report.is_file():
                    raise FileNotFoundError("Chua co bao cao danh gia")
                self.respond(json.loads(report.read_text(encoding="utf-8")))
            elif url.path == "/api/images":
                self.respond(gallery(query))
            elif url.path.startswith("/api/images/"):
                self.respond(detail(int(url.path.rsplit("/", 1)[1])))
            elif url.path.startswith("/media/"):
                image_id = int(url.path.rsplit("/", 1)[1])
                kind = query.get("kind", ["original"])[0]
                if kind not in {"original", "mask", "contour"}:
                    raise ValueError("Loai anh khong hop le")
                record = detail(image_id)
                requested = query.get("config", [""])[0]
                feature = next((f for f in record["features"] if f["config_id"] == requested), None)
                if requested and feature is None:
                    raise FileNotFoundError("Khong tim thay cau hinh")
                feature = feature or next(iter(record["features"]), None)
                threshold = feature["parameters"]["white_threshold"] if feature else 245
                path = resolve_image(self.server.images_root, record["image"]["relative_path"])
                self.respond(image_preview(str(path), path.stat().st_mtime_ns, kind, threshold), "image/png")
            else:
                self.respond({"error": "Khong tim thay duong dan"}, status=404)
        except FileNotFoundError as exc:
            self.respond({"error": str(exc)}, status=404)
        except ValueError as exc:
            self.respond({"error": str(exc)}, status=400)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:
            self.log_error("Database or server error")
            self.respond({"error": "Khong ket noi duoc CSDL hoac du lieu chua san sang. Chay docker compose up -d --wait va kiem tra db-stats."}, status=503)

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/api/search":
            self.respond({"error": "Khong tim thay duong dan"}, status=404)
            return
        try:
            query = parse_qs(url.query)
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_UPLOAD:
                self.close_connection = True
                self.respond({"error": "Kich thuoc upload toi da 10 MiB"}, status=413)
                return
            if query.get("id"):
                if length:
                    raise ValueError("Khong gui kem upload khi dung ID dataset")
                record = detail(int(query["id"][0]))
                path = resolve_image(self.server.images_root, record["image"]["relative_path"])
                raw, filename = path.read_bytes(), path.name
                background = "none"  # Dataset da chuan hoa, khong infer lai model.
            else:
                raw, filename = self.rfile.read(length), query.get("filename", ["query.png"])[0]
                background = query.get("background", ["none"])[0]
            self.respond(search_bytes(raw, filename, query.get("flip", ["0"])[0] == "1", background=background))
        except BackgroundUnavailable as exc:
            self.respond({"error": str(exc), "code": "background_unavailable"}, status=503)
        except (ValueError, cv2.error) as exc:
            self.respond({"error": str(exc)}, status=400)
        except FileNotFoundError as exc:
            self.respond({"error": str(exc)}, status=404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:
            self.log_error("Search error")
            self.respond({"error": "Khong tim kiem duoc. Kiem tra PostgreSQL va bo dac trung da nap."}, status=503)


def main():
    parser = argparse.ArgumentParser(description="Giao dien web kiem tra anh ca local")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--images", default="data/images")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.images_root = Path(args.images).resolve()
    print(f"Fish Features: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
