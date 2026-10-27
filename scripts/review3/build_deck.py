#!/usr/bin/env python3
"""Build the Review 3 deck from the VIT template (kept: master, layouts, footer, logo) with 19 slides.

Run: realdata/.venv/bin/python scripts/review3/build_deck.py
Output: docs/review-3/Team1_Review3_OCEL.pptx
"""

from __future__ import annotations

import re
import shutil
import struct
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path("/Users/aakaash/Downloads/Review 3- 28-10- 2026.pptx")
FIG = ROOT / "docs" / "review-3" / "figures"
OUT = ROOT / "docs" / "review-3" / "Team1_Review3_OCEL.pptx"
WORK = Path("/private/tmp/claude-501/-Users-aakaash-Downloads-Project-1-Team1-Educational-Capstone-Research/3c16c160-aca5-4af9-a8d5-576345b4cc10/scratchpad/deck_work")

EMU = 914400
def E(inches: float) -> int:
    return int(round(inches * EMU))

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
INK, MUTED, BLUE, ORANGE, AQUA = "1F2328", "5B616B", "2A78D6", "EB6834", "1BAF7A"
CARD, CARD_B, LINE = "F3F6FA", "E6F0FC", "C9D3E0"
TNR = '<a:latin typeface="Times New Roman" panose="02020603050405020304" pitchFamily="18" charset="0"/><a:cs typeface="Times New Roman" panose="02020603050405020304" pitchFamily="18" charset="0"/>'
MONO = '<a:latin typeface="Courier New"/><a:cs typeface="Courier New"/>'


# ---------------------------------------------------------------- text helpers
def run(text, sz=18, b=False, i=False, color=INK, hl=False, font=TNR):
    rpr = f'<a:rPr lang="en-IN" sz="{int(sz * 100)}"{" b=\"1\"" if b else ""}{" i=\"1\"" if i else ""} dirty="0"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>' \
          + ('<a:highlight><a:srgbClr val="FFFF00"/></a:highlight>' if hl else "") + font + '</a:rPr>'
    return f'<a:r>{rpr}<a:t>{escape(text)}</a:t></a:r>'


def para(runs, bullet=False, algn="l", before=6, after=0, line=100, lvl_indent=285750, num=None):
    if isinstance(runs, str):
        runs = [runs]
    if bullet:
        ppr = f'<a:pPr marL="{lvl_indent}" indent="-{lvl_indent}" algn="{algn}"><a:lnSpc><a:spcPct val="{line * 1000}"/></a:lnSpc><a:spcBef><a:spcPts val="{before * 100}"/></a:spcBef><a:spcAft><a:spcPts val="{after * 100}"/></a:spcAft><a:buFont typeface="Arial" panose="020B0604020202020204" pitchFamily="34" charset="0"/><a:buChar char="&#8226;"/></a:pPr>'
    elif num:
        ppr = f'<a:pPr marL="{lvl_indent}" indent="-{lvl_indent}" algn="{algn}"><a:lnSpc><a:spcPct val="{line * 1000}"/></a:lnSpc><a:spcBef><a:spcPts val="{before * 100}"/></a:spcBef><a:spcAft><a:spcPts val="{after * 100}"/></a:spcAft><a:buFont typeface="+mj-lt"/><a:buAutoNum type="arabicPeriod"/></a:pPr>'
    else:
        ppr = f'<a:pPr marL="0" indent="0" algn="{algn}"><a:lnSpc><a:spcPct val="{line * 1000}"/></a:lnSpc><a:spcBef><a:spcPts val="{before * 100}"/></a:spcBef><a:spcAft><a:spcPts val="{after * 100}"/></a:spcAft><a:buNone/></a:pPr>'
    return f'<a:p>{ppr}{"".join(runs)}</a:p>'


