# Quy trình xử lý dataset URL (kèm checklist)

Cập nhật 17/11/2026 · Dự án AI Anti-Scam · Nhánh phân tích URL

Chú thích: `[x]` đã làm · `[ ] 🔄` làm dở hoặc chưa xác nhận · `[ ]` chưa làm

## 1. Mục tiêu và nguyên tắc

- Mục tiêu là một dataset sạch, không trùng, có nhãn đáng tin, đa dạng nguồn, để train và đánh giá mô hình trung thực.
- Nhãn chỉ có hai loại: 0 là thật, 1 là phishing. Nguồn (`source`) là thông tin về nơi lấy dữ liệu, không đưa vào mô hình.
- Không bao giờ sửa file gốc; mọi thay đổi đi qua script để chạy lại được.
- Phải xử lý trùng và xung đột ở bước nhập dữ liệu, không để đến lúc train.
- Chia train/test theo domain để điểm số không bị cao ảo.

## 2. Bước 0 – Chuẩn bị môi trường

- [x] Cài Python, tạo môi trường ảo `.venv`.
- [x] Cài pandas, openpyxl, pyarrow, requests.
- [x] Tạo cấu trúc thư mục `data/raw` và `data/collected`.
- [ ] Tạo thêm `data/interim`, `data/processed` (có phiên bản) và `notebooks`.

## 3. Bước 1 – Thu thập và lưu dữ liệu thô

- [x] Lưu hai file gốc: `URL dataset.csv` (URL thật, 450,176 dòng) và `Phishing URLs.xlsx` (URL phishing, 54,807 dòng).
- [x] Tải Tranco `top-1m.csv` để lấy mẫu domain thật theo dải hạng.
- [x] Lấy URL thật bổ sung qua sitemap cho nhóm hạng thấp: `sm_tail.csv` (3,129 URL từ 3,000 domain).
- [ ] 🔄 Lấy URL thật qua Common Crawl: `list_url_01.csv` mới có kết quả dở, đang tạm dừng.
- [ ] 🔄 Lấy URL thật qua sitemap cho các dải top 1k, 1k–10k, 10k–100k: chưa xác nhận.
- [ ] Ghi lại cho mỗi nguồn: tên, link, giấy phép, ngày tải, có URL đầy đủ hay chỉ domain.
- [ ] Thêm ít nhất một nguồn phishing thứ hai (OpenPhish, Phishing.Database, nguồn Việt Nam), tải và đặt tên file kèm ngày.
- [ ] Lấy thêm URL thật có path dài, trang đăng nhập thật của ngân hàng và ví điện tử (hard negatives) và website Việt Nam.

## 4. Bước 2 – Thống nhất cấu trúc (schema)

- [x] Gắn nhãn theo từng file (thật = 0, phishing = 1) và gắn `source` theo tên file.
- [x] Đọc được CSV, Excel và file `.txt` (mỗi dòng một URL), nhận nhiều file cho mỗi nhãn.
- [ ] Thêm cột `collected_at` (ngày thu thập) để sau này chia train/test theo thời gian.
- [ ] Thêm cột thương hiệu bị giả mạo cho mẫu phishing (cần cho nhánh hình ảnh).

## 5. Bước 3 – Chuẩn hóa URL

- [x] Loại khoảng trắng, hạ chữ thường scheme và hostname, bỏ cổng mặc định, bỏ fragment, bỏ dấu `/` cuối path.
- [x] Bản v2: bỏ tiền tố `www.` để tránh lệch nguồn và gộp URL trùng; lưu `normalizer_version`.
- [ ] 🔄 Chạy lại `import_dataset.py` bản v2 trên toàn bộ dữ liệu: chưa xác nhận kết quả.
- [ ] Bổ sung: bỏ tham số theo dõi (`utm_*`, `fbclid`...), sắp xếp tham số query, chuyển tên miền Unicode sang Punycode.
- [ ] Dùng `tldextract` để tách domain đăng ký thay vì chỉ lấy hostname.
- Ghi nhớ: mỗi lần đổi quy tắc chuẩn hóa phải tính lại hash cho toàn bộ dữ liệu.

## 6. Bước 4 – Loại trùng và xử lý xung đột nhãn

- [x] Tạo `url_hash` (SHA-256) và loại URL trùng chính xác (lần chạy đầu loại 8,209 URL).
- [x] Tách URL xung đột nhãn ra `label_conflicts.csv` trước khi loại trùng (lần đầu có 48 URL).
- [x] Lưu cột `all_sources` để biết một URL xuất hiện ở những nguồn nào.
- [ ] Xem `label_conflicts.csv`: nhóm nào là nền tảng dùng chung (`github.io`, `sites.google.com`...), nhóm nào là trang bị chiếm quyền, rồi quyết định cách xử lý.
- [ ] Gắn cờ URL gần giống nhau (`similar_group_id`) bằng Levenshtein hoặc MinHash; chỉ gắn cờ, không tự xóa.

## 7. Bước 5 – Kiểm tra chất lượng nhãn

