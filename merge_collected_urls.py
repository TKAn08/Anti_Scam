"""
merge_collected_urls.py
Gộp các file URL thu thập (collected_url_01, collected_url_02,...) thành dataset chuẩn hóa.
Áp dụng cấu trúc schema Giai đoạn 1:
  - url_hash: SHA-256 của normalized_url
  - normalized_url: URL đã chuẩn hóa (bỏ www., lowercase host/scheme, bỏ trailing slash, bỏ fragment)
  - original_url: URL gốc ban đầu
  - domain: tên miền dùng để group train/test
  - label: 0 (website an toàn / thật)
  - source: nguồn thu thập (kết hợp nếu trùng nhiều nguồn)
  - collected_at: ngày thu thập
  - normalizer_ver: phiên bản chuẩn hóa (v2)
"""

import argparse
import glob
import hashlib
import os
import re
from datetime import date
from urllib.parse import urlsplit
import pandas as pd


def normalize_url(raw_url: str) -> str:
    """
    Chuẩn hóa URL theo quy tắc v2:
    - Loại khoảng trắng đầu/cuối
    - Bổ sung scheme nếu thiếu
    - Lowercase scheme và netloc (hostname)
    - Loại cổng mặc định (:80, :443)
    - Loại tiền tố 'www.' ở netloc để tránh lệch nguồn
    - Cắt bỏ fragment (#...)
    - Bỏ dấu '/' ở cuối path (nếu có)
    """
    if not isinstance(raw_url, str):
        return ""
    u = raw_url.strip()
    if not u:
        return ""
    
    # Bổ sung scheme nếu URL thiếu scheme
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", u):
        u = "http://" + u

    try:
        parsed = urlsplit(u)
    except Exception:
        return ""

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Bỏ cổng mặc định
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Bỏ tiền tố www.
    if netloc.startswith("www.") and len(netloc) > 4:
        netloc = netloc[4:]

    # Chuẩn hóa path: bỏ dấu gạch chéo cuối
    path = parsed.path.rstrip("/")

    # Query params
    query = parsed.query

    normalized = f"{scheme}://{netloc}{path}"
    if query:
        normalized += f"?{query}"
    return normalized


