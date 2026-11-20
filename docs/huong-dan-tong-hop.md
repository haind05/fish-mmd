# Tài liệu tổng hợp — Hệ CSDL lưu trữ và tìm kiếm ảnh cá

**Phạm vi:** bài tập lớn môn Hệ cơ sở dữ liệu đa phương tiện, từ dữ liệu và đặc trưng ở mục 1–2 đến triển khai mục 3–4 và giao diện kiểm tra local. Tài liệu mô tả bản mã nguồn hiện tại trên nhánh `main`, bao gồm tiền xử lý ảnh upload bằng RMBG-2.0.

**Đối tượng đọc:** thành viên nhóm tiếp quản mã nguồn, người cài dự án trên máy mới và người cần hiểu/kiểm chứng lựa chọn thực nghiệm. Các câu lệnh bên dưới dùng **Windows PowerShell**, chạy tại **thư mục gốc project** trừ khi nói rõ.

## Mục lục

1. [Dự án làm gì?](#1-dự-án-làm-gì)
2. [Dữ liệu, thuật ngữ và phạm vi yêu cầu](#2-dữ-liệu-thuật-ngữ-và-phạm-vi-yêu-cầu)
3. [Kiến trúc và các luồng xử lý](#3-kiến-trúc-và-các-luồng-xử-lý)
4. [Cấu hình trích rút đặc trưng](#4-cấu-hình-trích-rút-đặc-trưng)
5. [Tiền xử lý ảnh upload bằng RMBG-2.0](#5-tiền-xử-lý-ảnh-upload-bằng-rmbg-20)
6. [Cách tính điểm và chọn top 5](#6-cách-tính-điểm-và-chọn-top-5)
7. [Cách lựa chọn cấu hình và trọng số](#7-cách-lựa-chọn-cấu-hình-và-trọng-số)
8. [Phương pháp đánh giá và kết quả](#8-phương-pháp-đánh-giá-và-kết-quả)
9. [CSDL và tổ chức mã nguồn](#9-csdl-và-tổ-chức-mã-nguồn)
10. [Setup từ đầu trên máy mới](#10-setup-từ-đầu-trên-máy-mới)
11. [Sử dụng web và CLI](#11-sử-dụng-web-và-cli)
12. [Tái lập đánh giá và thử cấu hình mới](#12-tái-lập-đánh-giá-và-thử-cấu-hình-mới)
13. [Kiểm thử và xử lý lỗi thường gặp](#13-kiểm-thử-và-xử-lý-lỗi-thường-gặp)
14. [Giới hạn và các kết luận có thể đưa ra](#14-giới-hạn-và-các-kết-luận-có-thể-đưa-ra)
15. [Tài liệu và bằng chứng đối chiếu](#15-tài-liệu-và-bằng-chứng-đối-chiếu)

## 1. Dự án làm gì?

Hệ thống nhận một ảnh cá, mô tả nội dung ảnh bằng các vector số, so sánh với tập ảnh đã lưu và trả về **5 ảnh gần nhất theo hình dạng, màu sắc và kết cấu**. Đây là tìm kiếm ảnh theo nội dung — Content-Based Image Retrieval, viết tắt CBIR.

Ví dụ: người dùng upload một ảnh cá trên nền xám. Nếu bật tách nền, hệ thống dùng RMBG-2.0 giữ chủ thể, ghép lên nền trắng, đưa ảnh về canvas chuẩn, tính tám nhóm đặc trưng rồi so với gallery. Kết quả gồm năm ảnh, điểm xếp hạng, mặt nạ xử lý và đóng góp của từng nhóm đặc trưng.

Các chức năng chính:

- Trích rút hàng loạt đặc trưng cho dataset; xuất file kết quả và dữ liệu trung gian.
- Quản trị metadata, vector và cấu hình trích rút trong PostgreSQL chạy bằng Docker.
- Duyệt ảnh, tìm theo tên/loài để kiểm tra dữ liệu nguồn.
- Upload ảnh mới hoặc lấy một ảnh dataset làm query để thử truy hồi.
- Giải thích cách tính điểm: vector, khoảng cách, trọng số và tổng đóng góp.
- Đánh giá bằng một protocol holdout tách gallery, validation và test.

Phần **xếp hạng** sử dụng đặc trưng thủ công, không dùng embedding học sâu và không huấn luyện bộ phân loại loài. RMBG-2.0 là mô hình có sẵn, chỉ dùng cho bước **tách nền ảnh upload**. Một ảnh khác loài vẫn có thể được trả về vì giống về ngoại hình; hệ thống không khẳng định nhận dạng được loài của query.

## 2. Dữ liệu, thuật ngữ và phạm vi yêu cầu

### 2.1. Các tài liệu đầu vào

| Tệp | Vai trò |
|---|---|
| `assignment.txt` | Đề bài gốc của giảng viên, quy định các mục 1–5 |
| `BaoCao_BTL.pdf` | Báo cáo đã làm về dataset và các nhóm đặc trưng ở mục 1–2 |
| `images.zip` | Dataset chuẩn hóa, được cung cấp riêng ngoài Git |

Triển khai bám các phương pháp trong PDF. Những mã ảnh minh họa `0001–1000` trong PDF không được tự đồng nhất với thứ tự tên file trong ZIP khi chưa có bảng đối chiếu.

### 2.2. Dataset hiện tại

| Thuộc tính | Giá trị |
|---|---|
| Số ảnh | 1.000 |
| Định dạng | PNG RGB 8-bit |
| Kích thước | 640×320 pixel |
| Bố cục | Một cá thể, nằm ngang, đầu trái, nền trắng |
| Mã loài khác nhau | 323, lấy từ tên file |
| Nội dung pixel riêng biệt đã kiểm tra | 1.000 |
| Ví dụ tên file | `species_101_cheilinus_chlorourus_936.png` |

Từ tên ví dụ, chương trình đọc `species_code=101`, `species_name=cheilinus chlorourus`, `source_image_id=936`. Đây là metadata nguồn, không phải nhãn được hệ thống suy luận. Nhãn chưa được kiểm chứng lại về sinh học.

### 2.3. Các khái niệm dùng trong tài liệu

| Thuật ngữ | Nghĩa trong dự án |
|---|---|
| Query | Ảnh đầu vào cần tìm các ảnh tương đồng |
| Gallery | Tập ảnh tham chiếu được phép xuất hiện trong kết quả |
| Feature/vector | Dãy số mô tả một khía cạnh nội dung ảnh |
| Mask nhị phân | Ảnh 0/1: pixel cá bằng 1, pixel nền bằng 0 |
| Alpha matte | Mặt nạ mềm của RMBG, thể hiện mức độ thuộc chủ thể để ghép nền |
| Relevance | Quy tắc xác định kết quả nào được tính là phù hợp khi đánh giá |
| Validation | Các query dùng để chọn phương án trọng số |
| Test | Các query tách biệt dùng báo cáo kết quả sau khi chọn trọng số |
| `config_id` | SHA-256 của cấu hình trích rút, để tránh trộn các vector khác định nghĩa |
| Dataset fingerprint | Hash của config_id và danh sách tên ảnh/hash file, xác định tập dữ liệu đã dùng |

### 2.4. Đối chiếu yêu cầu của đề bài

| Yêu cầu | Thành phần đáp ứng |
|---|---|
| Mục 3: triển khai trích rút | Các module tiền xử lý, kết cấu, hình dạng, màu sắc và lệnh `extract` |
| Mục 3: CSDL quản trị đặc trưng | PostgreSQL Docker, schema, khóa ngoại, kiểm tra vector, upsert |
| Mục 4: trả top 5 | `query.py`, `retrieval.py`, API upload và giao diện |
| Mục 4a: sơ đồ/module/quy trình | Phần 3 của tài liệu này và `docs/muc4.md` |
| Mục 4b: giá trị trung gian | Mask/contour, bảng vector, khoảng cách từng nhóm, JSON kết quả |
| Mục 4c: đánh giá | `evaluation.py`, protocol và bảng số liệu ở phần 8 |
| Mục 5: hỗ trợ demo | Web local; có thể dùng trình tự demo ở phần 11 |

Nhánh `task/3.0` lưu bản mục 3 trước khi bổ sung truy hồi. Mã nguồn tổng hợp tiếp tục phát triển trên `main`.

## 3. Kiến trúc và các luồng xử lý

### 3.1. Hai công việc độc lập

**Chuẩn bị gallery** thực hiện trước: đọc 1.000 ảnh, trích rút, kiểm tra và ghi CSDL. Không cần tính lại toàn bộ gallery khi người dùng upload một query mới.

**Truy vấn** thực hiện khi người dùng tìm: xử lý một ảnh query, tính vector, lấy gallery cùng cấu hình từ CSDL và xếp hạng. Query không được tự động thêm vào CSDL.

```mermaid
flowchart TD
  subgraph PREP[Chuẩn bị gallery]
    ZIP[images.zip] --> FILES[data/images]
    FILES --> FE[Pipeline đặc trưng mục 3]
    FE --> JSON[JSONL và cấu hình]
    JSON --> DB[(PostgreSQL Docker)]
  end
  subgraph SEARCH[Truy vấn]
    UP[Ảnh upload] --> BG[RMBG nếu bật, ghép nền trắng]
    BG --> CANVAS[Canvas 640x320, lật ngang nếu chọn]
    CANVAS --> QE[Pipeline đặc trưng dùng chung]
    DB --> GI[Gallery cùng config_id, hash nguồn còn hợp lệ]
    GI --> SC[Thống kê chuẩn hóa gallery]
    QE --> DIST[8 khoảng cách theo nhóm]
    GI --> DIST
    SC --> DIST
    DIST --> SUM[Tổng có trọng số D, S=1-D]
    SUM --> TOP[Loại trùng pixel, sắp xếp, lấy top5]
    TOP --> UI[Web: ảnh, giải thích và JSON]
  end
```

### 3.2. Trách nhiệm và đầu vào/đầu ra

| Module | Đầu vào | Xử lý chính | Đầu ra |
|---|---|---|---|
| `preprocessing.py` | Ảnh BGR | Ngưỡng nền trắng, thành phần liên thông, lấp lỗ, contour | Mask, bbox, cảnh báo |
| `texture.py` | Xám + mask | GLCM và Circular Uniform LBP | 20 +59 giá trị |
| `shape.py` | Mask + contour | Hình học, mẫu contour đều theo cung, FFT | 3 +256 +10 giá trị |
| `color.py` | BGR + mask + bbox | HSV, RGB moments, spatial HSV | 192 +9 +1.152 giá trị |
| `extractor.py` | Ảnh + cấu hình | Gọi các module, kiểm tra chiều/giá trị | Một bản ghi đủ tám nhóm |
| `database.py` | JSONL và manifest | Nạp/cập nhật trong transaction, đọc dữ liệu | Bản ghi PostgreSQL |
| `background.py` | Ảnh upload | Inference RMBG và ghép nền trắng | Ảnh nền trắng, alpha, tham số thực thi |
| `query.py` | Byte ảnh, tùy chọn | Chuyển màu, tách nền, letterbox, trích rút, gọi tìm kiếm | Query, top5, preview, timing và cấu hình |
| `retrieval.py` | Gallery, query, profile | Fit scaler, tính khoảng cách và kết hợp | Thứ hạng và giải thích điểm |
| `evaluation.py` | Đặc trưng đã lưu và nhãn nguồn | Chia dữ liệu, chọn trọng số, đo test | Các báo cáo và profile được chọn |
| `web.py`, `web_static/` | HTTP và thao tác người dùng | API, upload, giao diện | Web tại localhost |

Với 1.000 ảnh, chương trình so sánh chính xác với toàn bộ ứng viên bằng NumPy. Chưa sử dụng pgvector hoặc thuật toán tìm lân cận gần đúng. PostgreSQL chịu trách nhiệm lưu trữ và quản trị; NumPy thực hiện phép đo khoảng cách.

## 4. Cấu hình trích rút đặc trưng

### 4.1. Cấu hình cơ sở và cách lựa chọn

Cấu hình nằm trong `src/fish_features/config.py`, phiên bản thuật toán `1.0.0`. Các lựa chọn kế thừa phương pháp và ví dụ trong báo cáo mục 2 để triển khai một baseline nhất quán, có thể tái lập.

**Chưa thực hiện tìm kiếm tối ưu toàn bộ tham số trích rút.** Ví dụ, chưa thử hệ thống nhiều số bin HSV hay nhiều tập hệ số Fourier rồi chọn trên validation. Vì vậy không kết luận 32 mức xám hoặc 12×4×4 bin là tốt nhất; đây là cấu hình cơ sở được giữ cố định trong lần đánh giá trọng số.

Mã cấu hình hiện tại:

```text
dee14083f1e017e28de89081ea10c392b830bb7331a19d6e70459a809c9ee484
```

### 4.2. Tiền xử lý chung

Đọc ảnh nguồn RGB thành BGR trong OpenCV; xử lý ảnh 8-bit trên canvas 640×320. Pixel ứng viên thuộc cá khi ít nhất một kênh màu nhỏ hơn 245. Giữ thành phần liên thông 8 hướng lớn nhất rồi lấp lỗ kín bên trong.

Từ mask, tính contour ngoài và bounding box. Pipeline ghi cảnh báo nếu mask chạm biên, bỏ trên 2% số pixel ứng viên khi chọn thành phần chính hoặc occupancy ngoài [0,05;0,8]. Các cảnh báo giúp xem lại ảnh; không có cảnh báo không có nghĩa mặt nạ chắc chắn hoàn hảo.

Nền xám có thể bị ngưỡng 245 nhận nhầm là cá. Đó là lý do cần RMBG cho ảnh mạng trước khi chạy bộ trích rút này.

### 4.3. Tám nhóm đặc trưng

| Tên trong dữ liệu | Cấu hình | Số chiều | Ý nghĩa |
|---|---|---:|---|
| `glcm` | 32 mức xám, bốn độ dời, năm thống kê/độ dời | 20 | Tương phản và tổ chức sáng tối |
| `ulbp` | Circular P=8, R=1; uniform giữ hướng | 59 | Phân bố mẫu kết cấu cục bộ |
| `geometry` | Aspect Ratio, Solidity, Extent | 3 | Tỷ lệ và mức lấp đầy hình dạng |
| `contour_profile` | 256 mẫu đều theo chiều dài cung | 256 | Biến thiên đường bao quanh cá |
| `fourier` | D2–D11 từ 256 điểm, chia biên độ F1 | 10 | Biểu diễn đường bao trong miền tần số |
| `hsv` | Histogram 3D 12×4×4, chuẩn hóa L1 | 192 | Phân bố màu toàn cục |
| `color_moments` | RGB/255, mean/std/căn bậc ba moment trung tâm bậc ba | 9 | Tóm tắt thống kê màu |
| `spatial_hsv` | 3 cột×2 hàng trên bbox, 192 bin/ô | 1.152 | Phân bố màu theo vị trí tương đối |

Tổng **1.701 giá trị/ảnh**, nhưng tám nhóm được lưu và đo khoảng cách riêng. “1.000 bộ đặc trưng” trong CSDL nghĩa là 1.000 bản ghi ứng với 1.000 ảnh ở cấu hình này; mỗi bản ghi có đủ tám nhóm, không phải chỉ có 1.000 con số.

Các quy ước cần giữ để tái lập:

- GLCM lượng tử hóa `floor(gray×32/256)`. Độ dời theo thứ tự `(0,1),(-1,1),(-1,0),(-1,-1)`; không cộng chuyển vị. Chỉ đếm cặp có cả hai pixel thuộc mask. Mỗi hướng lưu ASM, Contrast, Homogeneity, Correlation, Entropy; entropy log2, correlation bằng 1 khi phương sai biên bằng 0.
- LBP lấy điểm đầu bên phải, duyệt ngược chiều kim đồng hồ trong tọa độ ảnh, nội suy bilinear. Chỉ lấy tâm có toàn bộ pixel tham gia nội suy thuộc cá. 58 mã uniform được gán theo thứ tự mã tăng dần, non-uniform vào bin58; tổng histogram bằng 1.
- Geometry theo thứ tự `[w/h, A/AH, A/(w×h)]`. Diện tích cá và convex hull đều tính bằng pixel raster để cùng đơn vị.
- Contour duyệt theo chiều kim đồng hồ trên ảnh có y hướng xuống, bắt đầu ở điểm trái nhất, nếu trùng x lấy y nhỏ nhất. Lấy 256 điểm đều theo cung; profile là khoảng cách đến tâm diện tích mask chia khoảng cách trung bình.
- Fourier dùng `fft(x+j*y)/N`, không dùng F0; biên độ D2–D11 chia `abs(F1)`. Báo lỗi nếu F1 quá nhỏ, không chia cho 0.
- HSV OpenCV: H∈[0,180), S,V∈[0,256). Trải bin theo thứ tự V thay đổi nhanh nhất, sau đó S rồi H. Chỉ đếm pixel mask.
- Moments theo thứ tự `[μR,μG,μB,σR,σG,σB,τR,τG,τB]`; σ có mẫu số N, τ là căn bậc ba **có dấu** của moment trung tâm bậc ba, không phải skewness chuẩn hóa.
- Spatial chia bbox thành sáu ô, từ trái qua phải ở hàng trên rồi hàng dưới; phần dư chia nguyên đưa vào ô cuối. Mỗi ô chuẩn hóa L1 riêng, tổng vector ghép thường bằng 6, không phải 1.

Chi tiết công thức và liên hệ từng trang PDF nằm trong [muc3.md](muc3.md).

## 5. Tiền xử lý ảnh upload bằng RMBG-2.0

### 5.1. Vì sao có bước này?

Gallery đã có nền trắng, nhưng ảnh lấy từ mạng thường có nền xám, màu hoặc nhiều chi tiết. Chạy trực tiếp ngưỡng 245 trên các ảnh đó có thể đưa cả nền vào mask. RMBG được dùng trước để tạo ảnh nền trắng phù hợp với bộ trích rút hiện có.

Phương pháp tham khảo từ [repo DucHai278](https://github.com/DucHai278/Fish-Image-Retrieval-System/tree/158cbf1700f79794be2c9c75bad79d4980e20bd5/pre-processing-background-removal). Cấu hình riêng nằm trong `src/fish_features/background_profile.json`.

### 5.2. Tham số

| Tham số | Giá trị |
|---|---|
| Phiên bản | `query-rmbg2-1.0.0` |
| Mô hình có sẵn | `briaai/RMBG-2.0` |
| Revision model/code | `6a88d6a65119856a743be87ec1e6bee6f08e1f93` |
| Input model | RGB, resize 1024×1024 |
| Normalize mean/std | `[0.485,0.456,0.406]` / `[0.229,0.224,0.225]` |
| Dự đoán | Output cuối của model → sigmoid → mask về kích thước ảnh gốc |
| Ghép nền | `ảnh×alpha +255×(1−alpha)` |
| Thiết bị | CPU, 4 luồng torch, float32 |

Đã chọn CPU trên máy thử có GPU MX230 2 GB để tránh giả định đủ VRAM. Model nạp một lần trong mỗi tiến trình và inference lần lượt qua khóa dùng chung. Ảnh được xử lý local; lần đầu tải trọng số cần Internet và quyền Hugging Face. Model không tự nhận biết hướng đầu cá.

Thứ tự: đọc/chuyển màu ảnh → RMBG nếu bật → ghép trắng → resize giữ tỉ lệ và letterbox 640×320 → lật ngang nếu chọn → mask và đặc trưng mục 3. Không cắt sát cá hay tự chuẩn hóa diện tích cá thêm ngoài các bước này. Không tự hiệu chỉnh xoay theo EXIF.

Alpha mềm từ RMBG và mask nhị phân để trích rút là hai đối tượng khác nhau. Mask nhị phân vẫn được tính từ ảnh nền trắng để dùng cùng định nghĩa đặc trưng với gallery.

### 5.3. Kiểm chứng đã có

Đã chạy model thật qua web API với một ảnh dataset được thay nền thành xám xanh. Trước xử lý, mask chiếm 100% ảnh và có cảnh báo chạm biên/occupancy. Sau xử lý, mask chiếm **27,6592%**, hết hai cảnh báo và trả đủ top5. Lần thử gồm nạp model trong web mất khoảng **59,8 giây CPU**, không phải cam kết thời gian cho mọi máy hoặc mọi ảnh.

Đây là phép thử có kiểm soát trên một ảnh, không phải đánh giá chất lượng RMBG trên một tập ảnh mạng có nhãn. Nguồn số liệu: [background_check.json](background_check.json).

## 6. Cách tính điểm và chọn top 5

### 6.1. Vì sao không dùng một khoảng cách trên toàn vector ghép?

GLCM có Contrast ở thang khác geometry; spatial có nhiều chiều hơn Fourier. Nếu ghép tất cả và dùng Euclid trực tiếp, thang giá trị và số chiều có thể làm một nhóm chi phối kết quả. Hệ thống đo và đưa từng nhóm về khoảng cách [0,1], rồi kết hợp bằng trọng số rõ ràng.

### 6.2. Độ đo từng nhóm

**HSV và ULBP:** Hellinger giữa hai histogram đã chuẩn hóa L1:

```text
dH(p,q) = sqrt( Σ(sqrt(p_i) − sqrt(q_i))² /2 )
```

**Spatial HSV:** Hellinger từng cặp ô tương ứng rồi lấy trung bình. Ô chỉ có dữ liệu ở một phía nhận d=1. Hai phía cùng rỗng được bỏ khỏi trung bình; nếu không còn ô nào hợp lệ thì khoảng cách nhóm bằng 1. Với dataset hiện tại sáu ô đều có pixel, nên là trung bình sáu khoảng cách.

**GLCM, geometry, Fourier, Color Moment:** fit mean và std tổng thể riêng từng thành phần trên gallery, `ddof=0`. Std<1e−8 được thay bằng 1. Query không tham gia fit.

```text
z_g = (x_g − mean_gallery)/std_gallery
z_q = (x_q − mean_gallery)/std_gallery
r = sqrt( mean((z_g − z_q)²) )
d = r/(1+r)
```

Do dùng cùng mean, code tính tương đương bằng `(x_g−x_q)/std_gallery`. Trường `raw_rms` trong JSON là r trước ánh xạ `r/(1+r)`, sau bước chia std, không phải RMS chưa chuẩn hóa trên vector gốc.

**Contour Profile:** profile đã chia khoảng cách trung bình; tính RMS trực tiếp giữa hai profile rồi `d=r/(1+r)`, không fit thêm std theo từng điểm.

### 6.3. Kết hợp và sắp hạng

```text
D(Q,I) = Σ_g w_g × d_g(Q,I)
S(Q,I) = 1 − D(Q,I)
```

Trọng số không âm và tổng bằng 1. D nhỏ tương ứng S lớn. Chương trình tính điểm với mọi ảnh hợp lệ cùng `config_id`, loại ảnh trùng pixel với query, sắp D tăng dần và lấy 5 ảnh đầu. Khi điểm bằng nhau, giữ thứ tự đường dẫn để tái lập.

S không phải xác suất cùng loài hay phần trăm giống nhau. S=0,71 chỉ có nghĩa điểm gần theo cấu hình này là 0,71.

Loại trùng dùng SHA-256 **pixel sau tiền xử lý**, không dựa vào tên file. Query trùng một ảnh dataset, không qua RMBG, thường còn 999 ứng viên. Sau nén JPEG, RMBG hoặc thay đổi pixel, ảnh có cùng nguồn thị giác có thể không còn trùng hash và không bị loại; đây không phải chống trùng ngữ nghĩa.

### 6.4. Ví dụ đọc bảng giải thích

Trong ví dụ lưu ở [task4_example.json](task4_example.json), ảnh hạng 1 có:

```text
r_geometry = 0,159819...
d_geometry = r/(1+r) = 0,137797...
w_geometry = 0,20
đóng góp geometry = 0,027559...
```

Cộng đóng góp cả tám nhóm cho `D=0,287973277...`, suy ra `S=0,712026723...`. Web hiển thị từng `distance`, `weight`, `contribution`; tải JSON để xem toàn bộ số chưa làm tròn, vector query/kết quả và mean/std cụ thể.

## 7. Cách lựa chọn cấu hình và trọng số

### 7.1. Phân biệt ba loại quyết định

| Loại quyết định | Cách chọn trong bản hiện tại | Có được tối ưu trên validation không? |
|---|---|---|
| Tham số trích rút, như bin HSV và mức xám GLCM | Baseline kế thừa báo cáo mục 2, giữ cố định | Chưa khảo sát nhiều cấu hình |
| Độ đo và chuẩn hóa | Quy tắc triển khai cố định ở phần 6 | Chưa so sánh hệ thống nhiều độ đo |
| Tỷ lệ đặc trưng con trong từng nhóm lớn | Đặt trước làm giả thuyết thử nghiệm | Không tối ưu riêng từng hệ số |
| Trọng số ba nhóm lớn | Thử tám phương án và chọn validation mAP@5 cao nhất | Có, trong phạm vi tám phương án |

Vì vậy, không mô tả rằng mọi tham số hoặc từng trọng số đều đã được “học tối ưu”. Một phần là thiết kế ban đầu; phần chọn ba trọng số lớn mới có bằng chứng so sánh validation.

### 7.2. Tỷ lệ con được đặt trước

Gọi C, H, T lần lượt là tổng trọng số màu sắc, hình dạng và kết cấu, C+H+T=1. Code `evaluation.weights()` ánh xạ:

| Nhóm lớn | Đặc trưng con | Tỷ lệ trong nhóm lớn |
|---|---|---:|
| Màu C | HSV / Spatial HSV / Color Moment | 1/2 /3/8 /1/8 |
| Hình dạng H | Geometry / Fourier / Contour Profile | 1/3 /1/2 /1/6 |
| Kết cấu T | GLCM / ULBP | 1/2 /1/2 |

Các tỷ lệ này dành mức đóng góp lớn hơn cho HSV toàn cục và Fourier trong nhóm tương ứng, giữ các mô tả còn lại để bổ sung thông tin; GLCM và LBP được đối xử ngang nhau. Đây là **giả thuyết thiết kế đặt trước**, không phải kết luận thực nghiệm từng nhóm con tốt hơn nhóm khác. Nếu cần khẳng định vai trò riêng từng đặc trưng, phải bổ sung thí nghiệm bỏ từng nhóm hoặc khảo sát tỷ lệ con.

### 7.3. Tám phương án đã thử

| Tên trong code | C | H | T | mAP@5 validation | Hit@5 validation |
|---|---:|---:|---:|---:|---:|
| `color_only` | 1 | 0 | 0 | 0,075735 | 0,201923 |
| `shape_only` | 0 | 1 | 0 | 0,105061 | 0,278846 |
| `texture_only` | 0 | 0 | 1 | 0,044952 | 0,120192 |
| `balanced` | 1/3 | 1/3 | 1/3 | 0,135243 | 0,307692 |
| `base_40_30_30` | 0,4 | 0,3 | 0,3 | 0,131851 | 0,288462 |
| `color_60` | 0,6 | 0,2 | 0,2 | 0,118737 | 0,259615 |
| **`shape_60`** | **0,2** | **0,6** | **0,2** | **0,152337** | **0,375000** |
| `texture_60` | 0,2 | 0,2 | 0,6 | 0,119872 | 0,254808 |

Chọn `shape_60` vì có mAP@5 validation cao nhất, không chọn theo bảng test. Nếu mAP bằng nhau, code `max()` giữ phương án xuất hiện trước trong danh sách ứng viên.

### 7.4. Cấu hình đang vận hành

Profile nằm tại `src/fish_features/retrieval_profile.json`, phiên bản `retrieval-1.0.0`, topK=5 và bật loại trùng pixel.

| Đặc trưng | Trọng số cuối cùng |
|---|---:|
| HSV | 0,100 =10% |
| Spatial HSV | 0,075 =7,5% |
| Color Moment | 0,025 =2,5% |
| Geometry | 0,200 =20% |
| Fourier | 0,300 =30% |
| Contour Profile | 0,100 =10% |
| GLCM | 0,100 =10% |
| ULBP | 0,100 =10% |
| **Tổng** | **1,000** |

Một số số trong JSON có dạng `0.19999999999999998` do biểu diễn floating point. Chúng tương ứng các tỷ lệ trong bảng; mã kiểm tra tổng bằng 1 với dung sai số học.

## 8. Phương pháp đánh giá và kết quả

### 8.1. Query nào được xem là có kết quả phù hợp?

Đánh giá dùng quy tắc: ảnh gallery **cùng `species_code` với query** là relevant. Nhãn chỉ được dùng sau xếp hạng để tính chỉ số, không dùng trong tính khoảng cách hoặc lọc ứng viên.

Đây là nhãn thay thế cho tương đồng thị giác. Cá khác loài có thể giống về màu/dáng; cá cùng loài có thể khác ngoại hình. Chưa có tập nhãn thị giác do người đánh giá, nên các chỉ số không đo hoàn toàn đúng khái niệm “trông giống” trong mọi trường hợp.

### 8.2. Chia gallery, validation và test

Sắp tên loài/mã loài và tên ảnh ổn định, dùng NumPy `default_rng(42)`:

- Loài ≥3 ảnh: một query test, một query validation, còn lại vào gallery.
- Loài đúng 2 ảnh: một query test, một ảnh gallery, không có query validation.
- Loài một ảnh: chỉ đưa vào gallery, vì không có ảnh cùng loài khác để đánh giá truy hồi.

| Tập/nhóm | Số lượng |
|---|---:|
| Toàn bộ ảnh | 1.000 |
| Gallery đánh giá | 530 |
| Query validation | 208 |
| Query test | 262 |
| Loài một ảnh, chỉ trong gallery | 61 |
| Loài hai ảnh | 54 |
| Loài từ ba ảnh trở lên | 208 |

Ba tập ảnh không giao nhau. Đây là chia **ảnh trong từng loài**, không phải chia ba tập loài tách biệt. Validation và test kiểm tra query mới của những loài còn ảnh tham chiếu trong gallery.

### 8.3. Thứ tự thực nghiệm để tránh dùng test chọn cấu hình

1. Lấy đặc trưng đúng `config_id` từ CSDL.
2. Chia dữ liệu như trên.
3. Fit mean/std trên **530 ảnh gallery** duy nhất.
4. Tính khoảng cách cho **208 query validation** với gallery đó.
5. Đánh giá tám phương án, chọn bằng mAP@5 validation.
6. Giữ nguyên trọng số và scaler gallery, đánh giá **262 query test**.
7. Báo cáo phương án được chọn và các phương án đối chiếu, không đổi lựa chọn sau khi xem test.

Không có bước huấn luyện mô hình nhận dạng loài của nhóm. “Fit” ở đây chủ yếu là tính thống kê chuẩn hóa gallery; RMBG là model đã được huấn luyện bên ngoài và không tham gia lần đánh giá trên dataset chuẩn hóa.

### 8.4. Định nghĩa năm chỉ số

Với một query, gọi R là tổng số ảnh relevant trong gallery, `rel(k)` bằng 1 khi ảnh hạng k relevant, ngược lại bằng 0.

```text
Precision@5 = số relevant trong top5 /5
Recall@5    = số relevant trong top5 /R
Hit@5       = 1 nếu top5 có ít nhất một relevant, ngược lại 0

P@k         = số relevant trong k kết quả đầu /k
AP@5        = Σ(k=1..5)[P@k × rel(k)] / min(R,5)
mAP@5       = trung bình AP@5 của các query

DCG@5       = Σ(k=1..5)[rel(k)/log2(k+1)]
IDCG@5      = DCG khi min(R,5) ảnh relevant xếp đầu
nDCG@5      = DCG@5 /IDCG@5
```

Quy ước AP cắt ngọn dùng mẫu số **min(R,5)**. Một thư viện khác dùng mẫu số R có thể cho số khác; phải thống nhất định nghĩa khi so sánh. Các chỉ số cuối cùng lấy trung bình theo query, không cộng toàn bộ hits rồi thay cho mean recall/AP.

Ví dụ R=3, top5 có relevance `[1,0,1,0,0]`: Precision=2/5=0,4; Recall=2/3; Hit=1; AP=(1+2/3)/3≈0,5556. nDCG dùng DCG=1+1/log2(4)=1,5, chia IDCG=1+1/log2(3)+1/log2(4).

### 8.5. Kết quả test đã đo

| Phương án | P@5 | Recall@5 | Hit@5 | mAP@5 | nDCG@5 |
|---|---:|---:|---:|---:|---:|
| **Được chọn: C20/H60/T20** | **0,110687** | **0,324427** | **0,477099** | **0,228255** | **0,278866** |
| Chỉ màu | 0,048092 | 0,138041 | 0,213740 | 0,099650 | 0,122248 |
| Chỉ hình dạng | 0,076336 | 0,216285 | 0,320611 | 0,145367 | 0,181829 |
| Chỉ kết cấu | 0,035878 | 0,104326 | 0,164122 | 0,065744 | 0,084318 |
| Ba nhóm bằng nhau | 0,093893 | 0,275445 | 0,408397 | 0,194922 | 0,238573 |

Hit@5=0,477099 nghĩa là **125/262 query** có ít nhất một ảnh cùng loài trong top5, không có nghĩa 47,71% số ảnh trả về đều đúng. P@5=0,110687 nghĩa là tỷ lệ relevant trong năm kết quả chỉ khoảng 11,07%, trung bình khoảng 0,553 ảnh cùng loài/query. Hai chỉ số đo hai khía cạnh khác nhau nên cùng tồn tại là bình thường.

Số ảnh cùng loài trong gallery thường ít; nếu một query chỉ có một ảnh relevant thì P@5 tối đa cũng chỉ là 0,2 dù tìm được ảnh đó. Vì vậy cần đọc đồng thời Precision, Recall, Hit, AP và nDCG.

### 8.6. Vận hành khác đánh giá như thế nào?

| Bối cảnh | Gallery | Nguồn query | Scaler |
|---|---|---|---|
| Đánh giá holdout | 530 ảnh | 208 validation hoặc 262 test không nằm trong gallery | Fit trên 530 ảnh |
| Web/CLI tìm kiếm thực tế | Đủ 1.000 ảnh đúng cấu hình hiện có | Upload mới hoặc ảnh thư viện để demo | Fit trên 1.000 ảnh |

Điểm S live có thể khác điểm của cùng ảnh trong báo cáo holdout vì gallery và std thay đổi. Không lấy kết quả tự truy vấn trên gallery1000 để thay thế số liệu test độc lập.

Đã thử ba query bằng cách loại toàn bộ loài của query khỏi gallery, hệ thống vẫn trả top5. Đó là kiểm tra hoạt động với loài chưa có, chưa có thước đo relevance thị giác cho open-set để kết luận chất lượng.

### 8.7. File kết quả và tái lập

`docs/task4_evaluation.json` là bản tóm tắt đã lưu cùng source. Lệnh `evaluate` tạo:

| File trong thư mục output đánh giá | Nội dung |
|---|---|
| `summary.json` | Tham số, counts, tám ứng viên, số liệu validation/test, scaler và fingerprint |
| `splits.json` | Tên từng ảnh thuộc gallery/validation/test |
| `selected_profile.json` | Trọng số được chọn, có thể đưa vào tìm kiếm |
| `validation_queries.json` | Top5 và chỉ số từng query validation cho từng ứng viên |
| `test_queries.json` | Top5 và chỉ số từng query test của selected và đối chiếu |

Dataset fingerprint đã dùng:

```text
16f0dc3e0a545ddee0a4b05220055b133609e6d941ed8b6c7dee0428674c734f
```

Đã chạy lại evaluation và đối chiếu số liệu validation, test và selected profile cho kết quả khớp chính xác trong môi trường thử. Thời gian thực thi có thể khác, không phải dữ liệu cần khớp.

## 9. CSDL và tổ chức mã nguồn

### 9.1. CSDL lưu những gì?

Ảnh nằm ở `data/images`, PostgreSQL lưu đường dẫn tương đối và vector. Ba bảng:

| Bảng | Nội dung và khóa |
|---|---|
| `images` | `image_id`, đường dẫn duy nhất, hash file/pixel, kích thước, metadata loài |
| `extraction_configs` | `config_id`, tham số JSONB, số chiều các nhóm |
| `image_features` | Tám mảng float8, metadata, hash nguồn và thời gian; khóa kép `(image_id,config_id)` |

Khóa ngoại ngăn đặc trưng mồ côi. Xóa ảnh trong bảng `images` sẽ cascade đặc trưng liên quan. Trigger kiểm tra số chiều theo cấu hình, vector một chiều, không có NULL/NaN/vô cực. View `feature_catalog` chỉ hiện bộ đặc trưng còn khớp hash file nguồn hiện tại.

Nạp dùng transaction cho cả batch; lỗi làm rollback lần nạp. Upsert theo đường dẫn và ảnh+cấu hình giúp nạp lặp không nhân đôi. Khi nội dung file ảnh thay đổi, các đặc trưng cũ không còn khớp ảnh được loại trước khi nạp mới. Nạp một tập con không tự xóa các ảnh khác.

### 9.2. Cấu trúc thư mục

```text
assignment.txt, BaoCao_BTL.pdf   Cơ sở đề bài và báo cáo mục 1–2
images.zip                     Dataset cung cấp riêng, không nằm trong Git
requirements.txt               Dependency cốt lõi
requirements-dev.txt           Cốt lõi + pytest + pypdf
requirements-background.txt    Cốt lõi + torch/transformers/... cho RMBG
pyproject.toml                 Cài package fish_features
compose.yaml                   PostgreSQL Docker + healthcheck + volume
run-web.ps1                    Khởi động DB và web sau khi setup
src/fish_features/
  config.py                    Cấu hình trích rút
  preprocessing.py             Mask, contour, bbox
  texture.py, shape.py, color.py Các thuật toán đặc trưng
  extractor.py                 Pipeline dùng chung gallery/query
  database.py                  Đọc/nạp CSDL
  background.py                RMBG-2.0 và ghép trắng
  background_profile.json      Cấu hình tiền xử lý query
  query.py                     Điều phối tìm kiếm ảnh đầu vào
  retrieval.py                 Khoảng cách, chuẩn hóa và xếp hạng
  retrieval_profile.json       Cấu hình trọng số đang dùng
  evaluation.py                Chia tập và đánh giá
  __main__.py                  CLI
  web.py, web_static/          HTTP server, HTML/CSS/JavaScript
sql/                           Schema và ví dụ truy vấn
tests/                         Kiểm thử thuật toán, HTTP, CSDL
scripts/                       Kiểm tra trình duyệt và inference thật
docs/                          Tài liệu, số liệu và ví dụ đã lưu
data/images/                   Ảnh sau giải nén, sinh tại máy setup
outputs/                       Kết quả trích rút, truy vấn, đánh giá, preview
```

`images.zip`, `data/`, `outputs/`, `.venv/`, `.env` được bỏ qua bởi Git. Clone mã nguồn không tự có dataset, CSDL hoặc model. Không sao chép `.venv` sang máy khác để thay bước cài dependency.

## 10. Setup từ đầu trên máy mới

### 10.1. Điều kiện chuẩn bị

- Windows, PowerShell, Git nếu lấy source bằng Git.
- **Python 3.14 64-bit** là môi trường đã kiểm thử cho toàn bộ bản hiện tại. Metadata của phần core cho phép ≥3.11, nhưng bộ dependency RMBG được pin theo môi trường thử; với phiên bản Python/OS khác cần kiểm tra khả năng cài wheel tương ứng.
- Docker Desktop đang bật, dùng Linux containers; lệnh `docker compose` hoạt động.
- Bản mã nguồn **đầy đủ mục 3–4 và RMBG**; dataset `images.zip` được bàn giao riêng.
- Internet cho tải package/Docker image/model lần đầu. Nếu dùng RMBG, tài khoản Hugging Face có quyền truy cập đúng model và đủ RAM/dung lượng đĩa cho PyTorch/model/cache. Không bắt buộc GPU vì cấu hình mặc định dùng CPU.

Không cần cài PostgreSQL trực tiếp, không cần Node.js để chạy web. Node/Chrome/Playwright chỉ dùng cho script QA trình duyệt tùy chọn.

### 10.2. Nhận source và dataset

Nếu bản tổng hợp đã được đẩy lên repository:

```powershell
git clone https://github.com/haind05/fish-mmd.git
cd fish-mmd
git switch main
```

Hoặc giải nén bản ZIP bàn giao rồi mở terminal tại thư mục chứa `pyproject.toml`, `compose.yaml`. Lệnh clone chỉ tải những gì đã commit/push; không chứa thay đổi còn nằm trong working tree của máy phát triển. Trước khi bàn giao cần bảo đảm bản nhận có `src/fish_features/query.py`, `background.py`, `evaluation.py` và các file profile tương ứng; không dùng nhánh backup `task/3.0` để chạy các chức năng mới.

Đặt `images.zip` vào cùng thư mục gốc, không đổi tên các ảnh trong ZIP.

```powershell
python --version
docker --version
docker compose version
```

Nếu máy có nhiều Python, dùng đúng executable Python 3.14; ví dụ `py -3.14 -m venv .venv` thay cho `python -m venv .venv` ở bước kế tiếp.

### 10.3. Tạo môi trường và cài phần core

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pip install -e .
```

Không cần activate virtualenv; các lệnh dùng trực tiếp executable trong `.venv`. Cài editable `-e .` để Python tìm package dưới `src/`.

### 10.4. Khởi động PostgreSQL Docker

Mở Docker Desktop, đợi engine sẵn sàng rồi chạy:

```powershell
docker compose up -d --wait
docker compose ps
```

Kết quả mong đợi: service `db` healthy. Mặc định:

| Tham số | Giá trị |
|---|---|
| Image | `postgres:17` |
| Host từ ứng dụng/DBeaver | `127.0.0.1` |
| Port host | `5433` |
| Port PostgreSQL trong container | `5432` |
| Database | `fish_features` |
| User | `fish` |
| Password local | `fish_local` |

Không cần tạo `.env` khi dùng mặc định. Nếu đổi thông tin qua `.env` theo `.env.example`, phải đặt `DATABASE_URL` tương ứng cho Python; xem phần 13.

### 10.5. Giải nén và trích rút gallery

```powershell
.venv/Scripts/python -m fish_features unpack
.venv/Scripts/python -m fish_features extract
```

Ảnh được giải nén vào `data/images`. Không chạy RMBG cho dataset chuẩn hóa. Lệnh `extract` mặc định xử lý toàn bộ, lưu preview 5 ảnh đầu và tạo `outputs/default/features.jsonl`, `config.json`, `summary.json`.

Kiểm tra file tổng kết:

```powershell
Get-Content -Encoding UTF8 outputs/default/summary.json
```

Mong đợi `total=1000`, `success=1000`, `failed=0`. Lần đo trước mất khoảng 395,6 giây, máy khác có thể nhanh/chậm hơn. Nếu có lỗi, xem danh sách `errors` trước khi nạp CSDL; pipeline có thể vẫn tạo file cho các ảnh thành công.

### 10.6. Tạo schema và nạp dữ liệu

```powershell
.venv/Scripts/python -m fish_features db-init
.venv/Scripts/python -m fish_features db-load
.venv/Scripts/python -m fish_features db-stats
```

Mong đợi `images=1000`, `species=323`, và `feature_sets` có 1.000 bản ghi ở config_id đã nêu. `db-init` và `db-load` có thể chạy lại với dữ liệu hợp lệ, không tạo thêm bản trùng theo ảnh+cấu hình.

### 10.7. Cài tách nền cho ảnh mạng

Nếu chỉ thử ảnh đã có nền trắng, có thể bỏ qua bước này và **bỏ chọn checkbox RMBG trên web**. Nếu muốn upload ảnh mạng có nền:

```powershell
.venv/Scripts/python -m pip install -r requirements-background.txt
.venv/Scripts/hf auth login
```

Trước đó, dùng tài khoản của chính người setup được cấp quyền tại [briaai/RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0). Nhập token trực tiếp vào lời nhắc terminal; không ghi vào source hoặc gửi vào chat. Việc thêm token vào Git credential không bắt buộc cho cách tải model này.

```powershell
.venv/Scripts/python -m fish_features bg-check
.venv/Scripts/python -m fish_features bg-check --load
```

`bg-check` chỉ kiểm tra trạng thái. `--load` tải/nạp model, phải đợi hoàn tất. `state=loaded` nghĩa là model đã nạp trong tiến trình kiểm tra; tiến trình web vẫn nạp riêng từ cache ở lần dùng đầu. Cache nằm trong cấu hình Hugging Face của máy, không được mang theo khi clone Git.

Chi tiết và điều kiện truy cập model xem [background-removal.md](background-removal.md) cùng trang model chính thức.

### 10.8. Khởi động web

```powershell
.venv/Scripts/python -m fish_features.web
```

Mở **http://127.0.0.1:8000**. Giữ terminal này chạy; `Ctrl+C` dừng web. Web chỉ bind localhost, không được public lên Internet. Nếu cổng bận, dùng `--port 8001` rồi mở URL cổng8001.

Sau khi đã setup đầy đủ, những lần mở lại chỉ cần bật Docker Desktop và:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-web.ps1
```

Script khởi động DB và web; không thay cho các bước giải nén/trích rút/tạo schema/nạp dữ liệu. ExecutionPolicy trên chỉ áp dụng cho tiến trình lệnh này. Nếu web đang chạy sẵn, chỉ mở URL, không khởi động thêm một server cùng cổng.

## 11. Sử dụng web và CLI

### 11.1. Trình tự demo nên dùng

1. Mở web, kiểm tra thống kê 1.000 ảnh và CSDL đã kết nối.
2. Duyệt thư viện, mở một ảnh để xem tám nhóm và các giá trị hình học.
3. Bấm “Dùng ảnh này tìm tương đồng”; luồng này không chạy RMBG và loại chính ảnh trùng pixel khỏi kết quả.
4. Upload ảnh mạng, bật RMBG; nếu đầu hướng phải thì chọn lật ngang.
5. Xem lần lượt ảnh trước xử lý, alpha, ảnh nền trắng, mask và đường bao; nếu sai mask thì chưa diễn giải top5.
6. Mở “Giải thích điểm” ở một kết quả để chỉ ra d, w và w×d; mở đối chiếu vector query/kết quả.
7. Tải JSON và xem cấu hình/đánh giá cuối trang.

Upload chấp nhận ảnh 8-bit tối đa10MiB, tối đa20 megapixel sau giải mã. Ảnh xám được đổi thành ba kênh; ảnh alpha ghép nền trắng. RMBG được bật mặc định trên web cho upload, có thể tắt cho ảnh chuẩn. Ảnh nên chỉ có một cá thể; chữ, người, nhiều cá hoặc nền phức tạp có thể làm phân đoạn không như mong muốn.

### 11.2. Lệnh tìm kiếm

```powershell
# Ảnh chuẩn từ dataset, không dùng RMBG:
.venv/Scripts/python -m fish_features search data/images/species_101_cheilinus_chlorourus_936.png --output outputs/query.json

# Ảnh mạng, có tách nền:
.venv/Scripts/python -m fish_features search test.jpg --background rmbg2 --output outputs/query-rmbg.json

# Ảnh đầu hướng phải:
.venv/Scripts/python -m fish_features search test.jpg --background rmbg2 --flip --output outputs/query-flipped.json
```

CLI mặc định không RMBG, khác checkbox upload mặc định bật trên web. Cần chỉ rõ `--background rmbg2` khi dùng ảnh mạng.

JSON query có `query.features`, metadata, preview, tham số tiền xử lý, profile, mean/std gallery, fingerprint, timing và `results`. Mỗi kết quả có `rank`, `distance`, `similarity`, `components` và vector của ảnh đó. Query không tự lưu vào PostgreSQL.

### 11.3. Xem CSDL bằng terminal

```powershell
docker compose exec db psql -U fish -d fish_features
```

Trong psql:

```sql
\dt
SELECT COUNT(*) FROM images;
SELECT COUNT(*) FROM image_features;
SELECT relative_path, aspect_ratio, solidity, extent FROM feature_catalog LIMIT 5;
\q
```

Nếu psql hiện `(END)`, bấm `q` để thoát trình xem trang. Có thể kết nối DBeaver bằng thông tin phần10.4. `image_id` là định danh tự sinh, không dùng nó thay mã ảnh minh họa trong PDF.

## 12. Tái lập đánh giá và thử cấu hình mới

### 12.1. Chạy đánh giá hiện tại

Sau khi đã nạp đủ CSDL:

```powershell
.venv/Scripts/python -m fish_features evaluate --output outputs/evaluation
```

Lệnh tạo các file ở phần8.7, không sửa gallery, không gọi RMBG và không tự ghi đè profile đang dùng trên web. So sánh counts, config_id và dataset fingerprint với bản báo cáo trước khi so sánh chỉ số.

Muốn thử profile được chọn ở output mà chưa sửa mặc định:

```powershell
.venv/Scripts/python -m fish_features search data/images/species_101_cheilinus_chlorourus_936.png --profile outputs/evaluation/selected_profile.json --output outputs/query-selected.json
```

Sau khi đã đối chiếu và chủ động chọn dùng, có thể sao chép profile đó vào mặc định:

```powershell
Copy-Item outputs/evaluation/selected_profile.json src/fish_features/retrieval_profile.json
```

Lưu một bản profile cũ nếu cần so sánh. Khi thay cấu hình/thuật toán, nên khởi động lại web để tránh dùng model hoặc bộ nhớ đệm từ lần chạy cũ.

### 12.2. Thử trọng số khác

`evaluate` không đánh giá tùy ý mỗi vector trọng số trong file profile như một phương án mới. Danh sách ứng viên nằm ở `evaluation.candidate_profiles()`, với tỷ lệ con ở `evaluation.weights()`. Tùy chọn `--profile` của evaluate xác định cấu hình trích rút và dữ liệu cơ sở, không thay danh sách tám ứng viên thành trọng số tùy ý.

Nếu mở rộng khảo sát, chỉnh danh sách ứng viên trước, giữ nguyên split/tiêu chí và chỉ dùng validation để chọn. Nếu đã nhiều lần nhìn test rồi điều chỉnh phương án, các số liệu test đó không còn là một lần kiểm chứng cuối độc lập; cần protocol hoặc tập kiểm tra mới khi đưa ra kết luận mạnh hơn.

### 12.3. Thử tham số đặc trưng khác

Ví dụ muốn GLCM16 mức và HSV8×4×4, tạo `config-custom.json`:

```json
{"gray_levels":16,"hsv_bins":[8,4,4]}
```

Chạy:

```powershell
.venv/Scripts/python -m fish_features extract --config config-custom.json --output outputs/custom
.venv/Scripts/python -m fish_features db-load --input outputs/custom/features.jsonl
```

Đọc `config_id` mới trong `outputs/custom/config.json`, tạo một bản retrieval profile có `feature_config_id` tương ứng rồi đánh giá bằng `evaluate --profile <profile-mới>`. Query sẽ đọc lại tham số trích rút tương ứng từ CSDL. Không so sánh vector mới với vector cấu hình cũ hoặc sửa manifest sau trích xuất để giả lập config_id khác.

Nếu thay **công thức thuật toán**, tăng `algorithm_version`, trích lại và đánh giá lại. Sửa JSON trọng số không tự đổi công thức Hellinger/RMS trong code. Các phiên bản profile, kết quả và điều kiện thực nghiệm cần được ghi lại cùng nhau.

## 13. Kiểm thử và xử lý lỗi thường gặp

### 13.1. Kiểm thử

```powershell
# Core/HTTP; test CSDL cần cờ bên dưới:
.venv/Scripts/python -m pytest -q

# Sau khi DB healthy và đã db-init:
$env:RUN_DB_TESTS='1'
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m pip check
```

Lần kiểm chứng đầy đủ có **36 test đạt** với dependency RMBG và CSDL sẵn sàng. Một số test bỏ qua nếu không bật cờ CSDL hoặc không có torch/torchvision. Test inference adapter dùng torch stub kiểm tra quy ước xử lý, không thay thế chạy trọng số pretrained thật.

QA trình duyệt tùy chọn: cài `playwright` vào `.venv`, có Chrome trên máy và web đang chạy:

```powershell
.venv/Scripts/python -m pip install playwright
.venv/Scripts/python scripts/verify_web_browser.py
.venv/Scripts/python scripts/verify_retrieval_browser.py
```

Kiểm tra RMBG thật qua API, cần model đã có quyền và cache:

```powershell
.venv/Scripts/python scripts/verify_background_inference.py
```

Script thay nền một ảnh dataset thành xám xanh rồi gọi model thật qua web; xuất ảnh, JSON và summary trong `outputs/background-check/`. `verify_background_result_ui.py` dùng lại response thật đã lưu để kiểm tra render, không infer lại CPU. Các script QA dùng cổng8000; nếu mở web cổng khác phải điều chỉnh URL trong script.

### 13.2. Chẩn đoán nhanh

| Hiện tượng | Kiểm tra và xử lý |
|---|---|
| `No module named fish_features` | Dùng `.venv/Scripts/python`; chạy lại `pip install -e .` tại gốc project |
| Không có `.venv/Scripts/python.exe` | Tạo môi trường và cài theo phần10.3, không dùng script run-web trước setup |
| Docker báo không kết nối engine/named pipe | Mở Docker Desktop, đợi engine, dùng Linux containers, chạy lại Compose |
| DB khởi động nhưng Python không kết nối | Kiểm tra cổng5433, user/db, `DATABASE_URL` và `docker compose ps` |
| CSDL chưa có bảng | Chạy `db-init` sau khi DB healthy |
| Thư viện ảnh hoặc feature count bằng0 | Kiểm tra đã unpack/extract/db-load và dùng đúng CSDL |
| Không có config_id cần tìm | Profile trỏ sai cấu hình hoặc chưa nạp vector cấu hình đó |
| Không thấy ảnh dù có bản ghi | Cần dataset tại `data/images` với đúng tên/đường dẫn; CSDL không chứa file PNG |
| Cổng8000 bị chiếm | Dùng server đang chạy hoặc `web --port 8001`; không bật hai server cùng cổng |
| `missing_dependencies` | Cài `requirements-background.txt` trong đúng `.venv` |
| `needs_login` / lỗi quyền RMBG | Xin quyền bằng đúng tài khoản, `hf auth login`, kiểm tra `bg-check --load` |
| `not_loaded` | Có điều kiện để thử nạp, chưa phải model đã sẵn sàng; nạp/đợi lần đầu |
| CLI đã `loaded` nhưng web còn phải nạp | Hai tiến trình khác nhau; web đọc trọng số cache và nạp riêng |
| Chờ lâu khi upload có RMBG | CPU inference có thể hàng chục giây; xem trạng thái, chưa bấm gửi lặp |
| Mask trắng gần toàn ảnh, `unusual_occupancy` | Nền bị nhận nhầm là cá; bật RMBG hoặc thay ảnh đầu vào, kiểm tra preview |
| `mask_touches_border` | Mask chạm biên; có thể ảnh bị cắt hoặc phân đoạn cả nền, không tự kết luận cá được tách đúng |
| Top5 khác số liệu minh họa | Kiểm tra dataset, profile, có bật RMBG/flip không, gallery530 hay1000, normalizer/fingerprint |

`.env` chỉ được Compose đọc tự động. Python không tự nạp `.env`. Nếu đổi thông tin kết nối, đặt biến trong terminal chạy Python/web:

```powershell
$env:DATABASE_URL='postgresql://fish:fish_local@127.0.0.1:5433/fish_features'
```

Khi đổi `POSTGRES_PORT`, sửa port trong URL; khi đổi user/password/db phải sửa tương ứng. Thay user/password trong Compose không tự đổi tài khoản bên trong volume PostgreSQL đã khởi tạo.

### 13.3. Dừng và giữ dữ liệu

`Ctrl+C` dừng web trong terminal. `docker compose stop` dừng DB; `docker compose start` bật lại container. Named volume giữ dữ liệu PostgreSQL qua việc dừng/tạo lại container. **Không dùng `docker compose down -v` nếu cần giữ dữ liệu**, vì `-v` xóa volume.

Khi bàn giao máy khác cần cả source và dataset; có thể tái tạo CSDL bằng trích rút/nạp lại. Các file kết quả trong `outputs/` và model cache không đi theo Git. Báo cáo số liệu cần giữ các JSON có fingerprint và cấu hình tương ứng nếu muốn đối chiếu lịch sử.

## 14. Giới hạn và các kết luận có thể đưa ra

**Đã có bằng chứng:** pipeline trích đủ 1.000 ảnh, CSDL giữ đúng vector, truy vấn trả đủ top5 và giải thích điểm; kết hợp C20/H60/T20 đứng đầu tám phương án trên validation và cho bảng test đã công bố; RMBG thật xử lý được trường hợp nền xám xanh trong phép thử có kiểm soát.

**Chưa có bằng chứng để khẳng định:** mọi tham số trích rút đều tối ưu; hệ thống nhận dạng loài chính xác cao; S là xác suất; RMBG luôn tách đúng mọi ảnh mạng; số liệu holdout đại diện chất lượng ảnh mạng; sự hơn kém giữa các phương án có ý nghĩa thống kê trên mọi lần chia dữ liệu.

Các giới hạn cần nêu khi trình bày:

- Chỉ một seed chia dữ liệu, chưa có khoảng tin cậy hoặc đánh giá nhiều lần chia.
- Loài singleton không có query đánh giá cùng loài; kết quả chủ yếu là closed-set cho loài có ≥2 ảnh.
- Nhãn cùng loài chỉ là proxy; cần thêm đánh giá thị giác thủ công để đo đúng “tương đồng nội dung”.
- Feature thủ công mất thông tin: histogram mất vị trí chi tiết, Fourier bỏ pha và phần phổ, profile nhạy với contour.
- Chuẩn hóa tư thế, vị trí, kích thước hoa văn và mặt nạ ảnh hưởng kết quả; chưa tự phát hiện hướng đầu hoặc xử lý nhiều cá.
- RMBG là phân đoạn chủ thể tổng quát; có thể giữ cả chữ/bóng hoặc bỏ vây, cần xem alpha và mask.
- CPU xử lý RMBG chậm hơn nhiều so với xếp hạng vector. Không dùng thời gian xếp hạng vài chục ms để mô tả tổng thời gian xử lý ảnh mạng.

Các bước có thể khảo sát tiếp: nhiều seed hoặc cross-validation phù hợp dữ liệu ít ảnh/loài; đánh giá bỏ từng feature; khảo sát bin/GLCM/Fourier; tập query ảnh mạng có nhãn; đánh giá relevance thị giác và chất lượng mask. Những việc này chưa phải kết quả đã hoàn thành trong bản hiện tại.

## 15. Tài liệu và bằng chứng đối chiếu

| Tài liệu/tệp | Nội dung |
|---|---|
| [muc3.md](muc3.md) | Công thức đặc trưng, schema và đối chiếu báo cáo mục 2 |
| [muc4.md](muc4.md) | Thuyết minh theo yêu cầu 4a–4c, ví dụ đóng góp điểm |
| [background-removal.md](background-removal.md) | Nguồn repo, revision, cài model và luồng RMBG |
| [verification.md](verification.md) | Các lần kiểm chứng triển khai |
| [task4_evaluation.json](task4_evaluation.json) | Tham số, validation/test và lựa chọn đã đo |
| [task4_example.json](task4_example.json) | Ví dụ query/top5, vector và normalizer đầy đủ |
| [background_check.json](background_check.json) | Bằng chứng phép thử RMBG thật trên nền xám xanh |
| `src/fish_features/config.py` | Nguồn sự thật cho cấu hình trích rút |
| `src/fish_features/retrieval_profile.json` | Nguồn sự thật cho trọng số mặc định đang dùng |
| `src/fish_features/background_profile.json` | Nguồn sự thật cho cấu hình tiền xử lý upload |

Tài liệu mô tả một snapshot của dự án; khi sửa code, cấu hình hoặc dataset, cần chạy kiểm chứng/đánh giá tương ứng và cập nhật số liệu thay vì giữ nguyên các con số cũ.
