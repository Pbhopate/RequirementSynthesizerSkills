#!/usr/bin/env python3
"""Normalize stakeholder input files into citable markdown text.

Usage:
    python extract_inputs.py <file-or-dir> [<file-or-dir> ...] -o <outdir> [--max-rows 500]

Every input becomes <outdir>/S<n>_<name>.md and a manifest.json maps source IDs
(S1, S2, ...) to the original files. Locators are embedded in the text so that a
requirement can later cite e.g. "S2 @ Sheet1!R14" or "S1 @ 00:12:30" or "S3 @ p4".

Supported: .txt .md .vtt .srt .csv .tsv .xlsx .xlsm .xls .docx .pdf .pptx .json .eml
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys

SUPPORTED = {".txt", ".md", ".vtt", ".srt", ".csv", ".tsv", ".xlsx", ".xlsm", ".xls",
             ".docx", ".pdf", ".pptx", ".json", ".eml", ".log"}


def read_text_file(path):
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def extract_captions(path):
    """VTT / SRT: drop cue numbers and keep '[start] text' lines."""
    raw = read_text_file(path)
    out, ts = [], None
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.upper().startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        m = re.match(r"(\d{1,2}:)?(\d{2}:\d{2})[.,]\d+\s*-->", line)
        if m:
            ts = (m.group(1) or "") + m.group(2)
            continue
        out.append(f"[{ts}] {line}" if ts else line)
    return "\n".join(out)


def extract_delimited(path, delim):
    rows = []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        for r in csv.reader(f, delimiter=delim):
            rows.append(r)
    return rows_to_md("Sheet1", rows, 10 ** 9)


def rows_to_md(sheet, rows, max_rows):
    lines = [f"## Sheet: {sheet}  ({len(rows)} rows)"]
    shown = rows[:max_rows]
    for i, r in enumerate(shown, start=1):
        cells = ["" if c is None else str(c).replace("\n", " / ").strip() for c in r]
        if any(cells):
            lines.append(f"R{i}: " + " | ".join(cells))
    if len(rows) > max_rows:
        lines.append(f"... TRUNCATED: {len(rows) - max_rows} more rows not shown (raise --max-rows)")
    return "\n".join(lines)


def extract_xlsx(path, max_rows):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    parts = []
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        parts.append(rows_to_md(ws.title, rows, max_rows))
    return "\n\n".join(parts)


def extract_xls(path, max_rows):
    try:
        import pandas as pd
        sheets = pd.read_excel(path, sheet_name=None, header=None)
        return "\n\n".join(rows_to_md(n, df.fillna("").values.tolist(), max_rows)
                           for n, df in sheets.items())
    except Exception as e:  # xlrd missing, etc.
        try:
            subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", "/tmp", path],
                           check=True, capture_output=True, timeout=120)
            return extract_xlsx("/tmp/" + os.path.splitext(os.path.basename(path))[0] + ".xlsx", max_rows)
        except Exception:
            return f"[EXTRACTION FAILED for .xls: {e}. Ask the user to re-save as .xlsx]"


def extract_docx(path):
    import docx
    d = docx.Document(path)
    out = []
    # Walk body in order so tables stay next to the paragraphs around them.
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for child in d.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(child, d)
            t = p.text.strip()
            if not t:
                continue
            style = (p.style.name or "") if p.style is not None else ""
            if style.startswith("Heading"):
                lvl = re.sub(r"\D", "", style) or "1"
                out.append("#" * min(int(lvl) + 1, 6) + " " + t)
            else:
                out.append(t)
        elif tag == "tbl":
            tb = Table(child, d)
            out.append("[TABLE]")
            for i, row in enumerate(tb.rows, start=1):
                cells = [c.text.replace("\n", " / ").strip() for c in row.cells]
                out.append(f"T-R{i}: " + " | ".join(cells))
            out.append("[/TABLE]")
    # Comments / tracked changes are often where stakeholders disagree; flag them.
    try:
        xml = d.part.package.part_related_by  # noqa: F841 (probe only)
    except Exception:
        pass
    return "\n".join(out)


def extract_pdf(path):
    pages = []
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for i, pg in enumerate(pdf.pages, start=1):
                pages.append(f"[p{i}]\n" + (pg.extract_text() or ""))
    except Exception:
        r = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
        for i, chunk in enumerate(r.stdout.split("\f"), start=1):
            if chunk.strip():
                pages.append(f"[p{i}]\n{chunk}")
    text = "\n\n".join(pages)
    if len(re.sub(r"\[p\d+\]|\s", "", text)) < 50:
        text += ("\n[WARNING: almost no text layer found - this PDF is probably scanned. "
                 "OCR it (pytesseract + pdf2image) before use.]")
    return text


def extract_pptx(path):
    from pptx import Presentation
    prs = Presentation(path)
    out = []
    for i, slide in enumerate(prs.slides, start=1):
        out.append(f"[slide {i}]")
        for shp in slide.shapes:
            if shp.has_text_frame and shp.text_frame.text.strip():
                out.append(shp.text_frame.text.strip())
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            out.append("Notes: " + slide.notes_slide.notes_text_frame.text.strip())
    return "\n".join(out)


def extract_eml(path):
    import email
    from email import policy
    with open(path, "rb") as f:
        m = email.message_from_binary_file(f, policy=policy.default)
    body = m.get_body(preferencelist=("plain", "html"))
    head = f"From: {m['from']}\nTo: {m['to']}\nDate: {m['date']}\nSubject: {m['subject']}\n"
    return head + "\n" + (body.get_content() if body else "")


def extract(path, max_rows):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".log"):
        return read_text_file(path)
    if ext in (".vtt", ".srt"):
        return extract_captions(path)
    if ext == ".csv":
        return extract_delimited(path, ",")
    if ext == ".tsv":
        return extract_delimited(path, "\t")
    if ext in (".xlsx", ".xlsm"):
        return extract_xlsx(path, max_rows)
    if ext == ".xls":
        return extract_xls(path, max_rows)
    if ext == ".docx":
        return extract_docx(path)
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".pptx":
        return extract_pptx(path)
    if ext == ".json":
        return json.dumps(json.load(open(path)), indent=2)
    if ext == ".eml":
        return extract_eml(path)
    return ""


def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for n in sorted(names):
                    files.append(os.path.join(root, n))
        else:
            files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--max-rows", type=int, default=500)
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    manifest, n = [], 0
    for path in collect(a.inputs):
        ext = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)
        if ext not in SUPPORTED:
            print(f"SKIP  {name}: unsupported type {ext or '(none)'}", file=sys.stderr)
            continue
        n += 1
        sid = f"S{n}"
        try:
            text = extract(path, a.max_rows)
            err = None
        except Exception as e:
            text, err = "", str(e)
        slug = re.sub(r"[^A-Za-z0-9]+", "_", os.path.splitext(name)[0]).strip("_")[:40]
        out = os.path.join(a.outdir, f"{sid}_{slug}.md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"<!-- source {sid}: {name} -->\n{text}\n")
        manifest.append({"id": sid, "file": name, "type": ext.lstrip("."), "path": out,
                         "chars": len(text), "error": err})
        flag = "ERROR " + err if err else ("EMPTY" if not text.strip() else "ok")
        print(f"{sid}  {name:<45} {len(text):>8} chars  {flag}")

    with open(os.path.join(a.outdir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n{n} source(s) written to {a.outdir}/ (manifest.json lists the IDs)")


if __name__ == "__main__":
    main()
