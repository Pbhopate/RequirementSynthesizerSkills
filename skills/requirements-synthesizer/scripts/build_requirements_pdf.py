#!/usr/bin/env python3
"""Render requirements.json (see references/schema.md) as a requirements specification PDF.

Usage: python build_requirements_pdf.py requirements.json -o Requirements_Specification.pdf [--force]

The validator runs first; errors stop the build unless --force is given.
"""
import argparse
import datetime
import json
import os
import re
import sys
from collections import OrderedDict
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_requirements import validate  # noqa: E402

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, NextPageTemplate,  # noqa: E402
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents  # noqa: E402

NAVY = colors.HexColor("#1F3A5F")
GREY = colors.HexColor("#667085")
LIGHT = colors.HexColor("#F2F4F7")
LINE = colors.HexColor("#D0D5DD")
PRIO_COLOR = {"Must": "#B42318", "Should": "#B54708", "Could": "#175CD3", "Won't": "#667085"}
TYPE_LABEL = OrderedDict([
    ("functional", "Functional"), ("non_functional", "Non-functional"),
    ("business_rule", "Business rules"), ("data", "Data"), ("interface", "Interface")])
PREFIX_HINT = {"functional": "FR", "non_functional": "NFR", "business_rule": "BR",
               "data": "DR", "interface": "IR"}

# ---- fonts: DejaVu has the glyphs (arrows, >=, bullets) Helvetica lacks -------------------
FONT, BOLD, ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
_dj = "/usr/share/fonts/truetype/dejavu/"
if os.path.exists(_dj + "DejaVuSans.ttf"):
    pdfmetrics.registerFont(TTFont("DJ", _dj + "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DJ-B", _dj + "DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("DJ-I", _dj + "DejaVuSans-Oblique.ttf"))
    pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-B", italic="DJ-I", boldItalic="DJ-B")
    FONT, BOLD, ITAL = "DJ", "DJ-B", "DJ-I"
_ASCII_FALLBACK = FONT == "Helvetica"


def fmt(text):
    """Escape XML, keep **bold**, turn newlines into <br/>."""
    if text is None:
        return ""
    t = escape(str(text))
    if _ASCII_FALLBACK:
        for a, b in (("→", "->"), ("≥", ">="), ("≤", "<="), ("●", "*"), ("✓", "yes"), ("—", "-")):
            t = t.replace(a, b)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t.replace("\n", "<br/>")


S = {
    "body": ParagraphStyle("body", fontName=FONT, fontSize=9.5, leading=13.5, spaceAfter=6),
    "small": ParagraphStyle("small", fontName=FONT, fontSize=8.5, leading=11.5),
    "cell": ParagraphStyle("cell", fontName=FONT, fontSize=8.5, leading=11.5),
    "cellb": ParagraphStyle("cellb", fontName=BOLD, fontSize=8.5, leading=11.5),
    "head": ParagraphStyle("head", fontName=BOLD, fontSize=8.5, leading=11, textColor=colors.white),
    "H1": ParagraphStyle("H1", fontName=BOLD, fontSize=16, leading=20, textColor=NAVY,
                         spaceBefore=14, spaceAfter=8, keepWithNext=1),
    "H2": ParagraphStyle("H2", fontName=BOLD, fontSize=12, leading=15, textColor=NAVY,
                         spaceBefore=10, spaceAfter=5, keepWithNext=1),
    "note": ParagraphStyle("note", fontName=ITAL, fontSize=8.5, leading=11.5, textColor=GREY, spaceAfter=6,
                       keepWithNext=1),
    "bullet": ParagraphStyle("bullet", fontName=FONT, fontSize=9.5, leading=13.5, leftIndent=12,
                             bulletIndent=2, spaceAfter=2),
    "cover_t": ParagraphStyle("cover_t", fontName=BOLD, fontSize=26, leading=32, textColor=NAVY),
    "cover_s": ParagraphStyle("cover_s", fontName=FONT, fontSize=13, leading=18, textColor=GREY),
    "toc1": ParagraphStyle("toc1", fontName=BOLD, fontSize=10, leading=16, leftIndent=0),
    "toc2": ParagraphStyle("toc2", fontName=FONT, fontSize=9, leading=13, leftIndent=14),
    "center": ParagraphStyle("center", fontName=FONT, fontSize=9, alignment=TA_CENTER),
}


def P(text, style="body"):
    return Paragraph(fmt(text), S[style])


def bullets(items, style="bullet"):
    return [Paragraph(fmt(i), S[style], bulletText="•") for i in items]


def cell_bullets(items):
    return [Paragraph(fmt(i), S["cell"], bulletText="•") for i in items]


def table(rows, widths, header=True, zebra=True, extra=None):
    data = []
    for ri, row in enumerate(rows):
        data.append([c if not isinstance(c, str) else
                     Paragraph(fmt(c), S["head"] if (header and ri == 0) else S["cell"]) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for i in range(1 if header else 0, len(data)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(st + (extra or [])))
    return t


class Doc(BaseDocTemplate):
    def __init__(self, fn, meta):
        super().__init__(fn, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                         topMargin=22 * mm, bottomMargin=20 * mm,
                         title=meta.get("title", "Requirements Specification"),
                         author=meta.get("prepared_by", ""))
        self.meta = meta
        fr = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="cover", frames=[fr], onPage=lambda c, d: None),
                               PageTemplate(id="body", frames=[fr], onPage=self.decorate)])
        self._n = 0

    def decorate(self, canv, doc):
        canv.saveState()
        canv.setFont(FONT, 8)
        canv.setFillColor(GREY)
        canv.drawString(self.leftMargin, A4[1] - 14 * mm, self.meta.get("title", ""))
        canv.drawRightString(A4[0] - self.rightMargin, A4[1] - 14 * mm,
                             f"v{self.meta.get('version', '0.1')} · {self.meta.get('status', 'Draft')}")
        canv.setStrokeColor(LINE)
        canv.line(self.leftMargin, A4[1] - 16 * mm, A4[0] - self.rightMargin, A4[1] - 16 * mm)
        canv.line(self.leftMargin, 15 * mm, A4[0] - self.rightMargin, 15 * mm)
        canv.drawString(self.leftMargin, 10 * mm, self.meta.get("confidentiality", "Confidential"))
        canv.drawRightString(A4[0] - self.rightMargin, 10 * mm, f"Page {doc.page}")
        canv.restoreState()

    def beforeDocument(self):
        # multiBuild runs several passes; keys must be identical each pass or the TOC never settles.
        self._n = 0

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("H1", "H2"):
            self._n += 1
            key = f"h{self._n}"
            lvl = 0 if fl.style.name == "H1" else 1
            text = fl.getPlainText()
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, lvl, 0)
            self.notify("TOCEntry", (lvl, text, self.page, key))