class Slide:
    def __init__(self, layout=2):
        self.layout, self.shapes, self.rels, self.notes, self._id = layout, [], [], "", 1
        self.media: list[str] = []

    def nid(self):
        self._id += 1
        return self._id

    def rel(self, kind, target):
        rid = f"rId{len(self.rels) + 2}"           # rId1 is the layout
        self.rels.append((rid, kind, target))
        return rid

    # --- shapes
    def title(self, text, size=30):
        i = self.nid()
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="Title {i}"/><p:cNvSpPr txBox="1"><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{E(0.5)}" y="{E(0.55)}"/><a:ext cx="{E(12.33)}" cy="{E(0.75)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
            f'<p:txBody><a:bodyPr vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" rtlCol="0" anchor="ctr"><a:noAutofit/></a:bodyPr><a:lstStyle/>'
            f'<a:p><a:pPr marL="0"><a:lnSpc><a:spcPct val="100000"/></a:lnSpc></a:pPr><a:r><a:rPr lang="en-IN" sz="{size * 100}" b="1" dirty="0">{TNR}</a:rPr><a:t>{escape(text)}</a:t></a:r></a:p></p:txBody></p:sp>')

    def text(self, x, y, w, h, paras, fill=None, line=None, anchor="t", dashed=False, rounded=False, inset=0.12, name="TextBox"):
        i = self.nid()
        geom = "roundRect" if rounded else "rect"
        av = '<a:avLst><a:gd name="adj" fmla="val 6000"/></a:avLst>' if rounded else '<a:avLst/>'
        f = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>'
        ln = (f'<a:ln w="19050"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill>{"<a:prstDash val=\"dash\"/>" if dashed else ""}</a:ln>') if line else '<a:ln><a:noFill/></a:ln>'
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="{name} {i}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{E(x)}" y="{E(y)}"/><a:ext cx="{E(w)}" cy="{E(h)}"/></a:xfrm><a:prstGeom prst="{geom}">{av}</a:prstGeom>{f}{ln}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="{E(inset)}" tIns="{E(inset * 0.7)}" rIns="{E(inset)}" bIns="{E(inset * 0.7)}" rtlCol="0" anchor="{anchor}"><a:noAutofit/></a:bodyPr><a:lstStyle/>{"".join(paras)}</p:txBody></p:sp>')

    def shape(self, kind, x, y, w, h, fill, line=None, text=None, sz=14, color="FFFFFF", b=True):
        i = self.nid()
        ln = f'<a:ln w="19050"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
        body = para([run(text, sz, b, color=color)], algn="ctr", before=0) if text else '<a:p><a:endParaRPr lang="en-IN"/></a:p>'
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="Shape {i}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{E(x)}" y="{E(y)}"/><a:ext cx="{E(w)}" cy="{E(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{kind}"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>{ln}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="45720" tIns="45720" rIns="45720" bIns="45720" rtlCol="0" anchor="ctr"><a:noAutofit/></a:bodyPr><a:lstStyle/>{body}</p:txBody></p:sp>')

    def picture(self, path: Path, x, y, w=None, h=None, alt=""):
        pw, ph = png_size(path)
        if w and not h:
            h = w * ph / pw
        elif h and not w:
            w = h * pw / ph
        elif w and h:                                   # fit inside the box, centred
            s = min(w / pw, h / ph)
            x, y, w, h = x + (w - pw * s) / 2, y + (h - ph * s) / 2, pw * s, ph * s
        rid = self.rel("http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", f"../media/{path.name}")
        self.media.append(path.name)
        i = self.nid()
        self.shapes.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{i}" name="Picture {i}" descr="{escape(alt, {chr(34): "&quot;"})}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="{E(x)}" y="{E(y)}"/><a:ext cx="{E(w)}" cy="{E(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')

    def table(self, x, y, widths, rows, header_fill=BLUE, sz=13, row_h=0.5, header_h=0.45, zebra=True, bold_first_col=False):
        i = self.nid()
        grid = "".join(f'<a:gridCol w="{E(w)}"/>' for w in widths)
        def cell(content, head=False, fill=None, bold=False):
            runs = content if isinstance(content, list) else [run(content, sz, b=head or bold, color="FFFFFF" if head else INK)]
            fl = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>'
            border = "".join(f'<a:{s} w="9525"><a:solidFill><a:srgbClr val="{LINE}"/></a:solidFill></a:{s}>' for s in ("lnL", "lnR", "lnT", "lnB"))
            return (f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>{para(runs, before=0)}</a:txBody>'
                    f'<a:tcPr marL="{E(0.08)}" marR="{E(0.08)}" marT="{E(0.05)}" marB="{E(0.05)}" anchor="ctr">{border}{fl}</a:tcPr></a:tc>')
        trs = [f'<a:tr h="{E(header_h)}">' + "".join(cell(c, head=True, fill=header_fill) for c in rows[0]) + '</a:tr>']
        for n, r in enumerate(rows[1:]):
            fill = "EEF3FA" if (zebra and n % 2 == 0) else "FFFFFF"
            trs.append(f'<a:tr h="{E(row_h)}">' + "".join(cell(c, fill=fill, bold=bold_first_col and k == 0) for k, c in enumerate(r)) + '</a:tr>')
        total_h = header_h + row_h * (len(rows) - 1)
        self.shapes.append(
            f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{i}" name="Table {i}"/><p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
            f'<p:xfrm><a:off x="{E(x)}" y="{E(y)}"/><a:ext cx="{E(sum(widths))}" cy="{E(total_h)}"/></p:xfrm>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl><a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>{grid}</a:tblGrid>{"".join(trs)}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')

    def xml(self, number):
        footer = (
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self.nid()}" name="Date Placeholder"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="dt" sz="half" idx="10"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:fld id="{{61736562-4E3F-4038-A291-A7AE35CC3E6A}}" type="datetime1"><a:rPr lang="en-IN" smtClean="0"/><a:t>28/10/26</a:t></a:fld><a:endParaRPr lang="en-IN"/></a:p></p:txBody></p:sp>'
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self.nid()}" name="Footer Placeholder"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="ftr" sz="quarter" idx="11"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-IN"/><a:t>SCOPE</a:t></a:r></a:p></p:txBody></p:sp>'
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self.nid()}" name="Slide Number Placeholder"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldNum" sz="quarter" idx="12"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:fld id="{{65201FD4-9D8D-4491-815B-63C7BF4F0034}}" type="slidenum"><a:rPr lang="en-IN" smtClean="0"/><a:t>{number}</a:t></a:fld><a:endParaRPr lang="en-IN"/></a:p></p:txBody></p:sp>')
        return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sld {NS}><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                f'<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{"".join(self.shapes)}{footer}</p:spTree></p:cSld>'
                f'<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')


def png_size(path: Path):
    with path.open("rb") as h:
        h.read(16)
        return struct.unpack(">II", h.read(8))


# ---------------------------------------------------------------- content
def bullets(items, sz=18, before=8):
    out = []
    for it in items:
        out.append(para(it if isinstance(it, list) else [run(it, sz)], bullet=True, before=before))
    return out


def card_title(text, color=BLUE, sz=16):
    return para([run(text, sz, b=True, color=color)], before=0, after=4)


def stat(slide, x, y, w, value, label, color=BLUE):
    slide.text(x, y, w, 1.25, [para([run(value, 40, b=True, color=color)], algn="l", before=0), para([run(label, 14, color=MUTED)], before=0)], fill=CARD, rounded=True, anchor="ctr", inset=0.18, name="Stat")