- [ ] Lấy mẫu kiểm tay 200 đến 500 URL mỗi nguồn để ước lượng tỉ lệ nhãn sai (không mở URL phishing bằng trình duyệt thường).
- [ ] Lọc URL thật qua danh sách phishing để loại nhiễu.
- [ ] Xem lại nhóm domain hạng thấp ở phía thật (trang đỗ tên miền, cờ bạc, website bị chiếm quyền).
- [ ] Đánh dấu URL phishing xuất hiện ở từ 2 nguồn trở lên là đáng tin hơn.

## 8. Bước 6 – Kiểm tra lệch nguồn (EDA)

- [x] Bảng so sánh hai nhóm (độ dài URL, có path, có query, https, www) và phát hiện lệch `www` (80.6% so với 3.1%).
- [x] Phát hiện thêm: có path 86.4% (thật) so với 53.0% (phishing); https 79.2% so với 89.2%.
- [ ] Viết notebook EDA: phân bố độ dài, TLD, domain xuất hiện nhiều nhất, số URL mỗi domain.
- [ ] Phép thử 1: train chỉ bằng đặc điểm vô nghĩa về bản chất (có `www`, TLD, độ dài domain); nếu điểm cao bất thường thì dữ liệu đang lệch.
- [ ] Phép thử 2: train trên nguồn A, test trên nguồn B cùng nhãn; điểm tụt mạnh nghĩa là mô hình học nguồn.
- [ ] Nếu còn lệch, lấy mẫu lại phía thật cho gần phân bố với phía phishing ở những đặc điểm do cách thu thập.

## 9. Bước 7 – Giới hạn theo domain và chia tập

- [ ] Giới hạn 5 đến 20 URL mỗi domain, hoặc dùng `sample_weight` bằng 1 chia cho số URL của domain.
- [ ] Chia train/validation/test theo domain (`GroupShuffleSplit` hoặc `GroupKFold`).
- [ ] Chia thêm theo thời gian nếu có `collected_at`: train trên dữ liệu cũ, test trên dữ liệu mới.
- [ ] Khóa (đóng băng) tập test; khi thêm dữ liệu mới phải loại những URL và domain đã thuộc tập test.
- [ ] Viết hàm `validate_dataset`: `url_hash` duy nhất, không xung đột nhãn, train và test không chung domain.

## 10. Bước 8 – Đóng gói và đánh phiên bản

- [x] Xuất `dataset_clean.parquet` cùng `label_conflicts.csv`, `invalid_urls.csv` và `report.txt` (bản đầu).
- [ ] Lưu dataset theo phiên bản (v1, v2...) trong `data/processed`.
- [ ] Viết file mô tả dataset (datasheet): nguồn, ngày tải, giấy phép, số dòng trước và sau làm sạch, số trùng, số xung đột, tỉ lệ nhãn, hạn chế đã biết, phiên bản chuẩn hóa.
- [ ] Ghi phiên bản dataset vào mỗi lần train để kết quả tái lập được.

## 11. Bước 9 – Quy trình mỗi lần cập nhật dataset

Khi có dữ liệu mới, lặp lại theo thứ tự sau (chưa thực hiện lần nào nên cả chuỗi đều chưa tick):

1. [ ] Tải nguồn mới vào `data/raw`, đặt tên kèm ngày.
2. [ ] Chạy `import_dataset.py` với mọi nguồn cũ và mới; đọc `report.txt`.
3. [ ] Xem URL trùng, xung đột nhãn và bảng so sánh theo từng nguồn.
4. [ ] Loại những URL và domain thuộc tập test đã khóa, chia lại phần train.
5. [ ] Chạy `validate_dataset`; lỗi thì dừng, không train.
6. [ ] Train lại trên toàn bộ dữ liệu sạch, so với mô hình cũ trên cùng tập test, chỉ thay mô hình nếu tốt hơn.
7. [ ] Lưu phiên bản mới và cập nhật datasheet.

## 12. Lệnh thường dùng

Gộp và làm sạch (thêm các file nguồn sau `--legit` và `--phish`, cách nhau bằng dấu cách):

```
python import_dataset.py --legit "data/raw/URL dataset.csv" data/collected/sm_tail.csv --phish "data/raw/Phishing URLs.xlsx" --out output
```

Lấy URL thật qua sitemap theo dải hạng:

```
python sitemap_urls.py --domains data/raw/top-1m.csv --min-rank 1 --max-rank 1000 --per-domain 10 --out data/collected/sm_top1k.csv
```

Dừng bằng Ctrl+C một lần, chạy lại cùng lệnh kèm `--resume` để tiếp tục.

## 13. Số liệu mốc hiện tại (lần chạy đầu)

- Đọc vào: 450,176 URL thật, 54,807 URL phishing.
- Loại 5 dòng lỗi, 8,209 URL trùng; tách 48 URL xung đột nhãn.
- Kết quả: 496,670 URL sạch (444,228 thật, 52,442 phishing), tỉ lệ khoảng 8.5 : 1.
- 199,794 domain khác nhau; 67 domain có cả URL thật lẫn phishing.
- Khi chạy lại bản v2, các con số này sẽ thay đổi vì `www` được bỏ; hãy cập nhật lại mục này sau lần chạy đó.