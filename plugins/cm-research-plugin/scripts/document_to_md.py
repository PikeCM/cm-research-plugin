"""Convert a .docx or .pdf to Markdown (body only; the skill adds frontmatter).

Usage: document_to_md.py <input.docx|.pdf> [output.md]
- .docx: headings, paragraphs, bullet/number lists, and tables.
- .pdf : text extraction per page (layout-dependent; review output).
"""
import os
import sys


def docx_to_md(path: str) -> str:
    from docx import Document
    from docx.document import Document as _Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table, _Cell
    from docx.text.paragraph import Paragraph

    def iter_block_items(parent):
        if isinstance(parent, _Document):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._tc
        else:
            return
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    def table_to_md(table) -> str:
        rows = table.rows
        if not rows:
            return ""
        header = [c.text.strip().replace("\n", " ") for c in rows[0].cells]
        out = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
        for r in rows[1:]:
            cells = [c.text.strip().replace("\n", " ") for c in r.cells]
            out.append("| " + " | ".join(cells) + " |")
        return "\n".join(out)

    doc = Document(path)
    lines = []
    for block in iter_block_items(doc):
        if isinstance(block, Table):
            lines.append("")
            lines.append(table_to_md(block))
            lines.append("")
            continue
        text = block.text.strip()
        if not text:
            continue
        style = (block.style.name or "") if block.style else ""
        if style.startswith("Heading"):
            tail = style.split()[-1]
            level = int(tail) if tail.isdigit() else 2
            lines.append("#" * min(level, 6) + " " + text)
        elif "List Bullet" in style:
            lines.append("- " + text)
        elif "List Number" in style:
            lines.append("1. " + text)
        elif style == "Title":
            lines.append("# " + text)
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def pdf_to_md(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    out = []
    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        out.append(f"## Page {i}\n\n{text}\n")
    return "\n".join(out).strip() + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: document_to_md.py <input.docx|.pdf> [output.md]", file=sys.stderr)
        return 2
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".md"
    ext = os.path.splitext(src)[1].lower()

    if ext == ".docx":
        body = docx_to_md(src)
    elif ext == ".pdf":
        body = pdf_to_md(src)
    elif ext == ".doc":
        print("ERROR: legacy .doc is not supported. Save as .docx and retry.", file=sys.stderr)
        return 3
    else:
        print(f"ERROR: unsupported extension {ext}. Use .docx or .pdf.", file=sys.stderr)
        return 3

    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"Wrote {out} ({len(body)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
