"""
sitemap_urls.py
Lấy URL thật (có path) từ robots.txt + sitemap.xml của từng domain.
Mỗi domain do 1 luồng xử lý lần lượt, nên mỗi website chỉ nhận vài request.

Đầu vào (--domains): file text, mỗi dòng 1 domain (vd: vietcombank.com.vn)
                     hoặc file Tranco dạng  rank,domain
Chạy thử:
    python sitemap_urls.py --domains data/raw/top-1m.csv --max-rank 10000 --sample 50 --out data/collected/sitemap_test.csv
Chạy thật:
    python sitemap_urls.py --domains data/raw/top-1m.csv --max-rank 100000 --sample 3000 --per-domain 10 --out data/collected/sitemap_01.csv
Dừng bằng Ctrl+C, chạy lại cùng lệnh kèm --resume để tiếp tục.

Cần: pip install requests
Chỉ dùng cho website THẬT. Không dùng để truy cập URL phishing.
"""

import argparse
import csv
import gzip
import html
import os
import random
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

UA = {
    "User-Agent": "anti-scam-research/0.1 (student project; contact: trankhanha53@gmail.com)"
}
UA_NAME = "anti-scam-research"
SKIP_EXT = re.compile(
    r"\.(jpg|jpeg|png|gif|svg|ico|css|js|xml|json|pdf|zip|gz|mp4|mp3|txt|webp)(\?|$)",
    re.I,
)
LOC = re.compile(r"<loc>\s*(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</loc>", re.I | re.S)
MAX_BYTES = 8_000_000  # không đọc file sitemap lớn hơn mức này
STATS = Counter()


# ---------- Mạng ----------
def fetch(url):
    """Trả về bytes, hoặc None nếu lỗi / không phải 200."""
    try:
        r = requests.get(url, headers=UA, timeout=(8, 15), stream=True)
    except requests.RequestException:
        STATS["loi_mang"] += 1
        return None
    try:
        if r.status_code != 200:
            STATS[f"http_{r.status_code}"] += 1
            return None
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > MAX_BYTES:
                break
        return buf
    except requests.RequestException:
        STATS["loi_mang"] += 1
        return None
    finally:
        r.close()


# ---------- Phân tích ----------
def decode(buf):
    if buf[:2] == b"\x1f\x8b":  # file .gz
        try:
            buf = gzip.decompress(buf)
        except Exception:
            return ""
    return buf.decode("utf-8", errors="ignore")


def parse_locs(text):
    return [html.unescape(m) for m in LOC.findall(text)]


def find_robots(domain, fetch_fn):
    """Trả về (host, RobotFileParser, danh sách sitemap trong robots.txt)."""
    for host in (domain, "www." + domain):
        raw = fetch_fn(f"https://{host}/robots.txt")
        if raw is not None:
            rp = RobotFileParser()
            rp.parse(decode(raw).splitlines())
            return host, rp, list(rp.site_maps() or [])
    return None, None, []


def process_domain(domain, per_domain, max_collect, fetch_fn, rng, delay):
    host, rp, sitemaps = find_robots(domain, fetch_fn)
    time.sleep(delay)
    candidates = list(sitemaps[:3])
    if not candidates:  # robots.txt không nêu sitemap -> thử đường dẫn quen thuộc
        for h in ([host] if host else [domain, "www." + domain]):
            candidates.append(f"https://{h}/sitemap.xml")
    queue = [(c, 0) for c in dict.fromkeys(candidates)]
    urls, fetched = [], 0
    while queue and len(urls) < max_collect and fetched < 6:
        sm, depth = queue.pop(0)
        if rp and not rp.can_fetch(UA_NAME, sm):
            STATS["robots_chan"] += 1
            continue
        raw = fetch_fn(sm)
        fetched += 1
        time.sleep(delay)
        if raw is None:
            continue
        text = decode(raw)
        locs = parse_locs(text)
        if (
            "<sitemapindex" in text[:5000].lower()
        ):  # sitemap chỉ mục -> mở vài sitemap con
            if depth < 1:
                for child in rng.sample(locs, min(len(locs), 3)):
                    queue.append((child, depth + 1))
            continue
        for u in locs:
            host_u = (urlsplit(u).hostname or "").lower()
            if (
                u.startswith(("http://", "https://"))
                and len(u) <= 300
                and (host_u == domain or host_u.endswith("." + domain))
                and not SKIP_EXT.search(u)
                and (rp is None or rp.can_fetch(UA_NAME, u))
            ):
                urls.append(u)
    urls = list(dict.fromkeys(urls))
    STATS["co_sitemap" if urls else "khong_co_sitemap"] += 1
    return rng.sample(urls, min(len(urls), per_domain))


