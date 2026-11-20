# Trích rút đặc trưng ảnh cá — mục 3

Triển khai mục 3 trong `assignment.txt`, kế thừa các đặc trưng ở chương 2 của `BaoCao_BTL.pdf` (81 trang). Python xử lý ảnh, PostgreSQL chạy bằng Docker. Ảnh giữ trên filesystem, CSDL lưu đường dẫn, thông tin ảnh, vector và cấu hình trích rút.

## Giao diện web local

Sau khi đã có CSDL và dataset như hướng dẫn bên dưới, chạy:

```powershell
docker compose up -d --wait
.venv/Scripts/python -m fish_features.web
```

Mở **http://127.0.0.1:8000** trong trình duyệt. Giao diện cho phép:

- Xem thống kê CSDL, tìm ảnh theo tên và lọc theo loài, phân trang.
- Chọn ảnh để đối chiếu ảnh gốc, mặt nạ và đường bao. Hai ảnh phân đoạn dựng lại theo cấu hình của bản ghi đang xem.
- Xem biểu đồ, bảng toàn bộ giá trị của 8 nhóm đặc trưng đã lưu trong PostgreSQL.
- Chọn cấu hình nếu một ảnh có nhiều bộ đặc trưng; xem metadata, tham số và tải JSON.

Server chỉ lắng nghe trên máy local, không cần cài thêm thư viện web hoặc Node.js. Dừng bằng `Ctrl+C` trong terminal chạy server. Nếu cổng bận, chạy `.venv/Scripts/python -m fish_features.web --port 8001` rồi mở cổng tương ứng. Web chỉ đọc dữ liệu, không thay đổi các vector đã lưu.

Hoặc dùng một lệnh: `powershell -ExecutionPolicy Bypass -File .\run-web.ps1` (chỉ áp dụng ExecutionPolicy cho tiến trình này). Script khởi động PostgreSQL và web tại cổng 8000. Nếu web đang chạy sẵn thì chỉ cần mở URL, không chạy thêm server.

Kiểm tra giao diện bằng trình duyệt tự động là tùy chọn cho phát triển: cài `playwright` vào `.venv`, có Chrome trên máy rồi chạy `.venv/Scripts/python scripts/verify_web_browser.py` khi server đang bật. Ảnh chụp kiểm tra lưu ở `outputs/web-check/`.

## Bắt đầu trên Windows / PowerShell

Chạy tại thư mục gốc project, bật Docker Desktop ở chế độ Linux containers:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pip install -e .
docker compose up -d --wait
.venv/Scripts/python -m fish_features unpack
.venv/Scripts/python -m fish_features extract
.venv/Scripts/python -m fish_features db-init
.venv/Scripts/python -m fish_features db-load
.venv/Scripts/python -m fish_features db-stats
```

Python 3.11 trở lên; môi trường đã kiểm thử dùng Python 3.14. Không cần cài PostgreSQL trực tiếp. Cổng host là **5433**, user `fish`, password `fish_local`, database `fish_features`. Đây là thông tin cho môi trường học tập local, cổng chỉ mở trên localhost.

Có thể xem CSDL bằng DBeaver/pgAdmin có sẵn, hoặc dùng ngay psql trong container:

```powershell
docker compose exec db psql -U fish -d fish_features
```

Trong psql: `\dt` liệt kê bảng, `SELECT * FROM feature_catalog LIMIT 3;` xem đặc trưng hình học, `\q` thoát. Các truy vấn có sẵn ở `sql/examples.sql`.

## Cấu trúc

```text
assignment.txt                 Đề bài gốc
BaoCao_BTL.pdf                  Báo cáo mục 1, 2 gốc
images.zip                     Dataset gốc
compose.yaml                   PostgreSQL + volume + healthcheck
src/fish_features/
  config.py                    Tham số, số chiều, mã cấu hình
  preprocessing.py             Đọc ảnh, tách nền, kiểm tra đầu vào
  texture.py                   GLCM, Circular LBP, Uniform LBP
  shape.py                     Hình học, Contour Profile, Fourier
  color.py                     HSV, RGB moments, spatial HSV
  extractor.py                 Ghép các bước trên cho một ảnh
  database.py                  Khởi tạo, nạp/cập nhật, đọc CSDL
  __main__.py                  Các lệnh CLI
  web.py                       HTTP server local và API đọc CSDL
  web_static/                  Giao diện HTML/CSS/JavaScript
sql/                           Schema và ví dụ quản trị
tests/                         Kiểm chứng công thức, quy ước
docs/muc3.md                   Thuyết minh mục 3 và đối chiếu báo cáo
docs/verification.md           Kết quả chạy thực tế
data/images/                   Ảnh giải nén, giữ nguyên tên gốc
outputs/default/
  config.json                  Cấu hình + phiên bản thư viện
  features.jsonl               Một bản ghi/ảnh, đủ 8 nhóm vector
  summary.json                 Số ảnh, lỗi, cảnh báo, thời gian
  samples/<tên ảnh>/
    mask.png                   Mặt nạ vùng cá
    contour.png                Đường bao đỏ, bounding box xanh
    intermediates.npz          Vector và dữ liệu trung gian NumPy