def build_slides():
    S = []

    # 1 ---- title (patched from the template slide)
    S.append(None)

    # 2 ---- approval mail
    s = Slide(); s.title("Approval Mail From Guide")
    s.text(0.5, 1.55, 7.2, 4.9, [para([run("PLACEHOLDER", 28, b=True, hl=True)], algn="ctr", before=0), para([run("insert the guide's approval mail screenshot here", 20, hl=True)], algn="ctr", before=10),
           para([run("(taken after the guide approves the points on the right)", 14, color=MUTED, i=True)], algn="ctr", before=14)], fill="FFFFFF", line=MUTED, dashed=True, anchor="ctr", name="Screenshot placeholder")
    s.text(8.0, 1.55, 4.83, 4.9, [card_title("The mail should confirm"),
           *bullets(["Meeting with guide: frequent", "PowerPoint presentation", "Project demonstration", "Final project report", [run("Project outcome: ", 16), run("Ongoing", 16, b=True), run(" (manuscript in preparation)", 16)],
                     [run("Turnitin plagiarism: ", 16), run("[fill in] %", 16, hl=True)], [run("Turnitin AI score: ", 16), run("[fill in]", 16, hl=True), run(" (limit 25%)", 16)],
                     [run("Project ID: ", 16), run("[fill in]", 16, hl=True)]], sz=16, before=7)], fill=CARD, rounded=True, name="Checklist")
    s.notes = ("Quick honesty first. This slide is meant to show our guide's approval mail, and we do not have that screenshot in the file yet, so it is marked as a placeholder, in yellow, on purpose. "
               "We would rather show an empty box than a made-up one. The right side lists the six things the mail has to confirm, including the Turnitin numbers, which we will fill in from the real report. "
               "One thing we can already say truthfully: the project outcome is ongoing. Our journal manuscript is still being written.")
    S.append(s)

    # 3 ---- aim
    s = Slide(); s.title("Aim")
    s.text(0.5, 1.55, 7.3, 5.0, bullets([
        "Model the capstone review lifecycle (project, team, student, guide, report version, score) as an OCEL 2.0 object-centric event log.",
        "Measure, on real public logs, what a flat single-case view hides or distorts, and what a flat export must carry to stay trustworthy.",
        "Do it with reproducible, independently checked code, because production portal logs are not available to us."], sz=20, before=14), name="Aim text")
    s.text(8.2, 1.55, 4.63, 5.0, [para([run("The question we asked", 16, b=True, color=BLUE)], before=0, after=10),
           para([run("When a workflow with many entities is flattened to one case notion, what do we actually lose?", 26, i=True)], before=0)], fill=CARD_B, rounded=True, anchor="ctr", inset=0.3, name="Question")
    s.notes = ("Have you ever flattened a messy spreadsheet into one clean column and then wondered what just disappeared? That is our aim in one line. "
               "A capstone event is never about one thing. A single submission touches the project, the team, three students, the guide, a report version and, later, a score. "
               "Process mining normally forces one case identifier per event. So we asked: what is lost when we do that? We could not test it on the portal itself, because we do not have its logs. "
               "So the aim became two things: model the capstone lifecycle properly, and measure the loss on real public data, with code that anyone can re-run.")
    S.append(s)

    # 4 ---- abstract
    s = Slide(); s.title("Abstract")
    s.text(0.5, 1.55, 8.0, 5.2, [
        para([run("Process mining normally assigns each event to one case. A capstone event, however, concerns a project, a team, a guide, a report version and a score at once. Flattening it to a single case notion can duplicate events, drop others, or hide how cases share people and resources.", 17)], before=0, after=8),
        para([run("Production portal logs were unavailable, so we built a reproducible OCEL 2.0 pipeline and measured flattening on seven real public logs: code review, education, legislation, e-mail, blockchain and gameplay.", 17)], before=0, after=8),
        para([run("Duplication from flattening turned out to be small except in fan-out logs. The larger effect is narrowing: one case notion shows only a slice of the process. Every number is re-computed by open code and checked by independent implementations.", 17)], before=0)], name="Abstract text")
    stat(s, 8.9, 1.55, 3.93, "7", "real public logs, none synthetic")
    stat(s, 8.9, 3.05, 3.93, "38", "case notions compared against the object-centric reference", ORANGE)
    stat(s, 8.9, 4.55, 3.93, "0", "results from simulated or injected data", AQUA)
    s.notes = ("Here is the whole project in one breath. Process mining likes one case per event. Real workflows do not work like that. "
               "We built a pipeline around OCEL 2.0, which lets one event point at many objects, and we pointed it at seven real public logs: Gerrit code review, the Open University student data, Angular commits, the German Bundestag, Enron e-mails, Ethereum, and Age of Empires. "
               "Our honest finding is a little less dramatic than we expected. Flattening rarely duplicates events, except in fan-out logs. The bigger effect is narrowing, you only see a slice. "
               "And one more thing worth saying out loud: none of these numbers come from synthetic data.")
    S.append(s)

    # 5-6 ---- literature review
    head = ["Paper", "Objective", "Methodology", "Pros / Cons", "Findings"]
    w = [2.15, 2.5, 2.6, 2.6, 2.48]
    s = Slide(); s.title("Literature Review (1/2)")
    s.table(0.5, 1.5, w, [head,
        ["van der Aalst (2019) [1]", "Name the problems of one-case-per-event logs", "Conceptual analysis with worked examples", "Pro: defines convergence, divergence. Con: no measurement on real logs", "Flattening copies events across cases or mis-orders them"],
        ["Berti et al. (2024) [2]", "A standard exchange format for object-centric data", "OCEL 2.0 specification: JSON, XML, SQLite, qualifiers, o2o links", "Pro: expressive, tool support. Con: extraction needs domain decisions", "One event can relate to many typed objects"],
        ["Waibel et al. (2022) [5]", "Causal structure from relational data", "Causal event graph, one food-company case study", "Pro: avoids false edges. Con: single case study", "1:N and N:M links give spurious directly-follows relations"],
        ["Adams, Park, van der Aalst (2023) [3]", "Keep object-centric graph structure for ML tasks", "Compare graph encodings with flattened features on predictive tasks", "Pro: shows value of structure. Con: prediction focus, not analysis outputs", "Structure-preserving encodings are favoured over flattening"]],
        sz=13, row_h=1.22, header_h=0.45)
    s.notes = ("Four papers here, and I will go quickly. First, van der Aalst named the problem: flatten, and events get copied or mis-ordered. Second, the OCEL 2.0 specification is the format we build on. "
               "Third, Waibel and colleagues showed that one-to-many links create fake edges, but on one company's data. And fourth, Adams and colleagues showed that keeping the object graph helps machine learning. "
               "Notice the pattern in the Cons column. Lots of theory, a few case studies, very little measurement across real logs. That is the hole we walk into on the next slide.")
    S.append(s)
    s = Slide(); s.title("Literature Review (2/2)")
    s.table(0.5, 1.5, w, [head,
        ["Kabierski et al. (2026) [6]", "Classify quality issues in object-centric data", "Classification checked on real logs and practitioner interviews", "Pro: practitioner-validated. Con: classifies issues, gives no distortion rates", "Object-centric data has its own quality problems, e.g. wrong object relations"],
        ["Miri et al. (2026) [7]", "Object-centric educational process mining", "Moodle to OCEL conversion (PM4Moodle), real course case study", "Pro: first educational use. Con: one LMS course, not a transactional lifecycle", "Group and resource links are invisible in student-centric logs"],
        ["Premchaiswadi, Porouhan (2015) [11]", "Mine an online peer-review process", "Event log from review handling, discovery and conformance", "Pro: review workflow on real data. Con: single case notion", "Bottlenecks and rule violations found in reviewer handling"],
        ["Hassani et al. (2018) [10]", "Manage more than 250 computing final-year projects", "Case study of supervision, panels, rubrics", "Pro: real capstone practice. Con: no event data", "Capstones need coordinated supervision, submission and assessment"]],
        sz=13, row_h=1.22, header_h=0.45)
    s.notes = ("Second half. Kabierski and colleagues list what goes wrong in object-centric data, which is useful, but they classify problems, they do not count them. "
               "Miri and colleagues did object-centric mining in education, on Moodle, and that is the closest neighbour to us. So we are clear we are not the first to use OCEL in education. "
               "Premchaiswadi looked at an online peer-review system, and Hassani described how a department really runs more than two hundred and fifty capstones. "
               "Put together: capstone practice is well described, object-centric mining exists, but nobody has tied them to measured evidence on real logs.")
    S.append(s)

    # 7 ---- research gap
    s = Slide(); s.title("Research Gap")
    rows = [("1", "Flattening problems are named, but not measured", "Convergence and divergence appear as toy or single-case examples. We found no study that reports how often or how badly they occur across several real logs. Most object-centric evidence uses simulated logs.", BLUE),
            ("2", "Education and capstone work stays on LMS data", "Object-centric educational mining uses Moodle activity. A transactional review lifecycle (submit, review, reject, resubmit, score) has no public object-centric dataset.", ORANGE),
            ("3", "Capstone portal logs cannot be had", "Searches of Zenodo, 4TU and the web found no public capstone or thesis-management event log, so the capstone claim cannot be tested directly.", AQUA)]
    for k, (n, h, t, c) in enumerate(rows):
        y = 1.5 + k * 1.45
        s.shape("ellipse", 0.5, y + 0.1, 0.75, 0.75, c, text=n, sz=24)
        s.text(1.5, y, 11.3, 1.3, [para([run(h, 19, b=True)], before=0, after=3), para([run(t, 15, color=MUTED)], before=0)], fill=CARD, rounded=True, anchor="ctr", inset=0.2, name="Gap")
    s.text(0.5, 5.95, 12.33, 0.7, [para([run("Our angle: ", 17, b=True, color=BLUE), run("measure on real review-like and multi-entity logs, give the capstone an OCEL 2.0 model, and state the limits plainly.", 17)], before=0)], anchor="ctr", name="Angle")
    s.notes = ("So where is the gap? Number one: everyone agrees flattening is a problem, but we could not find a study that counts it across several real logs. Most of the evidence is simulated or one company's case. "
               "Number two: in education, object-centric work is about Moodle clicks. A capstone is different, it is a chain of submit, review, reject, resubmit, score. "
               "And number three, the awkward one: nobody publishes capstone portal logs. We searched. So we cannot prove anything about the portal itself. "
               "What we can do is measure the effect on real logs that look like it, and be upfront about that limit.")
    S.append(s)

    # 8 ---- objectives
    s = Slide(); s.title("Objectives")
    s.text(0.5, 1.5, 7.4, 5.3, [para([run(t, 20)], num=True, before=16, lvl_indent=420000) for t in [
        "Model the capstone lifecycle as OCEL 2.0 from the documented portal behaviour.",
        "Build a reproducible pipeline: download, verify, convert, load, analyse.",
        "Measure flattening distortion on seven real logs without hand-picked rules.",
        "Compare standard outputs (rankings, directly-follows, variants, entity counts) between flat and object-centric views.",
        "Verify every result with independent checks and release the code."]], name="Objectives")
    s.text(8.2, 1.5, 4.63, 0.4, [para([run("Identified", 17, b=True, color=BLUE)], before=0)], name="Identified")
    s.text(8.2, 1.95, 4.63, 0.62, [para([run("Sustainable Development Goals", 13, color=MUTED)], before=0)], name="SDG label")
    s.shape("rect", 8.2, 2.25, 0.62, 0.62, "C5192D", text="4", sz=22)
    s.text(8.9, 2.25, 3.93, 0.62, [para([run("Quality Education", 15, b=True)], before=0)], anchor="ctr", inset=0.04, name="SDG4")
    s.shape("rect", 8.2, 3.0, 0.62, 0.62, "F36E24", text="9", sz=22)
    s.text(8.9, 3.0, 3.93, 0.62, [para([run("Industry, Innovation and Infrastructure", 15, b=True)], before=0)], anchor="ctr", inset=0.04, name="SDG9")
    s.text(8.2, 3.85, 4.63, 1.35, [para([run("Technology Readiness Level", 13, color=MUTED)], before=0), para([run("TRL 4: validated in the lab", 17, b=True)], before=2),
           para([run("Pipeline reproduces on 7 public logs; portal integration is TRL 2-3", 13, color=MUTED)], before=2)], fill=CARD, rounded=True, name="TRL")
    s.text(8.2, 5.3, 4.63, 1.45, [para([run("Outcome", 13, color=MUTED)], before=0), para([run("Journal paper (Scopus): manuscript in preparation, not yet submitted", 16, b=True)], before=2),
           para([run("Open, re-runnable code in the project repository", 13, color=MUTED)], before=2)], fill=CARD, rounded=True, name="Outcome")
    s.notes = ("Five objectives, in the order we did them. One, model the capstone lifecycle. Two, build a pipeline you can re-run. Three, measure the distortion without us picking the rules, because rules we pick can flatter our own idea. "
               "Four, compare what an analyst would actually look at, rankings, edge counts, variants. Five, check everything twice. "
               "On the right: the goals this touches are Quality Education and Industry, Innovation and Infrastructure. We rate the technology at level four, validated in the lab, and we say level two to three for plugging it into the real portal. "
               "The outcome we are aiming at is a journal paper. It is in preparation. It is not submitted, and we are not going to pretend otherwise.")
    S.append(s)

    # 9 ---- framework (capstone OCEL model)
    s = Slide(); s.title("Framework: OCEL 2.0 Model of the Capstone Lifecycle")
    s.picture(FIG / "fig_capstone_schema.png", 0.5, 1.5, w=8.1, alt="Object types and relations of the capstone lifecycle")
    s.text(8.85, 1.5, 3.98, 4.95, [card_title("Documented in the portal docs"), *bullets([
        "8 object types: student, team, project, guide, report, report version, review stage, score",
        "8 audited actions become event types",
        "Qualifiers name each role (member-of, guides, has-score)",
        "Scores are write-once; each rejection uses one of 3 attempts"], sz=15, before=7),
        para([run("Design only: ", 14, b=True, color=ORANGE), run("no portal data exists in this study", 14, color=MUTED)], before=12)], fill=CARD, rounded=True, name="Facts")
    s.notes = ("This is the model we designed from the portal's documentation, and I want to be careful with the wording: it is a design, not a result. "
               "A project is executed by a team of students and guided by a faculty member. A report has versions, a version can get a score, and the score is write-once. "
               "Every audited action in the portal, create, compile, submit, verify, accept, reject, becomes an event that can point at several of these objects at once. "
               "That is exactly the shape a single case id cannot hold, and it is why we chose OCEL 2.0.")
    S.append(s)

    # 10 ---- architecture
    s = Slide(); s.title("Architecture / Block Diagram")
    s.picture(FIG / "fig_architecture.png", 1.9, 1.35, h=5.4, alt="Pipeline from public sources to analysis engines and validation")
    s.notes = ("Read this left to right. Seven public logs come in. The first box downloads each file, checks the size and MD5 against the Zenodo record, writes down a SHA-256, and can resume if the network drops, which it did on us once. "
               "Then we extract safely, convert Gerrit and Open University data into OCEL, and load everything into the same tables. "
               "The orange boxes are the analysis: distortion metrics, the consequence analysis, and a small rule-based engine we keep as an appendix. "
               "The green box is the one we care about most: validation, three different ways of checking our own code. The dashed box on top is the future: an adapter from the portal's audit log, once we are allowed to see one.")
    S.append(s)

    # 11 ---- functional requirements
    s = Slide(); s.title("Functional Requirements")
    left = ["Download datasets from a manifest; check size and MD5 (Zenodo) and record SHA-256", "Extract archives without trusting member paths", "Convert Gerrit (CROP) and OULAD into OCEL 2.0 SQLite", "Load OCEL from SQLite, JSON, XML and parquet bundles, with hashed identifiers"]
    right = ["Compute flattening distortion for every object type", "Compare flat and object-centric outputs: rankings, edges, variants, entities", "Validate with independent implementations", "Export CSV, JSON and Markdown tables; re-run end to end with one command"]
    for col, (items, x0) in enumerate(((left, 0.5), (right, 6.75))):
        for k, t in enumerate(items):
            y = 1.55 + k * 1.1
            s.shape("ellipse", x0, y + 0.16, 0.62, 0.62, BLUE, text=f"{col * 4 + k + 1}", sz=18)
            s.text(x0 + 0.75, y, 5.3, 0.94, [para([run(t, 16)], before=0)], anchor="ctr", inset=0.05, name="FR")
    s.text(0.5, 6.05, 12.33, 0.75, [para([run("Non-functional: ", 15, b=True, color=BLUE), run("results are byte-for-byte reproducible; personal identifiers are hashed; runs on an 8.6 GB laptop; only openly licensed (CC BY 4.0) data.", 15)], before=0)], fill=CARD, rounded=True, anchor="ctr", name="NFR")
    s.notes = ("Eight things the system has to do, and four rules it has to obey. The functional ones follow the pipeline: download and verify, extract safely, convert, load, measure, compare, validate, export. "
               "The rules at the bottom matter just as much. Same input must give the same bytes out, which we tested. Names and e-mail addresses are hashed, especially in the Enron data. "
               "It has to run on a normal laptop, ours has about eight and a half gigabytes of memory, which is why Ethereum is analysed as a window. And only openly licensed data goes in.")
    S.append(s)

    # 12 ---- modules
    s = Slide(); s.title("Modules")
    s.table(0.5, 1.5, [0.7, 3.2, 4.3, 4.13], [["#", "Module", "Files", "What it does"],
        ["M1", "Acquire and verify", "fetch_sources.py, extract_archives.py", "Resumable download, size + MD5 check (Zenodo), SHA-256 record, safe extraction"],
        ["M2", "Convert and load", "convert_crop.py, convert_oulad.py, ocel_io.py", "Gerrit and OULAD to OCEL; load OCEL 2.x; hash identifiers"],
        ["M3", "Distortion metrics", "distortion.py", "Deficiency, convergence, divergence, coupling per object type"],
        ["M4", "Consequence analysis", "consequence.py", "Flat vs object-centric rankings, edges, variants, entities"],
        ["M5", "Predicate engine (appendix)", "cooc.py, registry.py, run_cooc.py", "11 natural rules on CROP and OULAD"],
        ["M6", "Validation", "sql_crosscheck.py, check_consequence.py", "Independent SQL and brute-force re-implementations"],
        ["M7", "Summaries", "summarize_distortion.py, summarize_log_level.py, summarize_consequence.py", "Tables for the report and the paper"]],
        sz=13, row_h=0.62, header_h=0.45)
    s.notes = ("Seven modules, one per box in the architecture. M1 gets the data safely. M2 turns it into OCEL. M3 and M4 are the heart of the project: M3 asks how much a flat view distorts, and M4 asks what an analyst would actually see differently. "
               "M5 is the rule engine from our earlier idea. We kept it in the appendix because with real data only, eleven rules on two logs is simply too few to conclude anything. "
               "M6 is the checker that keeps us honest. And M7 produces the tables you see in the results.")
    S.append(s)

    # 13 ---- live demo
    s = Slide(); s.title("Live Demonstration")
    code = [("1", "python3 -I src/fetch_sources.py", "all 8 sources already present"),
            ("2", ".venv/bin/python -I src/check_consequence.py", "self-check against a plain-Python version"),
            ("3", ".venv/bin/python -I src/distortion.py enron", "flat[...] table for Enron (about 10 s)"),
            ("4", ".venv/bin/python -I src/consequence.py enron", "rankings, edges, variants (about 4 s)"),
            ("5", "open results/consequence_by_log.md", "the cross-log summary table")]
    s.text(0.5, 1.5, 7.9, 5.1, [para([run("cd realdata", 17, color="9AD0FF", font=MONO)], before=0, after=6)] + [
        para([run(f"{n}  ", 17, color="FFB86B", b=True, font=MONO), run(c, 17, color="F5F5F5", font=MONO)], before=14) for n, c, _ in code], fill="1F2328", rounded=True, anchor="ctr", inset=0.25, name="Terminal")
    s.text(8.65, 1.5, 4.18, 5.1, [card_title("What the panel will see"), *bullets([t for _, _, t in code], sz=15, before=11),
           para([run("Full run: make study (5 min 21 s on our laptop)", 13, color=MUTED, i=True)], before=14)], fill=CARD, rounded=True, name="Explain")
    s.notes = ("This is the part where, if the laptop is kind to us, we run it live. Five commands, about a minute in total. First, the download manifest, which should say all eight sources are already present, so nothing is downloaded again. "
               "Second, the self-check, our own code against a slow, plain Python version of itself, it should say passed. Third and fourth, we run the distortion and consequence analysis on the Enron e-mails, because that log has a real many-to-many structure and a nice, visible result. "
               "Last, we open the summary table. If anything misbehaves, we have the saved outputs for every step, so the story does not depend on the Wi-Fi.")
    S.append(s)

    # 14 ---- results 1
    s = Slide(); s.title("Experiments and Results: Distortion")
    s.picture(FIG / "fig_regimes.png", 0.4, 1.45, w=7.9, alt="Event duplication versus events dropped for seven real logs")
    s.text(8.5, 1.5, 4.33, 4.6, [card_title("Three kinds of log"), *bullets([
        [run("Star ", 15, b=True, color=BLUE), run("(CROP, OULAD): one object per type per event, no duplication", 15)],
        [run("Partitioned ", 15, b=True, color=ORANGE), run("(Bundestag, Age of Empires, Ethereum): one case notion drops 69-91% of events", 15)],
        [run("Fan-out ", 15, b=True, color=AQUA), run("(Angular, Enron): real duplication, up to 81.7 copies of an event", 15)]], sz=15, before=8),
        para([run("Across all logs, most object types share more than half their objects between cases.", 14, color=MUTED)], before=12)], fill=CARD, rounded=True, name="Takeaways")
    s.notes = ("Each dot is one real log. Left to right is how much flattening copies events, and up is how much of the process one case notion throws away. "
               "Look at the bottom left: CROP and OULAD sit at one-times, zero percent. Every event touches exactly one object of each type, so flattening is harmless there, at least for copying. "
               "Top left: the Bundestag, Age of Empires and Ethereum. Nothing is copied, but a single case notion drops seventy to ninety percent of the events. You see a slice, not the process. "
               "And bottom right: Angular, where one commit touches dozens of files, so an event gets copied eighty times. Three logs types, three different problems.")
    S.append(s)

    # 15 ---- results 2
    s = Slide(); s.title("Experiments and Results: Consequences")
    s.picture(FIG / "fig_rank_activity.png", 0.4, 1.35, w=6.2, alt="Activity ranking agreement per log")
    s.picture(FIG / "fig_rank_entity.png", 6.75, 1.35, w=6.2, alt="Entity ranking agreement per log")
    s.text(0.5, 5.3, 12.33, 1.55, bullets([
        [run("Duplication alone barely reorders activity rankings: ", 14, b=True), run("only 2 of 38 case notions fall below rank correlation 0.95.", 14)],
        [run("Narrowing is the real effect: ", 14, b=True), run("in 20 of 38 case notions the flat log shows fewer than half of the process's activities.", 14)],
        [run("Careless counting is risky: ", 14, b=True), run("entity rankings from a denormalised export reach correlation 0.16 (Enron), -0.01 (Ethereum) and -0.41 (Age of Empires) in the worst case.", 14)]], sz=14, before=4), name="Findings")
    s.notes = ("Same seven logs, but now we asked what an analyst would actually read off a chart. On the left: if we only count duplication, activity rankings barely move, the blue dots sit near one. "
               "But compare them with the whole process, the orange dots, and in the Bundestag the correlation falls to about 0.17. That gap is narrowing, not duplication. "
               "On the right, the scary one. If you rank entities from a flat export and just count rows, the worst case in Enron is 0.16 and in Age of Empires it is actually negative. "
               "An analyst who de-duplicates by event id would avoid it, so this is about careless counting, not an unavoidable loss. We are saying that plainly.")
    S.append(s)

    # 16 ---- testing and validation
    s = Slide(); s.title("Testing and Validation")
    s.table(0.5, 1.5, [3.4, 5.6, 3.33], [["Check", "What it proves", "Result"],
        ["Download integrity", "Zenodo files match the published size and MD5", "Zenodo: size + MD5 checked; every file: SHA-256 recorded"],
        ["Reproducibility", "Re-running gives the same outputs", "All tracked results byte-identical"],
        ["SQL cross-check", "Predicate code matches independent SQL", "4 of 4 CROP rules exact"],
        ["Brute-force self-check", "Fast code equals plain Python", "Event pairs identical on 4 case notions"],
        ["Distortion self-check", "Pandas metrics equal a plain-Python version", "60 case notions identical on 3 real slices"],
        ["Independent recomputation", "OULAD counts match raw CSVs", "15,348 / 415 / 29 exact"],
        ["Bugs our own checks found", "Verification is not a formality", "3 fixed: duplicate events, missed abandon form, tie-breaking"]],
        sz=13, row_h=0.57, header_h=0.45)
    s.text(0.5, 6.0, 12.33, 0.75, [para([run("What we did not do: ", 15, b=True, color=ORANGE), run("independent human labelling; the distortion check covers slices, not full logs; the activity rankings have no second implementation; the converters are checked by us only.", 15)], before=0)], fill=CARD, rounded=True, anchor="ctr", name="Limits")
    s.notes = ("We tested the project the way we would test someone else's. Downloads are checked against the published size and MD5 where the publisher gives one, and every file gets a SHA-256 on record. Re-running reproduces every result file byte for byte. "
               "Our fast code is compared with a slow, plain Python version, and our rule code with independent SQL, and the OULAD counts with a separate read of the raw files. "
               "And here is the part we are actually proud of: those checks found three real bugs of our own. Duplicate Gerrit comments, an abandon message we missed, and a tie-breaking problem in event order. We fixed all three and re-ran everything. "
               "What we have not done is get a second person to label the findings independently. That is on the limits list.")
    S.append(s)

    # 17 ---- conclusion
    s = Slide(); s.title("Conclusion and Future Work")
    s.text(0.5, 1.5, 6.05, 4.6, [card_title("Conclusion", sz=20), *bullets([
        "We built a reproducible, checked OCEL 2.0 pipeline on 7 real public logs.",
        "Flattening duplicates events only in fan-out logs; the common effect is narrowing.",
        "Naive entity counts from flat exports can mislead badly.",
        "The capstone model is a design; no portal data was available to test it."], sz=19, before=14)], fill=CARD, rounded=True, name="Conclusion")
    s.text(6.78, 1.5, 6.05, 4.6, [card_title("Future work", ORANGE, sz=20), *bullets([
        "Independent two-rater labelling of the real-data findings.",
        "Process-discovery quality and predictive-monitoring comparisons.",
        "Two or three more real logs (for example BPI 2019).",
        "A portal adapter once de-identified audit logs are approved.",
        "Journal manuscript, venue still to be chosen."], sz=19, before=14)], fill=CARD, rounded=True, name="Future")
    s.notes = ("So, what do we conclude? That the pipeline works, that it is checked, and that on real data the story is narrowing more than duplication. "
               "And one limit we repeat on purpose: the capstone model is a design. We could not test it on portal data. "
               "Next steps, in order of importance: get someone independent to label our findings, add the harder comparisons like discovery quality and prediction, add a few more real logs, "
               "and, if the university allows it, plug in the real audit log. Thank you. We are happy to take questions.")
    S.append(s)

    # 18 ---- outcome
    s = Slide(); s.title("Outcome Achieved")
    s.table(0.5, 1.5, [4.2, 8.13], [["Outcome type", "Status today"],
        ["Patent", "None filed"],
        ["International conference proceedings", "None submitted"],
        ["Journal publication (Scopus-indexed)", "Manuscript in preparation (draft v0.3); not submitted; venue not yet chosen"],
        ["Start-up", "None"],
        ["Others", "Open, re-runnable code and result tables in the project repository"]], sz=15, row_h=0.65, header_h=0.5)
    s.text(0.5, 5.4, 12.33, 1.3, [para([run("Proof to upload: ", 15, b=True, color=BLUE), run("none yet, because nothing has been accepted or published. We will upload proof as soon as a submission receipt or acceptance exists.", 15)], before=0),
           para([run("Outcome form (Google form, due 27 Oct 2026): ", 14, b=True, color=MUTED), run("[confirm submitted]", 14, hl=True)], before=8)], fill=CARD, rounded=True, anchor="ctr", name="Proof")
    s.notes = ("This slide is short because the honest answer is short. No patent, no conference paper, no journal acceptance. What we do have is a manuscript draft, version zero point two, and a working, checked code base. "
               "We would rather tell you that now than have you find it in Q and A. Once there is a real submission receipt, that is the proof we will upload.")
    S.append(s)

    # 19 ---- references
    s = Slide(); s.title("References")
    refs_l = ['[1] W. M. P. van der Aalst, "Object-centric process mining: Dealing with divergence and convergence in event data," in SEFM, LNCS, Springer, 2019, pp. 3-25.',
              '[2] A. Berti et al., "OCEL (Object-Centric Event Log) 2.0 specification," arXiv:2403.01975, 2024.',
              '[3] J. N. Adams, G. Park, and W. M. P. van der Aalst, "Preserving complex object-centric graph structures to improve machine learning tasks in process mining," Eng. Appl. Artif. Intell., vol. 125, p. 106764, 2023.',
              '[4] J. N. Adams and W. M. P. van der Aalst, "Addressing convergence, divergence, and deficiency issues," LNBIP, Springer, 2024.',
              '[5] P. Waibel, L. Pfahlsberger, K. Revoredo, and J. Mendling, "Causal process mining from relational databases with domain knowledge," arXiv:2202.08314, 2022.',
              '[6] M. Kabierski et al., "Data quality in object-centric event data: Issues classification and evaluation," Process Science, vol. 3, 2026.']
    refs_r = ['[7] N. Miri, S. Khayatbashi, J. Zdravkovic, and A. Jalali, "An object-centric approach to multi-entity educational process mining," Decis. Anal. J., vol. 19, p. 100724, 2026.',
              '[8] J. Kuzilek, M. Hlosta, and Z. Zdrahal, "Open University Learning Analytics dataset," Sci. Data, vol. 4, p. 170171, 2017.',
              '[9] M. Paixao, J. Krinke, D. Han, and M. Harman, "CROP: Linking code reviews to source code changes," in Proc. MSR, 2018.',
              '[10] H. Hassani et al., "Supervision of undergraduate final year projects in computing: A case study," Educ. Sci., vol. 8, no. 4, p. 210, 2018.',
              '[11] W. Premchaiswadi and P. Porouhan, "Process modeling and bottleneck mining in online peer-review systems," SpringerPlus, vol. 4, p. 441, 2015.',
              '[12] Datasets (CC BY 4.0): Zenodo 16811928 (Bundestag), 21989732 (Enron), 21989580 (Ethereum), 13365584 (Age of Empires), 8430332 (Angular), 3599150 (CROP); UCI 10.24432/C5KK69 (OULAD).']
    s.text(0.5, 1.45, 6.1, 5.3, [para([run(r, 14)], before=7) for r in refs_l], name="Refs left")
    s.text(6.75, 1.45, 6.1, 5.3, [para([run(r, 14)], before=7) for r in refs_r], name="Refs right")
    s.notes = ("References in IEEE style. Everything on this slide was checked against its publisher record or its arXiv entry before it went on the slide. The last line lists the datasets, all openly licensed. Thank you.")
    S.append(s)
    return S


