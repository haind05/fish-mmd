# Kết quả kiểm chứng mục 3

Chạy ngày **20/11/2026** trên workspace project, Python 3.14, NumPy 2.5.5, OpenCV 5.1.0, Psycopg 3.3.9; PostgreSQL 17 trong Docker.

## Trích rút toàn bộ dataset

Nguồn: `images.zip`, giải nén thành `data/images`. Kết quả lệnh `python -m fish_features extract`:

| Chỉ tiêu | Kết quả |
|---|---:|
| Số ảnh đầu vào | 1.000 |
| Trích rút thành công | 1.000 |
| Ảnh lỗi | 0 |
| Nội dung pixel riêng biệt | 1.000 |
| Nhóm ảnh trùng pixel | 0 |
| Mã loài khác nhau lấy từ tên file | 323 |
| Ảnh có cảnh báo theo quy tắc hiện tại | 0 |
| Thời gian trích rút | 395,613 giây (~6,6 phút) |

Cấu hình SHA-256:

```text
dee14083f1e017e28de89081ea10c392b830bb7331a19d6e70459a809c9ee484
```

Mỗi ảnh có tám nhóm với số chiều lần lượt: GLCM 20, ULBP 59, geometry 3, contour profile 256, Fourier 10, HSV 192, color moments 9 và spatial HSV 1.152. Tổng 1.701 giá trị số/ảnh.

Đã kiểm tra toàn bộ 1.000 bản ghi: đúng số chiều, toàn bộ giá trị hữu hạn, histogram HSV và ULBP tổng bằng 1, mỗi histogram spatial tổng bằng 1 khi ô có pixel, profile có trung bình bằng 1. Tổng số pixel ở sáu ô spatial bằng diện tích mask; Solidity và Extent nằm trong (0,1].

Kết quả chi tiết do chương trình tạo nằm tại `outputs/default/summary.json`, `config.json`, `features.jsonl`. Mặt nạ và đường bao 5 ảnh đầu nằm tại `outputs/default/samples/`. Đã xem trực quan overlay của ảnh `species_101_cheilinus_chlorourus_936.png`.

## CSDL

Dịch vụ `fish-features-db-1` ở trạng thái healthy, cổng `127.0.0.1:5433`. Khởi tạo schema và nạp JSONL thành công. Sau lần nạp đầu và sau lần nạp lại:

| Chỉ tiêu | Lần 1 | Lần 2 |
|---|---:|---:|
| Ảnh trong `images` | 1.000 | 1.000 |
| Mã loài khác nhau | 323 | 323 |
| Bộ đặc trưng của cấu hình mặc định | 1.000 | 1.000 |

Đọc lại tám mảng đặc trưng của tất cả 1.000 ảnh từ PostgreSQL và đối chiếu JSONL: giá trị giữ nguyên chính xác sau chu trình ghi/đọc.

## Kiểm thử tự động

**13 kiểm thử đạt** khi bật `RUN_DB_TESTS=1`, gồm 9 kiểm thử thuật toán/cấu hình và 4 kiểm thử CSDL. Các test CSDL dùng transaction rollback, không để lại ảnh thử.

- GLCM đối chiếu ví dụ báo cáo: ASM=0,25; Contrast=3; Homogeneity=0,4; Correlation=−0,2; Entropy=2.
- GLCM loại các cặp có pixel nền.
- Uniform LBP có 58 mã uniform riêng và 198 mã non-uniform gộp một nhãn; nội suy và vùng hợp lệ kiểm tra trên patch biết trước.
- Tách nền giữ thành phần chính và lấp lỗ kín; từ chối ảnh không có đối tượng.
- Hình học dùng cùng quy ước diện tích pixel; contour lấy mẫu nhất quán dù đảo chiều và dịch điểm bắt đầu.
- RGB đúng thứ tự, τ giữ dấu âm, histogram HSV và spatial được chuẩn hóa, ô trống không tạo NaN.
- Trigger CSDL từ chối sai số chiều, NaN và NULL; khóa ngoại/cascade hoạt động.

## Bổ sung giao diện kiểm tra local

Giao diện tại `http://127.0.0.1:8000` đọc dữ liệu PostgreSQL, có thư viện 24 ảnh/trang, tìm kiếm, lọc mã loài, chi tiết ảnh và lựa chọn cấu hình. Các ảnh mask/contour dựng lại từ file nguồn; các vector đọc từ CSDL. Có biểu đồ và bảng số đầy đủ cho tám nhóm, xuất JSON, thông tin phân đoạn và cấu hình thuật toán.