def extract_domain(netloc: str, domain_src: str = None) -> str:
    """Lấy domain chính xác, ưu tiên domain_src nếu có."""
    if isinstance(domain_src, str) and domain_src.strip():
        d = domain_src.strip().lower()
        if d.startswith("www."):
            d = d[4:]
        return d
    
    # Fallback từ netloc
    if not netloc:
        return ""
    host = netloc.split(":")[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def compute_sha256(text: str) -> str:
    """Tính mã SHA-256 cho chuỗi text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def process_files(file_paths, label=0, default_date=None, normalizer_version="v2"):
    if default_date is None:
        default_date = date.today().isoformat()

    records = []
    total_raw_rows = 0

    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"[CẢNH BÁO] Không tìm thấy file: {file_path}")
            continue

        source_name = os.path.basename(file_path)
        print(f"Đang đọc: {file_path} ...")
        
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"[LỖI] Đọc file {file_path} thất bại: {e}")
            continue

        total_raw_rows += len(df)

        for _, row in df.iterrows():
            orig_url = str(row.get("url", "")).strip()
            if not orig_url or orig_url.lower() == "nan":
                continue

            norm_url = normalize_url(orig_url)
            if not norm_url:
                continue

            domain_src = row.get("domain_src", None)
            parsed = urlsplit(norm_url)
            domain = extract_domain(parsed.netloc, domain_src)

            url_hash = compute_sha256(norm_url)

            records.append({
                "url_hash": url_hash,
                "normalized_url": norm_url,
                "original_url": orig_url,
                "domain": domain,
                "label": int(label),
                "source": source_name,
                "collected_at": default_date,
                "normalizer_ver": normalizer_version
            })

    if not records:
        print("[LỖI] Không có bản ghi hợp lệ nào được xử lý.")
        return pd.DataFrame(), total_raw_rows

    raw_df = pd.DataFrame(records)
    print(f"Tổng số bản ghi đọc được (trước khi khử trùng): {len(raw_df)}")

    # Gộp và khử trùng lặp theo url_hash
    def aggregate_sources(sources_series):
        unique_srcs = sorted(set(sources_series.dropna().tolist()))
        return "|".join(unique_srcs)

    clean_df = raw_df.groupby("url_hash", as_index=False).agg({
        "normalized_url": "first",
        "original_url": "first",
        "domain": "first",
        "label": "first",
        "source": aggregate_sources,
        "collected_at": "first",
        "normalizer_ver": "first"
    })

    # Đảm bảo đúng thứ tự cột của schema Giai đoạn 1
    ordered_cols = [
        "url_hash",
        "normalized_url",
        "original_url",
        "domain",
        "label",
        "source",
        "collected_at",
        "normalizer_ver"
    ]
    clean_df = clean_df[ordered_cols]
    clean_df["label"] = clean_df["label"].astype("int8")

    return clean_df, total_raw_rows


def main():
    parser = argparse.ArgumentParser(description="Gộp và chuẩn hóa các file URL thu thập (Schema Giai đoạn 1)")
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=None,
        help="Danh sách các file đầu vào (mặc định: tự động quét toàn bộ data/collected/collected_url_*)"
    )
    parser.add_argument(
        "--out-parquet",
        default="data/interim/collected_merged.parquet",
        help="Đường dẫn file parquet đầu ra"
    )
    parser.add_argument(
        "--out-csv",
        default="data/interim/collected_merged.csv",
        help="Đường dẫn file csv đầu ra (để xem thử)"
    )
    parser.add_argument("--label", type=int, default=0, help="Nhãn (0: an toàn, 1: lừa đảo)")
    parser.add_argument("--date", default=date.today().isoformat(), help="Ngày thu thập (YYYY-MM-DD)")

    args = parser.parse_args()

    # Tạo thư mục đầu ra nếu chưa có
    os.makedirs(os.path.dirname(args.out_parquet), exist_ok=True)
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)

    # Tự động tìm kiếm file nếu không truyền --inputs hoặc truyền wildcard
    resolved_files = []
    if not args.inputs:
        matched = sorted(glob.glob("data/collected/collected_url_[0-9]*"))
        resolved_files = [f for f in matched if not f.endswith(".done")]
    else:
        for item in args.inputs:
            matched = sorted(glob.glob(item))
            if matched:
                resolved_files.extend([f for f in matched if not f.endswith(".done")])
            elif not item.endswith(".done") and os.path.exists(item):
                resolved_files.append(item)
    resolved_files = list(dict.fromkeys(resolved_files))

    if not resolved_files:
        print("[LỖI] Không tìm thấy file dữ liệu nào để gộp trong data/collected/")
        return

    print(f"Các file sẽ được gộp ({len(resolved_files)} file):")
    for f in resolved_files:
        print(f"  - {f}")

    clean_df, total_raw = process_files(
        file_paths=resolved_files,
        label=args.label,
        default_date=args.date,
        normalizer_version="v2"
    )

    if clean_df.empty:
        print("Quá trình kết thúc không tạo ra dữ liệu.")
        return

    # Lưu Parquet
    clean_df.to_parquet(args.out_parquet, index=False)
    print(f"[THÀNH CÔNG] Đã lưu file Parquet: {args.out_parquet}")

    # Lưu CSV
    clean_df.to_csv(args.out_csv, index=False, encoding="utf-8")
    print(f"[THÀNH CÔNG] Đã lưu file CSV: {args.out_csv}")

    # In báo cáo thống kê
    num_clean = len(clean_df)
    num_dups = total_raw - num_clean
    num_domains = clean_df["domain"].nunique()

    print("\n" + "=" * 50)
    print("BÁO CÁO TỔNG HỢP GIAI ĐOẠN 1:")
    print(f"- Tổng số dòng đọc vào: {total_raw:,}")
    print(f"- Số URL trùng lặp đã loại: {num_dups:,} ({num_dups/total_raw*100:.2f}%)")
    print(f"- Số URL sạch duy nhất còn lại: {num_clean:,}")
    print(f"- Số tên miền (domain) duy nhất: {num_domains:,}")
    print(f"- Phân bố nhãn (label 0 / an toàn): {len(clean_df[clean_df['label'] == 0]):,}")
    print("=" * 50)
    print("\nXem trước 5 dòng đầu tiên:")
    print(clean_df.head(5)[["normalized_url", "domain", "label", "source"]])


if __name__ == "__main__":
    main()

