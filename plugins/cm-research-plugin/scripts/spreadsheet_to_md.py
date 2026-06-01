"""Convert a .csv, .xls, or .xlsx to Markdown tables (body only; skill adds frontmatter).

Usage: spreadsheet_to_md.py <input.csv|.xls|.xlsx> [output.md] [max_rows]
- One section per sheet (workbooks), with a row/column summary and a Markdown table.
- Large sheets are truncated to max_rows (default 1000) with a note.
"""
import os
import sys

import pandas as pd

DEFAULT_MAX_ROWS = 1000


def df_to_section(name: str, df: pd.DataFrame, max_rows: int) -> str:
    rows, cols = df.shape
    parts = [f"## {name}", "", f"- Rows: {rows} | Columns: {cols}", f"- Columns: {', '.join(map(str, df.columns))}", ""]
    view = df.head(max_rows).fillna("")
    parts.append(view.to_markdown(index=False))
    if rows > max_rows:
        parts.append("")
        parts.append(f"> Truncated to the first {max_rows} of {rows} rows. See the original file for the full dataset.")
    parts.append("")
    return "\n".join(parts)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: spreadsheet_to_md.py <input.csv|.xls|.xlsx> [output.md] [max_rows]", file=sys.stderr)
        return 2
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".md"
    max_rows = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_MAX_ROWS
    ext = os.path.splitext(src)[1].lower()

    if ext == ".csv":
        sheets = {"Data": pd.read_csv(src)}
    elif ext in (".xls", ".xlsx"):
        # sheet_name=None returns an ordered dict of all sheets
        sheets = pd.read_excel(src, sheet_name=None)
    else:
        print(f"ERROR: unsupported extension {ext}. Use .csv, .xls, or .xlsx.", file=sys.stderr)
        return 3

    sections = [df_to_section(name, df, max_rows) for name, df in sheets.items()]
    body = "\n".join(sections).strip() + "\n"
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"Wrote {out} ({len(sheets)} sheet(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
