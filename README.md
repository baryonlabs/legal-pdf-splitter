# legal-pdf-splitter

Korean legal document PDF splitter — separates a combined brief + exhibits PDF into individual files.

## What it does

Korean legal briefs (준비서면) are often submitted as a single PDF that includes both the brief text and attached exhibits (을호증, 갑호증). This tool splits that combined file into:

- **`<name>_준비서면.pdf`** — the brief pages only
- **`을제1호증.pdf`**, **`을제2호증.pdf`**, … — one file per exhibit, with multi-page exhibits automatically grouped

## Install

```bash
pip install pypdf
```

## Usage

```bash
python split.py <pdf_file> --brief-pages <N> [--output-dir <dir>]
```

| Argument | Description |
|---|---|
| `pdf` | Path to the input PDF |
| `--brief-pages N` | Number of pages that belong to the brief (exhibits start after page N) |
| `--output-dir` | Output folder (default: same folder as the input PDF) |

## Example

```bash
python split.py brief_2026-05-12.pdf --brief-pages 32
```

Output in the same directory:
```
brief_2026-05-12_준비서면.pdf   (32 pages)
을제4호증.pdf                   (6 pages — auto-grouped sub-exhibits 4-1 ~ 4-6)
을제5호증.pdf                   (2 pages)
을제6호증.pdf
을제7호증.pdf
을제8호증.pdf                   (2 pages)
을제9호증.pdf
```

## How grouping works

Pages are scanned for exhibit labels (e.g. `을 제4-1호증`, `을제4호증-2`). Pages sharing the same base number (e.g. all `을4`) are merged into a single output file. Useful when one exhibit spans multiple screenshot pages.

## Requirements

- Python 3.10+
- pypdf ≥ 4.0.0
