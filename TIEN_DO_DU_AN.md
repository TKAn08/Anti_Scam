# AI Anti-Scam – Tiến độ dự án

Cập nhật 17/11/2026 · Đề tài: phát hiện và cảnh báo website giả mạo, lừa đảo bằng phân tích URL và hình ảnh

Chú thích: `[x]` đã xong · `[ ] 🔄` đang làm hoặc làm dở · `[ ]` sắp tới

## 1. Pipeline tổng thể

URL cần kiểm tra được chia thành hai nhánh rồi gộp kết quả:

- Nhánh URL: trích xuất đặc trưng → mô hình Random Forest / XGBoost / ANN → điểm rủi ro URL.
- Nhánh hình ảnh: chụp ảnh website → phát hiện logo (YOLO), so sánh giao diện với trang chính thức (CLIP), đọc văn bản (PaddleOCR) → điểm rủi ro hình ảnh.
- Kết hợp: phân tích rủi ro đa phương thức → cảnh báo An toàn / Nghi ngờ / Lừa đảo.

Thứ tự thực hiện: A. Dữ liệu URL → B. Mô hình URL → C. Dữ liệu hình ảnh → D. Mô hình hình ảnh → E. Kết hợp → F. Đánh giá, báo cáo, demo.

## 2. Tóm tắt hiện trạng

- Đang ở Phần A (dữ liệu URL): đã làm sạch được bộ dữ liệu đầu tiên, đang bổ sung nguồn URL thật và chuẩn bị thêm nguồn phishing.
- Phần B đến F chưa bắt đầu.
- Mốc số liệu (lần chạy đầu của `import_dataset.py`): đọc 450,176 URL thật và 54,807 URL phishing, còn lại 496,670 URL sạch (444,228 thật, 52,442 phishing) trên 199,794 domain. Đã loại 8,209 URL trùng, tách 48 URL xung đột nhãn, có 67 domain xuất hiện ở cả hai nhãn.
- Phát hiện quan trọng: lệch nguồn ở `www` (80.6% URL thật có `www` so với 3.1% URL phishing). Đã sửa chuẩn hóa ở bản v2 của script.

## 3. Phần A – Dữ liệu URL

### A1. Thu thập

- [x] Chốt phạm vi đề tài (URL + hình ảnh) và vẽ sơ đồ quy trình.
- [x] Cài môi trường Python (`.venv`, pandas, openpyxl, pyarrow, requests) và tạo thư mục `data/raw`, `data/collected`.
- [x] Có hai file dữ liệu gốc: URL thật (CSV) và URL phishing (Excel, sheet Phishing URLs).
- [x] Tải danh sách Tranco top-1m để lấy mẫu domain thật.
- [x] Viết `cc_sample_urls.py` (lấy URL từ Common Crawl) và `sitemap_urls.py` (lấy URL từ robots.txt và sitemap).
- [x] Chạy `sitemap_urls.py` cho nhóm hạng thấp: 3,129 URL từ 3,000 domain (1,951 domain không lấy được URL).
- [ ] 🔄 Common Crawl: `list_url_01.csv` mới có kết quả dở, tạm dừng vì lỗi kết nối khi chạy 4 luồng.
- [ ] 🔄 Các dải hạng còn lại của `sitemap_urls.py` (top 1k, 1k–10k, 10k–100k): chưa xác nhận đã chạy.
- [ ] Phân tích vì sao 65% domain không ra URL, rồi vá script (thêm đường dẫn sitemap, thử http, lấy link từ trang chủ).
- [ ] Thêm 1 đến 2 nguồn phishing (OpenPhish, Phishing.Database, nguồn Việt Nam), ghi giấy phép và ngày tải.

### A2. Làm sạch

- [x] Viết `import_dataset.py`: đọc nhiều file, chuẩn hóa, hash SHA-256, loại trùng, tách xung đột nhãn, xuất báo cáo.
- [x] Chạy lần đầu và đọc báo cáo.
- [x] Sửa chuẩn hóa bản v2 (bỏ `www`), hỗ trợ nhiều nguồn và file `.txt`, thêm bảng so sánh theo nguồn.
- [ ] Chạy lại `import_dataset.py` v2 với tất cả nguồn URL thật và ghi lại số liệu mới.
- [ ] Xem `label_conflicts.csv` và quyết định cách xử lý từng nhóm.

### A3. Kiểm tra và chia dữ liệu

- [ ] Lấy mẫu kiểm tay nhãn (200 đến 500 URL mỗi nguồn).
- [ ] Viết notebook EDA và các phép thử lệch nguồn.
- [ ] Giới hạn số URL mỗi domain, chia train/test theo domain, khóa tập test.
- [ ] Đóng gói dataset v1 kèm file mô tả (datasheet).

## 4. Phần B – Mô hình URL