# ---------------------------------------------------------------- title slide patch
def patch_title_slide(xml: str) -> str:
    big = lambda t, sz, b=True: f'<a:r><a:rPr lang="en-IN" sz="{sz * 100}" b="{1 if b else 0}" dirty="0">{TNR}</a:rPr><a:t>{escape(t)}</a:t></a:r>'
    title_body = ('<a:p><a:pPr algn="ctr"/>' + big("BCSE497J - Project I  |  B.Tech. Computer Science and Engineering", 20) + '</a:p>'
                  '<a:p><a:pPr algn="ctr"><a:spcBef><a:spcPts val="800"/></a:spcBef></a:pPr>' + big("Object-Centric Event Log Mining for Academic Capstone Processes: A Native OCEL 2.0 Approach", 28) + '</a:p>')
    xml = re.sub(r'(<p:ph type="ctrTitle"/>.*?<p:txBody>.*?<a:lstStyle/>).*?(</p:txBody>)', lambda m: m.group(1) + title_body + m.group(2), xml, count=1, flags=re.S)
    xml = xml.replace('<a:off x="1907459" y="1934141"/><a:ext cx="8924544" cy="1089529"/>', f'<a:off x="{E(0.9)}" y="{E(1.95)}"/><a:ext cx="{E(11.53)}" cy="{E(1.75)}"/>')
    xml = xml.replace('<a:bodyPr wrap="square" rtlCol="0"><a:spAutoFit/></a:bodyPr>', '<a:bodyPr wrap="square" rtlCol="0" anchor="ctr"><a:noAutofit/></a:bodyPr>', 1)
    line = lambda t, b=False, hl=False, before=3: (f'<a:p><a:pPr marL="12700"><a:lnSpc><a:spcPct val="100000"/></a:lnSpc><a:spcBef><a:spcPts val="{before * 100}"/></a:spcBef><a:tabLst><a:tab pos="{E(3.9)}" algn="l"/></a:tabLst></a:pPr><a:r><a:rPr lang="en-IN" sz="2000" b="{1 if b else 0}" dirty="0">{TNR}</a:rPr><a:t>{escape(t)}</a:t></a:r></a:p>')
    team = ''.join([line("Team members:", True, before=0), line("Mitisha Sharma\t(23BCE0434)"), line("Tanmay Khambete\t(23BCE0498)"), line("Aakaash Sathya Saravanan\t(23BCE0500)"), line("Faculty guide:", True, before=14), line("Dr. Kalyanaraman P.")])
    xml = re.sub(r'(name="object 3".*?<a:lstStyle/>).*?(</p:txBody>)', lambda m: m.group(1) + team + m.group(2), xml, count=1, flags=re.S)
    xml = xml.replace('<a:off x="2609088" y="3208471"/><a:ext cx="7071360" cy="2460809"/>', f'<a:off x="{E(3.2)}" y="{E(3.95)}"/><a:ext cx="{E(7.0)}" cy="{E(2.7)}"/>')
    xml = xml.replace('<a:bodyPr vert="horz" wrap="square" lIns="0" tIns="12700" rIns="0" bIns="0" rtlCol="0"><a:spAutoFit/></a:bodyPr>', '<a:bodyPr vert="horz" wrap="square" lIns="0" tIns="12700" rIns="0" bIns="0" rtlCol="0"><a:noAutofit/></a:bodyPr>')
    return xml


