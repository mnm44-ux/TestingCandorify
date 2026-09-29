"""Generate docs/Candorify_Project_Plan.pdf from docs/PROJECT_PLAN.md.

Pure standard library — no third-party dependencies — so it runs anywhere.
It renders headings, paragraphs, bullet lists, and Markdown tables into a
multi-page A4 PDF with basic word-wrapping. This is intentionally simple and
self-contained (not a full Markdown engine), tuned for this specific document.

Run:  python3 docs/build_plan_pdf.py
Out:  docs/Candorify_Project_Plan.pdf
"""
from __future__ import annotations

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "PROJECT_PLAN.md")
OUT = os.path.join(HERE, "Candorify_Project_Plan.pdf")

# Page geometry (points; 72 pt = 1 inch). A4 = 595 x 842.
PAGE_W, PAGE_H = 595, 842
MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 50, 50, 55, 55
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

# Helvetica widths are ~0.5-0.55 em on average; use a conservative factor so we
# never overflow the right margin.
def _char_w(size: float) -> float:
    return size * 0.52


def _wrap(text: str, size: float, max_w: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        if (len(cur) + 1 + len(w)) * _char_w(size) <= max_w:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _pdf_escape(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _clean(s: str) -> str:
    """Strip inline markdown and non-latin-1 chars for the core PDF fonts."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)      # bold
    s = re.sub(r"`(.+?)`", r"\1", s)             # code
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", s)  # links -> text
    s = s.replace("—", "-").replace("–", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("↔", "<->").replace("→", "->").replace("≥", ">=").replace("✅", "[x]")
    return s.encode("latin-1", "replace").decode("latin-1")


class PDF:
    """Minimal PDF writer: a stream of text-drawing ops across pages."""

    def __init__(self):
        self.pages: list[list[str]] = []
        self.ops: list[str] = []
        self.y = 0.0
        self._new_page()

    def _new_page(self):
        if self.ops:
            self.pages.append(self.ops)
        self.ops = []
        self.y = PAGE_H - MARGIN_T

    def _ensure(self, needed: float):
        if self.y - needed < MARGIN_B:
            self._new_page()

    def text(self, s: str, x: float, size: float, font: str = "F1", gray: float = 0.0):
        self.ops.append("BT")
        self.ops.append(f"/{font} {size} Tf")
        self.ops.append(f"{gray:.2f} {gray:.2f} {gray:.2f} rg")
        self.ops.append(f"1 0 0 1 {x:.1f} {self.y:.1f} Tm")
        self.ops.append(f"({_pdf_escape(s)}) Tj")
        self.ops.append("ET")

    def rect(self, x: float, y: float, w: float, h: float, gray: float):
        self.ops.append(f"{gray:.3f} {gray:.3f} {gray:.3f} rg")
        self.ops.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re f")
        self.ops.append("0 0 0 rg")

    # ---- high-level blocks ----
    def heading(self, text: str, level: int):
        sizes = {1: 20, 2: 14, 3: 11.5}
        size = sizes.get(level, 11)
        gap_before = 16 if level == 1 else (12 if level == 2 else 8)
        self.y -= gap_before
        for line in _wrap(_clean(text), size, CONTENT_W):
            self._ensure(size + 4)
            self.text(line, MARGIN_L, size, font="F2", gray=0.05 if level == 1 else 0.12)
            self.y -= size + 4
        self.y -= 4

    def paragraph(self, text: str, size: float = 10, indent: float = 0.0,
                  bullet: bool = False, gray: float = 0.15):
        clean = _clean(text)
        x = MARGIN_L + indent
        avail = CONTENT_W - indent - (12 if bullet else 0)
        lines = _wrap(clean, size, avail)
        for i, line in enumerate(lines):
            self._ensure(size + 3)
            if bullet and i == 0:
                self.text("-", x, size, gray=gray)
            bx = x + (12 if bullet else 0)
            self.text(line, bx, size, gray=gray)
            self.y -= size + 3
        self.y -= 2

    def table(self, rows: list[list[str]]):
        if not rows:
            return
        ncol = max(len(r) for r in rows)
        rows = [r + [""] * (ncol - len(r)) for r in rows]
        col_w = CONTENT_W / ncol
        size = 8.5
        pad = 3
        for ridx, row in enumerate(rows):
            cells = [_wrap(_clean(c), size, col_w - 2 * pad) for c in row]
            rh = max(len(c) for c in cells) * (size + 2) + 2 * pad
            self._ensure(rh)
            top = self.y
            # header / zebra background
            if ridx == 0:
                self.rect(MARGIN_L, top - rh + 2, CONTENT_W, rh, gray=0.12)
            elif ridx % 2 == 0:
                self.rect(MARGIN_L, top - rh + 2, CONTENT_W, rh, gray=0.94)
            self._render_row(row, col_w, size, pad, rh, header=(ridx == 0))
            self.y = top - rh
        self.y -= 6

    def _render_row(self, row, col_w, size, pad, rh, header):
        top = self.y
        for ci, cell in enumerate(row):
            cx = MARGIN_L + ci * col_w + pad
            lines = _wrap(_clean(cell), size, col_w - 2 * pad)
            ly = top - pad - size
            for ln in lines:
                self.ops.append("BT")
                self.ops.append(f"/{'F2' if header else 'F1'} {size} Tf")
                g = 0.98 if header else 0.15
                self.ops.append(f"{g:.2f} {g:.2f} {g:.2f} rg")
                self.ops.append(f"1 0 0 1 {cx:.1f} {ly:.1f} Tm")
                self.ops.append(f"({_pdf_escape(ln)}) Tj")
                self.ops.append("ET")
                ly -= size + 2

    def build(self) -> bytes:
        if self.ops:
            self.pages.append(self.ops)
        objs = []
        # 1 catalog, 2 pages, then per page: content + page obj; plus 2 fonts
        n_pages = len(self.pages)
        font_regular = n_pages * 2 + 3
        font_bold = font_regular + 1
        kids = []
        page_objs = []
        content_objs = []
        obj_id = 3
        for content in self.pages:
            stream = "\n".join(content).encode("latin-1", "replace")
            content_objs.append((obj_id, stream))
            page_obj_id = obj_id + 1
            kids.append(page_obj_id)
            page_objs.append((page_obj_id, obj_id, font_regular, font_bold))
            obj_id += 2

        parts = {}
        parts[1] = "<< /Type /Catalog /Pages 2 0 R >>"
        kids_str = " ".join(f"{k} 0 R" for k in kids)
        parts[2] = f"<< /Type /Pages /Count {n_pages} /Kids [{kids_str}] >>"
        for cid, stream in content_objs:
            parts[cid] = ("stream", stream)
        for pid, cid, fr, fb in page_objs:
            parts[pid] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Contents {cid} 0 R /Resources << /Font << /F1 {fr} 0 R /F2 {fb} 0 R >> >> >>"
            )
        parts[font_regular] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        parts[font_bold] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"

        out = bytearray(b"%PDF-1.4\n")
        offsets = {}
        max_id = font_bold
        for oid in range(1, max_id + 1):
            offsets[oid] = len(out)
            val = parts[oid]
            if isinstance(val, tuple) and val[0] == "stream":
                data = val[1]
                out += f"{oid} 0 obj\n<< /Length {len(data)} >>\nstream\n".encode("latin-1")
                out += data
                out += b"\nendstream\nendobj\n"
            else:
                out += f"{oid} 0 obj\n{val}\nendobj\n".encode("latin-1")

        xref_pos = len(out)
        out += f"xref\n0 {max_id + 1}\n".encode("latin-1")
        out += b"0000000000 65535 f \n"
        for oid in range(1, max_id + 1):
            out += f"{offsets[oid]:010d} 00000 n \n".encode("latin-1")
        out += (
            f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF"
        ).encode("latin-1")
        return bytes(out)


def parse_and_render(md: str) -> PDF:
    pdf = PDF()
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("---"):
            i += 1
            continue
        # table block
        if line.lstrip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i])
                i += 1
            rows = []
            for r in block:
                if re.match(r"^\s*\|[\s:|-]+\|\s*$", r):
                    continue  # separator row
                cells = [c.strip() for c in r.strip().strip("|").split("|")]
                rows.append(cells)
            pdf.table(rows)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            pdf.heading(m.group(2), len(m.group(1)))
            i += 1
            continue
        if line.lstrip().startswith(("- ", "* ")):
            pdf.paragraph(line.lstrip()[2:], size=10, indent=6, bullet=True)
            i += 1
            continue
        if line.lstrip().startswith(">"):
            pdf.paragraph(line.lstrip()[1:].strip(), size=10, indent=8, gray=0.4)
            i += 1
            continue
        pdf.paragraph(line, size=10)
        i += 1
    return pdf


def main():
    with open(SRC, encoding="utf-8") as f:
        md = f.read()
    pdf = parse_and_render(md)
    data = pdf.build()
    with open(OUT, "wb") as f:
        f.write(data)
    print(f"Wrote {OUT} ({len(data):,} bytes)")


if __name__ == "__main__":
    main()