```

`data/`, `outputs/`, `.venv/` không đưa vào Git, có thể tái tạo từ ZIP và lệnh trên. File gốc được giữ nguyên.

Dataset `images.zip` được cung cấp riêng, không đưa vào Git. Khi clone repository sang máy khác, đặt file này tại thư mục gốc project trước khi chạy lệnh `unpack`.

## Kiểm tra từng bước

```powershell
# Chạy thử 10 ảnh, không thay kết quả toàn bộ:
.venv/Scripts/python -m fish_features extract --limit 10 --output outputs/preview
# Đọc một ảnh đã nạp; thay bằng tên file thực tế:
.venv/Scripts/python -m fish_features db-inspect species_101_cheilinus_chlorourus_936.png
# Kiểm thử thuật toán:
.venv/Scripts/python -m pytest -q
```

Kiểm thử thêm ràng buộc CSDL (sau `db-init`):

```powershell
$env:RUN_DB_TESTS='1'
.venv/Scripts/python -m pytest -q
```

Các test CSDL dùng dữ liệu tạm trong transaction và rollback sau mỗi test.

Trích rút mặc định lưu minh họa cho 5 ảnh đầu theo thứ tự tên file. Dùng `--samples 20` để lưu 20 ảnh, hoặc `--samples 1000` để xem mặt nạ toàn bộ dataset. `.npz` đọc bằng `numpy.load(...)`; `features.jsonl` là JSON thuần để dễ kiểm tra và tái sử dụng ở mục 4.

Nếu một ảnh lỗi, pipeline ghi lỗi vào `summary.json`, tiếp tục các ảnh còn lại và trả exit code 1. Chỉ các ảnh thành công có trong JSONL. Kiểm tra `failed` trước khi nạp; mục tiêu với dataset hiện tại là 1.000 ảnh thành công. Các cảnh báo phân đoạn cần được đối chiếu trực quan với ảnh gốc.

## Thay cấu hình

Tạo JSON chỉ chứa các trường muốn thay, ví dụ `{"gray_levels":16,"hsv_bins":[8,4,4]}`, rồi chạy:

```powershell
.venv/Scripts/python -m fish_features extract --config config-custom.json --output outputs/custom
.venv/Scripts/python -m fish_features db-load --input outputs/custom/features.jsonl
```

Mỗi cấu hình có SHA-256 riêng, cùng ảnh có thể lưu nhiều bộ đặc trưng. Khi đổi thuật toán phải tăng `algorithm_version` trong `config.py` để không nhầm kết quả cũ. Không sửa `config.json` sau khi trích xuất.

## Vận hành CSDL

`db-init` có thể chạy lại. `db-load` dùng transaction và upsert theo đường dẫn ảnh + cấu hình: nạp lại không nhân đôi bản ghi. Khi nội dung file ảnh thay đổi, các đặc trưng cũ của ảnh đó bị loại khỏi CSDL trước khi nạp bộ mới. Ảnh khác không nằm trong lần nạp hiện tại được giữ lại. Xóa ảnh trong bảng `images` sẽ xóa đặc trưng liên quan bằng khóa ngoại.

`docker compose stop` dừng CSDL; `docker compose start` bật lại. Volume giữ dữ liệu khi container dừng hoặc được tạo lại. **Không dùng `docker compose down -v` nếu muốn giữ dữ liệu**, vì tùy chọn `-v` xóa volume.

`.env.example` là mẫu cấu hình Compose. Nếu đổi cổng/user/password/database bằng `.env`, đặt `DATABASE_URL` tương ứng cho tiến trình Python:

```powershell
$env:DATABASE_URL='postgresql://fish:fish_local@127.0.0.1:5433/fish_features'
```

CLI Python đọc biến môi trường hệ điều hành, không tự đọc file `.env`. Thay user/password trong Compose không thay thông tin xác thực của volume PostgreSQL đã khởi tạo.

Sao lưu/khôi phục có thể dùng `pg_dump` và `psql` trong container. Giữ cùng dataset ảnh khi chuyển CSDL sang máy khác vì đường dẫn ảnh là đường dẫn tương đối với `data/images`.

Phạm vi hiện tại là mục 3 và giao diện web kiểm tra dữ liệu local. Cấu trúc vector và hàm `extract()` đã sẵn sàng để mục 4 dùng chung; việc xếp hạng top 5, chọn trọng số và đánh giá truy hồi thuộc bước tiếp theo.
