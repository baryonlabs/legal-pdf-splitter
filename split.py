#!/usr/bin/env python3
"""
legal-pdf-splitter: Split Korean legal document PDFs into brief + individual exhibits.

Usage:
    python split.py <pdf_file> --brief-pages <N> [--output-dir <dir>]

Example:
    python split.py brief_with_exhibits.pdf --brief-pages 32
    python split.py brief_with_exhibits.pdf --brief-pages 32 --output-dir ./output
"""

import argparse
import os
import re
import sys

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("Error: pypdf is required. Run: pip install pypdf")
    sys.exit(1)


def extract_exhibit_number(text: str) -> str | None:
    """
    Extract exhibit number from page text.
    Matches patterns like:
      을 제1호증, 을 제1-2호증, 을 제1호증-2, 갑 제3호증, etc.
    Returns a normalized key like '을1', '을1-2', '갑3'.
    """
    # Match: 을/갑 + optional space + 제 + number + optional sub-number + 호증
    pattern = r'([을갑])\s*제\s*(\d+)(?:[–\-](\d+))?\s*호증(?:[–\-](\d+))?'
    m = re.search(pattern, text[:200])  # only look at top of page
    if not m:
        return None

    party = m.group(1)          # 을 or 갑
    main = m.group(2)           # main number
    sub_a = m.group(3)          # e.g. "1-2호증" → sub_a=2
    sub_b = m.group(4)          # e.g. "을제1호증-2" → sub_b=2

    # Normalize sub-numbering: treat both forms as same exhibit group
    # 을제1-1호증, 을제1-2호증 → key '을1'
    # 을제1호증-1, 을제1호증-2 → key '을1'
    # 을제2호증 → key '을2'
    key = f"{party}{main}"
    return key


def detect_groups(reader: PdfReader, start_page: int) -> list[tuple[str, list[int]]]:
    """
    Scan pages from start_page onward and group consecutive pages by exhibit number.
    Returns list of (exhibit_key, [page_indices]).
    """
    groups: list[tuple[str, list[int]]] = []
    current_key = None
    current_pages: list[int] = []

    for i in range(start_page, len(reader.pages)):
        text = reader.pages[i].extract_text() or ""
        key = extract_exhibit_number(text)

        if key is None:
            # No exhibit label found — attach to current group or make unnamed
            if current_key is not None:
                current_pages.append(i)
            else:
                # Orphan page — create its own group
                groups.append((f"page{i+1}", [i]))
        elif key != current_key:
            if current_key is not None:
                groups.append((current_key, current_pages))
            current_key = key
            current_pages = [i]
        else:
            current_pages.append(i)

    if current_key is not None and current_pages:
        groups.append((current_key, current_pages))

    return groups


def save_pages(reader: PdfReader, indices: list[int], path: str) -> None:
    writer = PdfWriter()
    for i in indices:
        writer.add_page(reader.pages[i])
    with open(path, "wb") as f:
        writer.write(f)


def exhibit_filename(key: str) -> str:
    """Convert exhibit key like '을1' → '을제1호증.pdf'"""
    m = re.match(r'([을갑])(\d+)', key)
    if m:
        return f"{m.group(1)}제{m.group(2)}호증.pdf"
    return f"{key}.pdf"


def split(pdf_path: str, brief_pages: int, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    total = len(reader.pages)

    print(f"PDF: {os.path.basename(pdf_path)}  ({total} pages total)")
    print(f"Brief: pages 1–{brief_pages}  |  Exhibits: pages {brief_pages+1}–{total}\n")

    # 1. Save brief
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    brief_path = os.path.join(output_dir, f"{stem}_준비서면.pdf")
    save_pages(reader, list(range(brief_pages)), brief_path)
    print(f"✓ 준비서면  →  {os.path.basename(brief_path)}  ({brief_pages}p)")

    # 2. Detect and save exhibits
    groups = detect_groups(reader, brief_pages)
    if not groups:
        print("No exhibits found after the brief pages.")
        return

    for key, indices in groups:
        fname = exhibit_filename(key)
        out_path = os.path.join(output_dir, fname)
        save_pages(reader, indices, out_path)
        print(f"✓ {key}  →  {fname}  ({len(indices)}p)")

    print(f"\n총 {1 + len(groups)}개 파일 생성  →  {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split a Korean legal PDF into brief + individual exhibit files."
    )
    parser.add_argument("pdf", help="Input PDF file path")
    parser.add_argument(
        "--brief-pages", "-n",
        type=int,
        required=True,
        help="Number of pages belonging to the brief (준비서면). Exhibits start after this.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Output directory (default: same directory as the input PDF)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"Error: file not found: {args.pdf}")
        sys.exit(1)

    output_dir = args.output_dir or os.path.dirname(os.path.abspath(args.pdf))
    split(args.pdf, args.brief_pages, output_dir)


if __name__ == "__main__":
    main()
