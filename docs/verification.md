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

## Ý nghĩa và giới hạn của kết quả

Các kết quả trên xác nhận quy trình trích rút và quản trị dữ liệu chạy được trên dataset, không phải đánh giá chất lượng truy hồi. Không có cảnh báo tự động không chứng minh 1.000 mặt nạ đều hoàn hảo. Số 323 là số mã loài trong tên file, chưa có bước kiểm chứng nhãn sinh học. Các thông số cơ sở và tám nhóm vector còn cần được đánh giá khi thực hiện mục 4.