Sau bổ sung web: **17 kiểm thử Python đạt**, gồm các kiểm thử trước và kiểm tra HTTP/API, đường dẫn ảnh không vượt ra ngoài dataset, trang lỗi và hướng dẫn khi CSDL mất kết nối. Kiểm tra trình duyệt Chrome đạt các luồng phân trang, tìm kiếm, lọc loài, chi tiết, tám biểu đồ, tải JSON, kết quả rỗng và màn hình 390px; không ghi nhận lỗi JavaScript. Ảnh chụp kiểm tra trong `outputs/web-check/`.

## Bổ sung mục 4 — tìm kiếm ảnh tương đồng

Đã triển khai CLI `search`, `evaluate` và upload ảnh trên web. Cấu hình có hiệu lực ở `src/fish_features/retrieval_profile.json`; mọi lần truy vấn trả lại cấu hình, gallery fingerprint, mean/std chuẩn hóa và điểm từng nhóm.

**28 kiểm thử Python đạt** sau bổ sung mục 4. Bổ sung kiểm chứng Hellinger, self distance bằng 0, loại ảnh trùng pixel, tổng đóng góp bằng khoảng cách tổng, nhãn loài không ảnh hưởng xếp hạng, xử lý spatial rỗng, chia holdout không giao nhau, công thức chỉ số, chuyển alpha/letterbox/lật và API upload/giới hạn dung lượng.

Đã kiểm tra trực tiếp trên CSDL: trích lại một ảnh dataset cho query cho kết quả khớp chính xác cả 8 vector đã lưu, query bị loại khỏi top5 theo hash pixel. Browser Chrome đã kiểm tra upload ảnh, JPEG mới 480×240 được đưa về canvas chuẩn, thứ tự 5 kết quả, điểm từng nhóm, xem mọi vector, tải JSON, query từ gallery, lỗi ảnh hỏng và màn hình 390px; không có lỗi JavaScript. Ảnh chụp ở `outputs/web-check/retrieval.png` và `retrieval-mobile.png`.

Đánh giá seed42: 530 gallery /208 validation /262 test, chọn trọng số 20% màu +60% hình dạng +20% kết cấu theo validation mAP@5 cao nhất trong 8 phương án. Test đạt P@5=0,110687; Recall@5=0,324427; Hit@5=0,477099; mAP@5=0,228255; nDCG@5=0,278866. Chi tiết protocol, giới hạn và cấu hình ở `docs/muc4.md`, số liệu gốc ở `docs/task4_evaluation.json`.

## Bổ sung RMBG-2.0 cho ảnh upload

Đã tích hợp phương pháp từ repo `DucHai278/Fish-Image-Retrieval-System`, model `briaai/RMBG-2.0` revision `6a88d6a65119856a743be87ec1e6bee6f08e1f93`, CPU, đầu vào 1024×1024, alpha mềm ghép nền trắng trước letterbox. Tham số và nguồn: `docs/background-removal.md`, `src/fish_features/background_profile.json`.

**36 kiểm thử Python đạt**, `pip check` không báo xung đột. Bộ mới kiểm tra alpha/composite, thứ tự xử lý trước letterbox, bypass ảnh chuẩn, lỗi thiếu model không fallback âm thầm, tham số RGB Normalize/1024 bằng torch stub, API và việc bỏ qua model cho query chọn bằng ID dataset.

Đã tải model bằng credential Hugging Face do người dùng đăng nhập trên máy và **chạy model thật qua API** với ảnh cá trên nền xám xanh: mask trước xử lý chiếm 100%, sau xử lý 27,6592%; không còn cảnh báo chạm biên/occupancy bất thường và trả đủ top5. Thời gian RMBG lần thử khoảng 59,8 giây CPU. Kết quả gốc ở `outputs/background-check/summary.json` và `result.json`. Đây là phép thử có kiểm soát trên một ảnh, không thay thế đánh giá ảnh mạng có nhãn.

Web có nút bật/tắt RMBG, trạng thái model và các preview trước/sau. Số liệu holdout mục 4 vẫn giữ nguyên và chỉ áp dụng dataset đã chuẩn hóa, không coi là số liệu đánh giá RMBG.

## Giới hạn tổng thể

Các kết quả trên xác nhận quy trình trích rút và quản trị dữ liệu chạy được trên dataset, không phải đánh giá chất lượng truy hồi. Không có cảnh báo tự động không chứng minh 1.000 mặt nạ đều hoàn hảo. Số 323 là số mã loài trong tên file, chưa có bước kiểm chứng nhãn sinh học. Các thông số cơ sở và tám nhóm vector còn cần được đánh giá khi thực hiện mục 4.