# ---------------------------------------------------------------------------------------
def build(d, out):
    meta = d["meta"]
    stk = {s["id"]: s for s in d.get("stakeholders", [])}
    reqs = d["requirements"]
    W = 170 * mm
    story = []
    sec = [0]

    def H1(title):
        sec[0] += 1
        sub[0] = 0
        story.append(Paragraph(f"{sec[0]}. {escape(title)}", S["H1"]))

    sub = [0]

    def H2(title):
        sub[0] += 1
        story.append(Paragraph(f"{sec[0]}.{sub[0]} {escape(title)}", S["H2"]))

    def stk_label(ids):
        return ", ".join(f"{stk[i]['name']} ({stk[i].get('role', '')})" if i in stk and stk[i].get("role")
                         else stk[i]["name"] if i in stk else i for i in ids) or "—"

    # ---- cover ------------------------------------------------------------------------
    story += [Spacer(1, 55 * mm), Paragraph(escape(meta["title"]), S["cover_t"]), Spacer(1, 6),
              Paragraph(escape(meta.get("subtitle", "Requirements Specification")), S["cover_s"]),
              Spacer(1, 30 * mm)]
    ctrl = [["Document control", ""],
            ["Version", meta.get("version", "0.1")],
            ["Status", meta.get("status", "Draft - pending stakeholder review")],
            ["Date", meta.get("date", datetime.date.today().isoformat())],
            ["Prepared by", meta.get("prepared_by", "—")],
            ["Project / Client", meta.get("project", "—")],
            ["Sources consolidated", str(len(d.get("sources", [])))],
            ["Stakeholders", str(len(d.get("stakeholders", [])))]]
    story.append(table(ctrl, [45 * mm, 125 * mm], zebra=True))
    story += [NextPageTemplate("body"), PageBreak()]

    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    story += [Paragraph("Contents", S["H1"].clone("TocTitle")), toc, PageBreak()]

    # ---- 1 executive summary -----------------------------------------------------------
    H1("Executive Summary")
    if d.get("summary"):
        story.append(P(d["summary"]))
    counts = OrderedDict((t, OrderedDict((p, 0) for p in PRIO_COLOR)) for t in TYPE_LABEL)
    for r in reqs:
        if r["type"] in counts and r["priority"] in counts[r["type"]]:
            counts[r["type"]][r["priority"]] += 1
    rows = [["Requirement type"] + list(PRIO_COLOR) + ["Total"]]
    for t, lab in TYPE_LABEL.items():
        tot = sum(counts[t].values())
        if tot:
            rows.append([lab] + [str(counts[t][p]) for p in PRIO_COLOR] + [str(tot)])
    rows.append(["**Total**"] + [str(sum(counts[t][p] for t in counts)) for p in PRIO_COLOR] + [str(len(reqs))])
    story.append(table(rows, [50 * mm] + [24 * mm] * 4 + [24 * mm]))
    story.append(Spacer(1, 6))
    nc, nq = len(d.get("conflicts", [])), len(d.get("open_questions", []))
    open_c = sum(1 for c in d.get("conflicts", []) if c.get("status", "Open").lower().startswith("open"))
    story.append(P(f"**Decisions needed:** {open_c} of {nc} stakeholder conflict(s) are open and "
                   f"{nq} open question(s) must be answered before this specification can be baselined. "
                   f"See sections on Conflicts and Open Questions."))
    story.append(P("Priorities are labelled **stated** (the stakeholder said it) or **proposed** (assigned "
                   "during consolidation and awaiting confirmation).", "note"))

    # ---- 2 introduction ----------------------------------------------------------------
    H1("Introduction")
    H2("Purpose and background")
    story.append(P(d.get("background", "—")))
    sc = d.get("scope", {})
    H2("Scope")
    story.append(P("**In scope**"))
    story += bullets(sc.get("in_scope", ["—"]))
    story.append(Spacer(1, 4))
    story.append(P("**Out of scope**"))
    story += bullets(sc.get("out_of_scope", ["—"]))
    if d.get("glossary"):
        H2("Glossary")
        story.append(table([["Term", "Definition"]] + [[g["term"], g["definition"]] for g in d["glossary"]],
                           [40 * mm, 130 * mm]))

    # ---- 3 stakeholders ----------------------------------------------------------------
    H1("Stakeholders")
    rows = [["ID", "Name / Role", "Interests and concerns", "Influence"]]
    for s in d.get("stakeholders", []):
        rows.append([s["id"],
                     f"**{s['name']}**\n{s.get('role', '')}" + (f"\n{s['org']}" if s.get("org") else ""),
                     s.get("interests", "—"), s.get("influence", "—")])
    story.append(table(rows, [14 * mm, 48 * mm, 83 * mm, 25 * mm]))
    if d.get("user_roles"):
        H2("User roles")
        story.append(table([["Role", "Description", "Key permissions / needs"]] +
                           [[u["name"], u.get("description", ""), u.get("permissions", "")]
                            for u in d["user_roles"]], [35 * mm, 65 * mm, 70 * mm]))

    # ---- 4 objectives ------------------------------------------------------------------
    if d.get("objectives"):
        H1("Business Objectives and Success Measures")
        story.append(table([["ID", "Objective", "Success measure", "Sponsors"]] +
                           [[o["id"], o["statement"], o.get("metric", "TBD - to be confirmed"),
                             ", ".join(stk[i]["name"] if i in stk else i for i in o.get("stakeholders", []))
                             or "—"] for o in d["objectives"]],
                           [14 * mm, 70 * mm, 55 * mm, 31 * mm]))

    # ---- requirements ------------------------------------------------------------------
    def req_card(r):
        pc = PRIO_COLOR.get(r["priority"], "#667085")
        head = Paragraph(f"<b>{escape(r['id'])}</b> &nbsp;·&nbsp; {fmt(r.get('title', ''))}"
                         f" &nbsp;&nbsp;—&nbsp;&nbsp; <b>{r['priority']}</b> "
                         f"<font size='7'>({r.get('priority_basis', 'proposed')})</font>", S["head"])
        L = lambda x: Paragraph(f"<b>{x}</b>", S["cell"])
        rows = [[head, ""], [L("Requirement"), P(r["statement"], "cell")]]
        if r.get("rationale"):
            rows.append([L("Rationale"), P(r["rationale"], "cell")])
        if r.get("acceptance_criteria"):
            rows.append([L("Acceptance criteria"), cell_bullets(r["acceptance_criteria"])])
        rows.append([L("Raised by"), P(stk_label(r.get("stakeholders", [])), "cell")])
        if r.get("objectives"):
            rows.append([L("Objectives"), P(", ".join(r["objectives"]), "cell")])
        rows.append([L("Sources"), P("; ".join(r.get("sources", [])), "cell")])
        if r.get("origin") == "derived":
            rows.append([L("Origin"), P("Derived during analysis - not stated verbatim by a stakeholder; "
                                        "needs confirmation.", "cell")])
        if r.get("notes"):
            rows.append([L("Notes"), P(r["notes"], "cell")])
        t = Table(rows, colWidths=[34 * mm, 136 * mm])
        t.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)), ("BACKGROUND", (0, 0), (1, 0), colors.HexColor(pc)),
            ("BACKGROUND", (0, 1), (0, -1), LIGHT), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]))
        return t

    def req_section(title, types, group_by_category=True):
        items = [r for r in reqs if r["type"] in types]
        if not items:
            return
        H1(title)
        groups = OrderedDict()
        for r in items:
            groups.setdefault(r.get("category") or TYPE_LABEL[r["type"]], []).append(r)
        for cat, rs in groups.items():
            if group_by_category and (len(groups) > 1 or cat):
                H2(cat)
            for r in rs:
                story.append(KeepTogether([req_card(r), Spacer(1, 7)]))

    req_section("Functional Requirements", {"functional"})
    req_section("Non-Functional Requirements", {"non_functional"})
    req_section("Business Rules, Data and Interface Requirements", {"business_rule", "data", "interface"})

    # ---- assumptions / constraints / dependencies --------------------------------------
    blocks = [("Assumptions", "assumptions"), ("Constraints", "constraints"), ("Dependencies", "dependencies")]
    if any(d.get(k) for _, k in blocks):
        H1("Assumptions, Constraints and Dependencies")
        for title, key in blocks:
            if d.get(key):
                H2(title)
                story.append(table([["ID", "Statement", "Source / owner"]] +
                                   [[x["id"], x["text"], x.get("source", x.get("owner", "—"))] for x in d[key]],
                                   [16 * mm, 120 * mm, 34 * mm]))

    # ---- conflicts ---------------------------------------------------------------------
    H1("Stakeholder Conflicts and Decisions Required")
    if d.get("conflicts"):
        story.append(P("Where stakeholders asked for incompatible things, the positions are recorded as "
                       "stated. Recommendations are proposals for the decision owner, not decisions.", "note"))
        for c in d["conflicts"]:
            rows = [[Paragraph(f"<b>{escape(c['id'])}</b> &nbsp;·&nbsp; {fmt(c['topic'])}"
                               f" &nbsp;&nbsp;—&nbsp;&nbsp; <b>{escape(c.get('status', 'Open'))}</b>", S["head"]), ""]]
            pos = [P(f"**{stk[p['stakeholder']]['name'] if p.get('stakeholder') in stk else p.get('stakeholder')}:** "
                     f"{p['position']}" + (f" ({p['source']})" if p.get("source") else ""), "cell")
                   for p in c.get("positions", [])]
            rows.append([Paragraph("<b>Positions</b>", S["cell"]), pos])
            rows.append([Paragraph("<b>Affects</b>", S["cell"]), P(", ".join(c.get("requirements", [])) or "—", "cell")])
            if c.get("impact"):
                rows.append([Paragraph("<b>Impact</b>", S["cell"]), P(c["impact"], "cell")])
            if c.get("recommendation"):
                rows.append([Paragraph("<b>Proposed resolution</b>", S["cell"]), P(c["recommendation"], "cell")])
            rows.append([Paragraph("<b>Decision owner</b>", S["cell"]), P(c.get("decision_owner", "TBD"), "cell")])
            t = Table(rows, colWidths=[34 * mm, 136 * mm])
            t.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                                   ("BACKGROUND", (0, 1), (0, -1), LIGHT),
                                   ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]))
            story.append(KeepTogether([t, Spacer(1, 7)]))
    else:
        story.append(P("No conflicts between stakeholder positions were identified in the supplied sources."))

    # ---- risks -------------------------------------------------------------------------
    if d.get("risks"):
        H1("Risks")
        story.append(table([["ID", "Risk", "Likelihood", "Impact", "Mitigation"]] +
                           [[r["id"], r["description"], r.get("likelihood", "—"), r.get("impact", "—"),
                             r.get("mitigation", "—")] for r in d["risks"]],
                           [14 * mm, 62 * mm, 21 * mm, 21 * mm, 52 * mm]))

    # ---- open questions ----------------------------------------------------------------
    H1("Open Questions and Gaps")
    if d.get("open_questions"):
        story.append(P("Items the sources did not settle. Each blocks or weakens one or more requirements.", "note"))
        story.append(table([["ID", "Question", "Why it matters", "Owner", "Related"]] +
                           [[q["id"], q["question"], q.get("why_it_matters", "—"), q.get("owner", "TBD"),
                             ", ".join(q.get("related", [])) or "—"] for q in d["open_questions"]],
                           [13 * mm, 62 * mm, 47 * mm, 22 * mm, 26 * mm]))
    else:
        story.append(P("None recorded."))

    # ---- traceability ------------------------------------------------------------------
    H1("Traceability Matrix")
    story.append(P("Each requirement mapped to the stakeholders who raised it, the objectives it serves, "
                   "and where in the sources it came from.", "note"))
    tr = [["Req", "Pri.", "Raised by", "Objectives", "Sources"]]
    for r in reqs:
        tr.append([r["id"], r["priority"], ", ".join(stk[i]["name"] if i in stk else i for i in r.get("stakeholders", [])),
                   ", ".join(r.get("objectives", [])) or "—", "; ".join(r.get("sources", []))])
    story.append(table(tr, [17 * mm, 14 * mm, 52 * mm, 25 * mm, 62 * mm]))

    # ---- appendix ----------------------------------------------------------------------
    H1("Appendix: Source Inventory")
    story.append(table([["ID", "Source", "Type", "Date", "Participants / notes"]] +
                       [[s["id"], s.get("name", "—"), s.get("type", "—"), s.get("date", "—"),
                         s.get("participants", s.get("notes", "—"))] for s in d.get("sources", [])],
                       [12 * mm, 50 * mm, 25 * mm, 18 * mm, 65 * mm]))
    if d.get("next_steps"):
        H1("Recommended Next Steps")
        story += bullets(d["next_steps"])

    Doc(out, meta).multiBuild(story)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("-o", "--out", default="Requirements_Specification.pdf")
    ap.add_argument("--force", action="store_true", help="build even if validation errors exist")
    a = ap.parse_args()
    with open(a.json_file, encoding="utf-8") as f:
        d = json.load(f)
    errors, warnings = validate(d)
    for e in errors:
        print("ERROR  ", e)
    for w in warnings:
        print("WARNING", w)
    if errors and not a.force:
        print("\nFix the errors above (or pass --force). PDF not built.")
        sys.exit(1)
    build(d, a.out)
    print(f"\nWrote {a.out}  ({len(d['requirements'])} requirements, {len(warnings)} warning(s))")


if __name__ == "__main__":
    main()