# ---------- Đọc danh sách domain ----------
def read_domains(path):
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            rank, dom = (
                (int(parts[0]), parts[1])
                if len(parts) >= 2 and parts[0].isdigit()
                else (None, parts[0])
            )
            dom = re.sub(r"^https?://", "", dom.lower()).strip("/")
            if dom.startswith("www."):
                dom = dom[4:]
            if dom:
                out.append((rank, dom))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-rank", type=int, default=1)
    ap.add_argument("--max-rank", type=int, default=10**9)
    ap.add_argument(
        "--sample", type=int, default=0, help="0 = lấy hết; N = bốc ngẫu nhiên N domain"
    )
    ap.add_argument("--per-domain", type=int, default=5)
    ap.add_argument(
        "--max-collect",
        type=int,
        default=500,
        help="gom tối đa bấy nhiêu URL/domain trước khi bốc mẫu",
    )
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="giây nghỉ giữa các request cùng 1 domain",
    )
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--log-every", type=float, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    done_path = args.out + ".done"
    if os.path.exists(args.out) and not args.resume:
        raise SystemExit(
            f"{args.out} đã tồn tại. Thêm --resume để chạy tiếp, hoặc đổi tên --out."
        )

    items = [
        (r, d)
        for r, d in read_domains(args.domains)
        if r is None or args.min_rank <= r <= args.max_rank
    ]
    domains = list(dict.fromkeys(d for _, d in items))
    if args.sample and args.sample < len(domains):
        domains = random.Random(args.seed).sample(domains, args.sample)

    done = set()
    if args.resume and os.path.exists(done_path):
        done = set(open(done_path, encoding="utf-8").read().split())
    todo = [d for d in domains if d not in done]
    print(
        f"Tổng domain: {len(domains):,} | đã xong: {len(domains) - len(todo):,} | còn lại: {len(todo):,} "
        f"| luồng: {args.workers}"
    )

    def work(d):
        rng = random.Random(f"{args.seed}-{d}")
        try:
            return d, process_domain(
                d, args.per_domain, args.max_collect, fetch, rng, args.delay
            )
        except Exception:
            STATS["loi_xu_ly"] += 1
            return d, []

    n_rows = n_empty = n_done = 0
    t0 = time.time()
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(args.log_every):
            rate = n_done / max(time.time() - t0, 1)
            print(
                f"  [{time.strftime('%H:%M:%S')}] xong {n_done:,}/{len(todo):,} | URL {n_rows:,} | "
                f"không có URL {n_empty:,} | {rate:.2f} domain/s | {dict(STATS)}"
            )

    new_file = not os.path.exists(args.out)
    ex = ThreadPoolExecutor(max_workers=args.workers)
    with open(args.out, "a", newline="", encoding="utf-8") as fo, open(
        done_path, "a", encoding="utf-8"
    ) as fd:
        w = csv.writer(fo)
        if new_file:
            w.writerow(["url", "domain_src", "source_type"])
        futures = [ex.submit(work, d) for d in todo]
        threading.Thread(target=heartbeat, daemon=True).start()
        try:
            for i, fut in enumerate(as_completed(futures), 1):
                n_done = i
                d, picks = fut.result()
                for u in picks:
                    w.writerow([u, d, "sitemap"])
                n_rows += len(picks)
                n_empty += not picks
                fd.write(d + "\n")
                fo.flush()
                fd.flush()
        except KeyboardInterrupt:
            print("\nĐã dừng. Chạy lại cùng lệnh kèm --resume để tiếp tục.")
            fo.flush()
            fd.flush()
            os._exit(0)
        finally:
            stop.set()
    ex.shutdown()
    print(
        f"Xong: {n_rows:,} URL | domain không lấy được URL: {n_empty:,}/{len(todo):,} -> {args.out}"
    )


if __name__ == "__main__":
    main()
