
import argparse
import pandas as pd


def normalize_url(url):
    if pd.isna(url):
        return ""
    return str(url).strip().lower().rstrip("/")


def main():
    parser = argparse.ArgumentParser(
        description="Compare URL columns between two CSV files"
    )

    parser.add_argument("--file1", required=True, help="First CSV file")
    parser.add_argument("--file2", required=True, help="Second CSV file")
    parser.add_argument("--col1", default="url", help="URL column in first CSV")
    parser.add_argument("--col2", default="url", help="URL column in second CSV")
    parser.add_argument("--out", default="data/unique_urls.csv", help="Output CSV")

    args = parser.parse_args()

    df1 = pd.read_csv(args.file1)
    df2 = pd.read_csv(args.file2)

    urls1 = set(df1[args.col1].dropna().map(normalize_url))
    urls2 = set(df2[args.col2].dropna().map(normalize_url))

    # URLs appearing in both files
    common = urls1 & urls2

    # URLs appearing in only one file
    only_file1 = urls1 - urls2
    only_file2 = urls2 - urls1

    print(f"File 1 unique URLs: {len(urls1)}")
    print(f"File 2 unique URLs: {len(urls2)}")
    print(f"Common URLs:       {len(common)}")
    print(f"Only in file 1:    {len(only_file1)}")
    print(f"Only in file 2:    {len(only_file2)}")

    result = pd.DataFrame({
        "url": sorted(only_file1 | only_file2),
        "source": [
            "file1" if url in only_file1 else "file2"
            for url in sorted(only_file1 | only_file2)
        ]
    })

    result.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\nSaved non-overlapping URLs to: {args.out}")


if __name__ == "__main__":
    main()