- [ ] Hàm trích xuất đặc trưng trên `normalized_url` (NumDots, UrlLength, NumDash, AtSymbol, IpAddress, HttpsInHostname, PathLevel, PathLength, NumNumericChars...).
- [ ] Baseline Random Forest / LightGBM / XGBoost với `class_weight`.
- [ ] Đánh giá bằng recall, precision, PR-AUC và tỉ lệ false positive trên tập test chia theo domain.
- [ ] Vẽ learning curve để biết có cần thêm dữ liệu.
- [ ] Thử chéo nguồn (train nguồn A, test nguồn B) và test ngoài bằng bộ đặc trưng có sẵn.
- [ ] Thử ANN và so sánh với mô hình cây.
- [ ] Lưu mô hình kèm phiên bản dataset, tham số và log metric.

## 5. Phần C – Dữ liệu hình ảnh

- [ ] Chốt 30 đến 100 thương hiệu mục tiêu (ưu tiên Việt Nam) kèm danh sách domain chính thức.
- [ ] Dựng bộ chụp ảnh bằng Playwright trong môi trường cách ly, lưu cả ảnh và HTML.
- [ ] Lọc ảnh rác (trang trắng, 404, đỗ tên miền, chặn bot).
- [ ] Chụp ảnh trang thật từ các URL sitemap đã thu thập.
- [ ] Chụp ảnh trang phishing ngay sau khi tải feed, vì trang chết rất nhanh.
- [ ] Dựng bộ tham chiếu thương hiệu: logo chính thức và ảnh trang đăng nhập thật.
- [ ] Gắn nhãn thương hiệu bị giả mạo cho mẫu phishing.
- [ ] Tìm bộ dữ liệu công khai có ảnh chụp để bổ sung (kiểm tra giấy phép).

## 6. Phần D – Mô hình hình ảnh

- [ ] OCR bằng PaddleOCR và danh sách từ khóa (đăng nhập, mật khẩu, OTP, tài khoản bị khóa...).
- [ ] CLIP: vector hóa trang cần kiểm tra và so với bộ tham chiếu thương hiệu.
- [ ] YOLO một lớp "logo" (gán khung vài nghìn ảnh), dùng CLIP để nhận ra thương hiệu.
- [ ] Đánh giá riêng từng mô-đun trước khi kết hợp.

## 7. Phần E – Kết hợp (fusion)

- [ ] Lấy điểm dự đoán out-of-fold của từng mô hình con để tránh rò rỉ.
- [ ] Luật thương hiệu: giao diện giống thương hiệu A nhưng domain không thuộc A.
- [ ] Mô hình kết hợp (Logistic Regression hoặc GBM) trên các điểm và luật.
- [ ] So sánh ba cấu hình: chỉ URL, chỉ hình ảnh, kết hợp.

## 8. Phần F – Đánh giá, báo cáo, demo

- [ ] Test theo thời gian bằng dữ liệu thu thập mới nhất.
- [ ] Đo false positive ở tỉ lệ nhãn gần thực tế (phishing chỉ chiếm vài phần trăm).
- [ ] Báo cáo đề tài: phương pháp, kết quả, hạn chế, vấn đề đạo đức khi thu thập.
- [ ] Demo hoặc tiện ích cảnh báo cho người dùng.

## 9. Vấn đề tồn đọng và rủi ro

- Chỉ có một nguồn phishing, nên dễ học dấu vân tay của nguồn thay vì học phishing.
- Common Crawl bị lỗi kết nối khi tăng lên 4 luồng, nên tạm dừng và chuyển sang lấy URL qua sitemap.
- Chỉ khoảng 35% domain hạng thấp có sitemap, nên URL thu được thiên về website xây dựng bài bản.
- Chưa có danh sách thương hiệu mục tiêu, trong khi cả nhánh hình ảnh phụ thuộc vào nó.
- Chưa xác nhận đã chạy lại `import_dataset.py` bản v2 trên toàn bộ dữ liệu.

## 10. Ưu tiên kế tiếp

1. Đọc dòng thống kê cuối của `sitemap_urls.py` để biết lý do 1,951 domain không ra URL.
2. Chạy lại `import_dataset.py` v2 với mọi nguồn URL thật hiện có và ghi lại số liệu.
3. Thêm một nguồn phishing thứ hai và so sánh hai nguồn.
4. Làm EDA và các phép thử lệch nguồn.
5. Chốt danh sách thương hiệu mục tiêu.

## 11. File và thư mục dự án

- `import_dataset.py`: gộp, chuẩn hóa, loại trùng, báo cáo.
- `cc_sample_urls.py`: lấy URL thật từ Common Crawl (tạm dừng).
- `sitemap_urls.py`: lấy URL thật từ sitemap.
- `data/raw`: file gốc, chỉ thêm không sửa (`URL dataset.csv`, `Phishing URLs.xlsx`, `top-1m.csv`).
- `data/collected`: URL thu thập thêm (`list_url_01.csv`, `sm_tail.csv`...).
- `output`: `dataset_clean.parquet`, `label_conflicts.csv`, `invalid_urls.csv`, `report.txt`.