NOTES_TITLE = ("Good morning, panel! Quick question before we start: have you ever tried to answer a simple question from a spreadsheet, and then realised the spreadsheet was built to answer a completely different one? "
               "That is basically our project. We are Team 1, and this is Object-Centric Event Log Mining for Academic Capstone Processes. "
               "The title is the same one we locked in Review 1. What changed is the evidence behind it, and we will be upfront about that as we go.")


def notes_xml(text: str) -> str:
    paras = "".join(f'<a:p><a:r><a:rPr lang="en-IN" dirty="0"/><a:t>{escape(p)}</a:t></a:r></a:p>' for p in text.split("\n") if p.strip())
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:notes {NS}><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image Placeholder 1"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg"/></p:nvPr></p:nvSpPr><p:spPr/></p:sp>'
            f'<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes Placeholder 2"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{paras}</p:txBody></p:sp>'
            '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>')


# ---------------------------------------------------------------- assemble
def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    with zipfile.ZipFile(TEMPLATE) as z:
        assert not [n for n in z.namelist() if n.startswith("/") or ".." in n.split("/")]
        z.extractall(WORK)
    ppt = WORK / "ppt"
    title_xml = patch_title_slide((ppt / "slides" / "slide1.xml").read_text(encoding="utf-8"))
    for f in (ppt / "slides").glob("slide*.xml"):
        f.unlink()
    for f in (ppt / "slides" / "_rels").glob("*.rels"):
        f.unlink()
    for f in list((ppt / "media").glob("*")):
        if f.name != "image1.png":
            f.unlink()
    slides = build_slides()
    slides[0] = None
    n_total = len(slides)
    (ppt / "notesSlides" / "_rels").mkdir(parents=True, exist_ok=True)
    ct_extra, pres_rels, sld_ids = [], [], []
    for n in range(1, n_total + 1):
        sl = slides[n - 1]
        if n == 1:
            xml, notes, layout, rels = title_xml, NOTES_TITLE, 1, [("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", "../media/image1.png")]
        else:
            xml, notes, layout, rels = sl.xml(n), sl.notes, sl.layout, sl.rels
            for name in set(sl.media):
                shutil.copy(FIG / name, ppt / "media" / name)
        (ppt / "slides" / f"slide{n}.xml").write_text(xml, encoding="utf-8")
        rel_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
                   f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout{layout}.xml"/>']
        rel_xml += [f'<Relationship Id="{rid}" Type="{kind}" Target="{tgt}"/>' for rid, kind, tgt in rels]
        rel_xml.append(f'<Relationship Id="rId99" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide{n}.xml"/></Relationships>')
        (ppt / "slides" / "_rels" / f"slide{n}.xml.rels").write_text("".join(rel_xml), encoding="utf-8")
        (ppt / "notesSlides" / f"notesSlide{n}.xml").write_text(notes_xml(notes), encoding="utf-8")
        (ppt / "notesSlides" / "_rels" / f"notesSlide{n}.xml.rels").write_text(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" Target="../notesMasters/notesMaster1.xml"/>'
            f'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="../slides/slide{n}.xml"/></Relationships>', encoding="utf-8")
        ct_extra.append(f'<Override PartName="/ppt/slides/slide{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                        f'<Override PartName="/ppt/notesSlides/notesSlide{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>')
        pres_rels.append(f'<Relationship Id="rId{100 + n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{n}.xml"/>')
        sld_ids.append(f'<p:sldId id="{255 + n}" r:id="rId{100 + n}"/>')
    # presentation.xml, rels, content types, app.xml
    p = (ppt / "presentation.xml").read_text(encoding="utf-8")
    p = re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>", "<p:sldIdLst>" + "".join(sld_ids) + "</p:sldIdLst>", p, flags=re.S)
    (ppt / "presentation.xml").write_text(p, encoding="utf-8")
    r = (ppt / "_rels" / "presentation.xml.rels").read_text(encoding="utf-8")
    r = re.sub(r'<Relationship Id="rId\d+" Type="[^"]+/slide" Target="slides/slide\d+\.xml"/>', "", r)
    r = r.replace("</Relationships>", "".join(pres_rels) + "</Relationships>")
    (ppt / "_rels" / "presentation.xml.rels").write_text(r, encoding="utf-8")
    ct = (WORK / "[Content_Types].xml").read_text(encoding="utf-8")
    ct = re.sub(r'<Override PartName="/ppt/slides/slide\d+\.xml"[^>]*/>', "", ct)
    ct = ct.replace("</Types>", "".join(ct_extra) + "</Types>")
    (WORK / "[Content_Types].xml").write_text(ct, encoding="utf-8")
    app = (WORK / "docProps" / "app.xml").read_text(encoding="utf-8")
    app = re.sub(r"<Slides>\d+</Slides>", f"<Slides>{n_total}</Slides>", app)
    app = re.sub(r"<Notes>\d+</Notes>", f"<Notes>{n_total}</Notes>", app)
    app = re.sub(r"<HeadingPairs>.*?</TitlesOfParts>", "", app, flags=re.S)
    (WORK / "docProps" / "app.xml").write_text(app, encoding="utf-8")
    thumb = WORK / "docProps" / "thumbnail.jpeg"
    if thumb.exists():
        thumb.unlink()
        rr = (WORK / "_rels" / ".rels").read_text(encoding="utf-8")
        rr = re.sub(r'<Relationship [^>]*thumbnail[^>]*/>', "", rr)
        (WORK / "_rels" / ".rels").write_text(rr, encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(WORK / "[Content_Types].xml", "[Content_Types].xml")
        for f in sorted(WORK.rglob("*")):
            if f.is_file() and f.name != "[Content_Types].xml":
                z.write(f, f.relative_to(WORK).as_posix())
    print("wrote", OUT, f"({OUT.stat().st_size / 1e6:.2f} MB, {n_total} slides)")


if __name__ == "__main__":
    main()
