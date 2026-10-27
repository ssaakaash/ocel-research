#!/usr/bin/env python3
"""Build the BCSE497J Project-I report from the VIT template.

The template's cover, declaration, certificate and acknowledgement pages are edited in place; everything from the table of
contents onward is generated (report_engine.py, report_chapters_*.py). Page numbers in the contents lists are filled in by a
second pass after LibreOffice renders the first pass.

Run: realdata/.venv/bin/python scripts/review3/build_report.py
Needs: soffice (set SOFFICE to a wrapper command if plain `soffice` hangs) and pdftotext for the page numbers.
Output: docs/review-3/Team1_BCSE497J_Project_I_Report.docx
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_chapters_1_4 as A  # noqa: E402
import report_chapters_5_9 as B  # noqa: E402
import report_engine as E  # noqa: E402
from report_engine import Doc, TNR, esc, inline, pageref, para, plain_table, run  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path("/Users/aakaash/Downloads/BCSE497J Project I Report - Template FINAlL Updated (2).docx")
FIG = ROOT / "docs" / "review-3" / "figures"
DEMO = ROOT / "docs" / "review-3" / "demo"
RES = ROOT / "realdata" / "results"
SRC = ROOT / "realdata" / "src"
OUT = ROOT / "docs" / "review-3" / "Team1_BCSE497J_Project_I_Report.docx"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSW = {"w": W}
TITLE = "Object-Centric Event Log Mining for Academic Capstone Processes: A Native OCEL 2.0 Approach"
TEAM = [("23BCE0434", "Mitisha Sharma"), ("23BCE0498", "Tanmay Khambete"), ("23BCE0500", "Aakaash Sathya Saravanan")]   # sorted on register number
GUIDE = "Dr. Kalyanaraman P."

SECT_FRONT = ('<w:sectPr><w:headerReference w:type="default" r:id="rId9"/><w:footerReference w:type="default" r:id="rId10"/><w:pgSz w:w="11910" w:h="16840"/>'
              '<w:pgMar w:top="851" w:right="1320" w:bottom="280" w:left="1240" w:header="1447" w:footer="459" w:gutter="0"/><w:pgNumType w:fmt="lowerRoman" w:start="1"/><w:cols w:space="720"/></w:sectPr>')
SECT_BODY = ('<w:sectPr><w:headerReference w:type="default" r:id="rId11"/><w:footerReference w:type="default" r:id="rId10"/><w:pgSz w:w="11910" w:h="16840"/>'
             '<w:pgMar w:top="1418" w:right="1134" w:bottom="1418" w:left="1701" w:header="709" w:footer="709" w:gutter="0"/><w:pgNumType w:start="1"/><w:cols w:space="720"/></w:sectPr>')

ABSTRACT = [
    "When a student leader submits a report on a capstone portal, that single event concerns a project, a team, three students, a guide and a report version. "
    "Process mining, however, requires every event to belong to exactly one case. When the event is flattened to one case notion, it can be copied into several cases (convergence), "
    "dropped altogether (deficiency) or merged with repeated events that belong to other objects (divergence). Object-centric event logs, in the OCEL 2.0 standard, keep the many-to-many links instead.",

    "We began this project to study capstone review processes with OCEL 2.0, but portal logs could not be obtained. We also found no public capstone or thesis-management event log. "
    "We therefore narrowed our claims. The capstone is presented as a documented OCEL 2.0 design, and we measured flattening on seven real public logs: Gerrit code review (CROP), "
    "Open University learning analytics (OULAD), Angular commits, German Bundestag procedures, Enron e-mail, an Ethereum window and Age of Empires II matches. No synthetic or simulated data was used anywhere.",

    "We built a reproducible pipeline that downloads and checks each source, converts the Gerrit and OULAD data to OCEL 2.0, computes flattening distortion for 38 case notions, "
    "and compares what an analyst would read off a flat view against the object-centric one: activity rankings, directly-follows edges, process variants, entity rankings and the process model a miner discovers.",

    "The logs fall into three groups. In star logs (CROP, OULAD) every event touches one object of each type, so flattening copies nothing. In partitioned logs (Bundestag, Age of Empires II, Ethereum) "
    "one case notion drops 69% to 91% of the events in the median. In fan-out logs (Angular, Enron) flattening does duplicate events, up to 81.65 copies of one event in Angular. "
    "Duplication alone rarely changes an activity ranking, since only 2 of 38 case notions fall below a rank correlation of 0.95. The bigger effect is narrowing: in 20 of 38 case notions "
    "the flat log shows fewer than half of the process's activities, and 2 of the 15 case notions that cover at least half of their log are among them. A model discovered from a narrowed flat log still reaches a replay fitness of 0.955 or more, "
    "so the usual quality check gives no warning. Counting rows in a denormalised flat export can also invert an entity ranking, with worst-case rank correlations of 0.16 (Enron), "
    "-0.01 (Ethereum) and -0.41 (Age of Empires II).",

    "We checked parts of the pipeline with an independent SQL implementation, a brute-force self-check, an independent recomputation of the OULAD counts and byte-identical re-runs. "
    "A plain-Python re-implementation reproduces the distortion metrics exactly on all seven full logs. Those checks caught three bugs of our own, which we fixed. No one outside the team has labelled the findings, and the capstone model is still a design that has not met portal data. "
    "The measurement work is under review at the Journal of Intelligent Information Systems.",
]

ABBREVIATIONS = [
    ("AGPL", "GNU Affero General Public Licence"), ("AoE2", "Age of Empires II"), ("CC BY", "Creative Commons Attribution"), ("COOC", "Cross-Object Observability Coverage"), ("CROP", "Code Review Open Platform (Gerrit code-review dataset)"),
    ("CSV", "Comma-Separated Values"), ("DF", "Directly-Follows"), ("DFD", "Data Flow Diagram"), ("E2O", "Event-to-Object"), ("HTTP", "Hypertext Transfer Protocol"),
    ("JSON", "JavaScript Object Notation"), ("MD5", "Message-Digest Algorithm 5"), ("MSR", "Mining Software Repositories"), ("O2O", "Object-to-Object"),
    ("OCEL", "Object-Centric Event Log"), ("OULAD", "Open University Learning Analytics Dataset"), ("SCOPE", "School of Computer Science and Engineering"),
    ("SDG", "Sustainable Development Goal"), ("SHA-256", "Secure Hash Algorithm, 256-bit"), ("SQL", "Structured Query Language"), ("TRL", "Technology Readiness Level"),
    ("UCI", "University of California, Irvine"), ("UML", "Unified Modeling Language"), ("VIT", "Vellore Institute of Technology"), ("XML", "Extensible Markup Language"),
]
SYMBOLS = [
    ("T", "Object type chosen as the case notion"), ("U", "Another object type, the entities being ranked or nested inside T"),
    ("δ(T)", "Deficiency: share of events with no T-object"), ("κ(T)", "Convergence share: share of covered events related to two or more T-objects"),
    ("c(T)", "Copies per event: flat rows divided by covered events"), ("ρ", "Spearman rank correlation coefficient"),
]


# ------------------------------------------------------------------------------------------------ front matter
def frag(xml: str) -> list:
    """Parse WordprocessingML fragments into elements (namespaces borrowed from the template root)."""
    root = etree.fromstring(f'<root xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                            f'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">{xml}</root>')
    return list(root)


def set_runs(p, runs_xml: str):
    for ch in list(p):
        if ch.tag != f"{{{W}}}pPr":
            p.remove(ch)
    for el in frag(runs_xml):
        p.append(el)


def set_ppr_spacing(p, **attrs):
    ppr = p.find("w:pPr", NSW)
    sp = ppr.find("w:spacing", NSW)
    if sp is None:
        sp = etree.SubElement(ppr, f"{{{W}}}spacing")
    for k, v in attrs.items():
        sp.set(f"{{{W}}}{k}", str(v))


def edit_front(body):
    ps = list(body.iter(f"{{{W}}}p"))
    team_names = [n.upper() for _, n in TEAM]
    # cover page
    set_runs(ps[2], run(TITLE.upper(), b=True, sz=36))
    set_ppr_spacing(ps[2], line=360, lineRule="auto")
    set_runs(ps[12], run("Computer Science and Engineering", b=True, sz=26))
    for k, (reg, name) in enumerate(TEAM):
        set_runs(ps[16 + 2 * k], run(reg, b=True, sz=26))
        set_runs(ps[17 + 2 * k], run(name.upper(), b=True, sz=26))
    set_runs(ps[25], run(GUIDE, b=True, sz=26))
    set_runs(ps[26], run("Professor Grade 1", sz=26))
    # declaration
    set_runs(ps[36], inline(f"We hereby declare that the project entitled **{TITLE}** submitted by us, for the award of the degree of //Bachelor of Technology in Computer Science and Engineering// to VIT "
                            f"is a record of bonafide work carried out by us under the supervision of {GUIDE}", sz=24))
    set_runs(ps[37], inline("We further declare that the work reported in this project has not been submitted and will not be submitted, either in part or in full, for the award of any other degree or diploma "
                            "in this institute or any other institute or university.", sz=24))
    sig = []
    for _, name in TEAM:
        sig.append(f'<w:p><w:pPr><w:spacing w:before="200" w:after="0"/><w:ind w:left="480"/></w:pPr>{run("Signature:  ______________________    ", sz=24)}{run(name, b=True, sz=24)}</w:p>')
    sig_els = frag("".join(sig))
    parent = ps[46].getparent()
    idx = parent.index(ps[46])
    parent.remove(ps[46])
    for k, el in enumerate(sig_els):
        parent.insert(idx + k, el)
    # certificate
    names = ", ".join(f"{n} ({r})" for r, n in TEAM[:-1]) + f" and {TEAM[-1][1]} ({TEAM[-1][0]})"
    set_runs(ps[56], inline(f"This is to certify that the project entitled **{TITLE}** submitted by **{names}**, School of Computer Science and Engineering, VIT, for the award of the degree of "
                            "//Bachelor of Technology in Computer Science and Engineering//, is a record of bonafide work carried out by them under my supervision during Fall Semester 2026-2027, "
                            "as per the VIT code of academic and research ethics.", sz=24))
    set_runs(ps[82], run("Dr. Boominathan P", b=True, sz=24))
    set_runs(ps[83], run("Computer Science and Engineering", b=True, sz=24))
    # acknowledgements
    set_runs(ps[88], inline("We are deeply grateful to the management of Vellore Institute of Technology (VIT) for giving us the opportunity and the resources to take up this project. "
                            "Their commitment to a conducive learning environment has been important to our academic journey, and the support and infrastructure provided by VIT let us explore and develop our ideas.", sz=24))
    set_runs(ps[90], inline("Our sincere thanks to Dr. Jaisankar N, the Dean of the School of Computer Science and Engineering (SCOPE), for the Dean's unwavering support and encouragement. "
                            "The Dean's leadership and vision have inspired us to strive for excellence, and the dedication to academic excellence and innovation has been a constant source of motivation. "
                            "We appreciate the effort that goes into creating an environment that nurtures creativity and critical thinking.", sz=24))
    set_runs(ps[92], inline("We express our profound appreciation to Dr. Boominathan P, the Head of the Department of Computer Science and Engineering, for their insightful guidance and continuous support. "
                            "Their expertise and advice shaped the direction of our project, and the collaborative, supportive atmosphere they keep made learning easier for us.", sz=24))
    set_runs(ps[94], inline(f"We are immensely thankful to our project guide, {GUIDE}, for their dedicated mentorship and valuable feedback. "
                            "Their patience, knowledge and encouragement carried us through this project, and the time they spent sharing expertise and giving thoughtful guidance helped us refine our ideas and methods.", sz=24))
    sigs = frag("".join(f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:ind w:left="5000"/></w:pPr>{run(n, b=True, sz=24)}</w:p>' for _, n in TEAM))
    parent = ps[100].getparent()
    idx = parent.index(ps[100])
    parent.remove(ps[100])
    for k, el in enumerate(sigs):
        parent.insert(idx + k, el)
    # instruction paragraphs left in the template
    for i in (3, 22, 52, 78, 4, 5, 28, 29, 76, 77, 79, 80, 81):       # instructions, then empty spacer paragraphs
        ps[i].getparent().remove(ps[i])
    return ps[101]                                                      # the page break before the template's contents page


# ------------------------------------------------------------------------------------------------ generated pages
_BM = [800]


def centered_heading(text: str, bm: str | None = None, sz=28, page_break=False) -> str:
    r = run(text, b=True, sz=sz)
    if bm:
        _BM[0] += 1
        r = f'<w:bookmarkStart w:id="{_BM[0]}" w:name="{bm}"/>{r}<w:bookmarkEnd w:id="{_BM[0]}"/>'
    pb = "<w:pageBreakBefore/>" if page_break else ""
    return f'<w:p><w:pPr><w:keepNext/>{pb}<w:spacing w:before="0" w:after="240" w:line="360" w:lineRule="auto"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/></w:pPr>{r}</w:p>'


def roman(n: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def front_pages(D: Doc, labels: dict) -> str:
    out = []
    g = lambda k: labels.get(k, "0")
    # table of contents
    out.append(centered_heading("TABLE OF CONTENTS", page_break=False))
    roman = lambda n: next(r for v, r in [(10, "x"), (9, "ix"), (8, "viii"), (7, "vii"), (6, "vi"), (5, "v"), (4, "iv"), (3, "iii"), (2, "ii"), (1, "i")] if str(v) == str(n)) if str(n).isdigit() and 1 <= int(n) <= 10 else n
    rows = [["", "Abstract", f"**{roman(g('_Toc_abstract'))}**"]]   # plain text: a PAGEREF field would be re-rendered in arabic numerals by LibreOffice
    for e in D.toc:
        lvl = e["level"]
        pad = " " * (0 if lvl == 1 else 4 if lvl == 2 else 9)
        title = e["title"] if lvl == 1 else f"{e['num']} {e['title']}"
        if lvl == 1:
            title = f"**{title}**"
        rows.append([f"**{e['num']}**" if lvl == 1 and e["num"] else "", pad + title, pageref(e["bm"], g(e["bm"]), sz=22, b=(lvl == 1))])
    out.append(plain_table(rows, [800, 7350, 1200], sz=22, jcs=["left", "left", "center"], header=["Sl.No", "Contents", "Page No."]))
    # list of figures
    out.append(centered_heading("LIST OF FIGURES", bm="_Toc_lof", page_break=True))
    out.append(plain_table([[f["num"], f["title"], pageref(f["bm"], g(f["bm"]), sz=22)] for f in D.figs], [1300, 6800, 1250], sz=22, jcs=["center", "left", "center"], header=["Figure No.", "Title", "Page No."]))
    out.append(centered_heading("LIST OF TABLES", bm="_Toc_lot", page_break=True))
    out.append(plain_table([[t["num"], t["title"], pageref(t["bm"], g(t["bm"]), sz=22)] for t in D.tabs], [1300, 6800, 1250], sz=22, jcs=["center", "left", "center"], header=["Table No.", "Title", "Page No."]))
    out.append(centered_heading("LIST OF ABBREVIATIONS", bm="_Toc_abbr", page_break=True))
    out.append(plain_table([[f"**{a}**", d] for a, d in sorted(ABBREVIATIONS, key=lambda x: x[0].lower())], [2000, 7350], sz=24, jcs=["left", "left"]))
    out.append(centered_heading("SYMBOLS AND NOTATIONS", bm="_Toc_sym", page_break=True))
    out.append(plain_table([[f"**{a}**", d] for a, d in SYMBOLS], [2000, 7350], sz=24, jcs=["left", "left"]))
    out.append(centered_heading("ABSTRACT", bm="_Toc_abstract", sz=32, page_break=True))
    words = 0
    for t in ABSTRACT:
        words += len(t.split())
        out.append(para(inline(t, sz=24), jc="both", before=0, after=140, line=276))
    assert 300 <= words <= 500, f"abstract has {words} words"
    out.append(f'<w:p><w:pPr>{SECT_FRONT}</w:pPr></w:p>')
    print(f"abstract: {words} words")
    return "".join(out)


def make_body(labels: dict) -> tuple[Doc, str]:
    D = Doc(FIG)
    A.ch1(D)
    A.ch2(D)
    A.ch3(D)
    A.ch4(D)
    B.ch5(D)
    B.ch6(D, DEMO)
    B.ch7(D, RES)
    B.ch8(D)
    B.ch9(D)
    B.appendix(D, SRC)
    return D, "".join(D.parts)


# ------------------------------------------------------------------------------------------------ assembly
def assemble(labels: dict, out: Path) -> Doc:
    D, body_xml = make_body(labels)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "pkg"
        with zipfile.ZipFile(TEMPLATE) as z:
            assert not [n for n in z.namelist() if n.startswith("/") or ".." in n.split("/")]
            z.extractall(work)
        doc_path = work / "word" / "document.xml"
        tree = etree.parse(str(doc_path))
        body = tree.getroot().find("w:body", NSW)
        cut_el = edit_front(body)
        kids = list(body)
        for c in kids[kids.index(cut_el) + 1:]:
            body.remove(c)
        gen = front_pages(D, labels) + body_xml
        for el in frag(gen):
            body.append(el)
        for el in frag(SECT_BODY):
            body.append(el)
        tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)

        # media + relationships
        media = work / "word" / "media"
        rels_path = work / "word" / "_rels" / "document.xml.rels"
        rels = rels_path.read_text(encoding="utf-8")
        add = ""
        for rid, name in D.rels:
            Image.open(FIG / name).save(media / name, "PNG")        # re-save without the plotting library's metadata text
            add += f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>'
        rels_path.write_text(rels.replace("</Relationships>", add + "</Relationships>"), encoding="utf-8")
        ct_path = work / "[Content_Types].xml"
        ct = ct_path.read_text(encoding="utf-8")
        if 'Extension="png"' not in ct:
            ct = ct.replace('<Default Extension="rels"', '<Default Extension="png" ContentType="image/png"/><Default Extension="rels"')
        ct_path.write_text(ct, encoding="utf-8")
        # bullet list definition
        num_path = work / "word" / "numbering.xml"
        num = num_path.read_text(encoding="utf-8")
        absn = ('<w:abstractNum w:abstractNumId="90"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/>'
                '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:hint="default"/></w:rPr></w:lvl></w:abstractNum>')
        first_num = num.index("<w:num ")
        num = num[:first_num] + absn + num[first_num:]
        num = num.replace("</w:numbering>", '<w:num w:numId="90"><w:abstractNumId w:val="90"/></w:num></w:numbering>')
        num_path.write_text(num, encoding="utf-8")
        # document properties
        core = work / "docProps" / "core.xml"
        if core.exists():
            c = core.read_text(encoding="utf-8")
            c = re.sub(r"<dc:title>.*?</dc:title>|<dc:title/>", f"<dc:title>{esc(TITLE)}</dc:title>", c, flags=re.S)
            if "<dc:title>" not in c:
                c = c.replace("</cp:coreProperties>", f"<dc:title>{esc(TITLE)}</dc:title></cp:coreProperties>")
            c = re.sub(r"<dc:creator>.*?</dc:creator>|<dc:creator/>", "<dc:creator>Team 1, BCSE497J</dc:creator>", c, flags=re.S)
            c = re.sub(r"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>", "<cp:lastModifiedBy>Team 1, BCSE497J</cp:lastModifiedBy>", c, flags=re.S)
            c = re.sub(r"(<dcterms:created[^>]*>)[^<]*", r"\g<1>2026-10-27T00:00:00Z", c)
            c = re.sub(r"(<dcterms:modified[^>]*>)[^<]*", r"\g<1>2026-10-27T00:00:00Z", c)
            core.write_text(c, encoding="utf-8")
        app = work / "docProps" / "app.xml"
        if app.exists():                                          # drop the template's stale page and word counts; Word recomputes them
            a_xml = app.read_text(encoding="utf-8")
            for tag in ("TotalTime", "Pages", "Words", "Characters", "Lines", "Paragraphs", "CharactersWithSpaces"):
                a_xml = re.sub(rf"<{tag}>[^<]*</{tag}>", "", a_xml)
            a_xml = re.sub(r"<HeadingPairs>.*?</TitlesOfParts>", "", a_xml, flags=re.S)
            app.write_text(a_xml, encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(work / "[Content_Types].xml", "[Content_Types].xml")
            for f in sorted(work.rglob("*")):
                if f.is_file() and f.name != "[Content_Types].xml":
                    z.write(f, f.relative_to(work).as_posix())
    return D


# ------------------------------------------------------------------------------------------------ page numbers
def render_pages(docx: Path) -> list[str]:
    outdir = docx.parent / "_render"
    outdir.mkdir(exist_ok=True)
    soffice = shlex.split(os.environ.get("SOFFICE", "soffice"))
    subprocess.run(soffice + ["--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx)], check=True, capture_output=True, timeout=600)
    pdf = outdir / (docx.stem + ".pdf")
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout).group(1))
    pages = []
    for k in range(1, n + 1):
        pages.append(subprocess.run(["pdftotext", "-f", str(k), "-l", str(k), "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout)
    return pages


def compute_labels(D: Doc, pages: list[str]) -> dict:
    flat = [re.sub(r"[ \t ]+", " ", p) for p in pages]
    first_body = next(k for k, p in enumerate(flat) if "CHAPTER 1" in p and k > 1)
    label = lambda k: str(k - first_body + 1) if k >= first_body else roman(k)          # k is a zero-based pdf page; the cover is page 0
    labels = {}

    def find(pattern: str, start: int) -> int | None:
        rx = re.compile(pattern, re.M)
        for k in range(start, len(flat)):
            if rx.search(flat[k]):
                return k
        return None

    k = find(r"^\s*ABSTRACT\s*$", 1)
    labels["_Toc_abstract"] = label(k) if k is not None else "0"
    for e in D.toc:
        if e["level"] == 1:
            pat = r"^\s*" + re.escape(e["title"]).replace(r"\ ", r"\s+") + r"\s*$"
        else:
            pat = r"^\s*" + re.escape(e["num"]) + r"\s+" + r"\s+".join(re.escape(w) for w in e["title"].split()) + r"(\s|$)"
        k = find(pat, first_body)
        labels[e["bm"]] = label(k) if k is not None else "0"
        if k is None:
            print("  page not found for", e["num"], e["title"])
    for kind, items, tag in (("figure", D.figs, "Figure"), ("table", D.tabs, "Table")):
        for it in items:
            k = find(r"^\s*" + tag + r"\s+" + re.escape(it["num"]) + r":", first_body)
            labels[it["bm"]] = label(k) if k is not None else "0"
            if k is None:
                print("  page not found for", tag, it["num"])
    print(f"body starts on pdf page {first_body + 1} of {len(flat)}")
    return labels


def main() -> None:
    work_dir = Path(tempfile.mkdtemp(prefix="report_pass_"))
    try:
        first = work_dir / "pass1.docx"
        D = assemble({}, first)
        labels = compute_labels(D, render_pages(first))
        D = assemble(labels, OUT)
        second = work_dir / "pass2.docx"
        shutil.copy(OUT, second)
        check = compute_labels(D, render_pages(second))
        diff = {k: (labels.get(k), v) for k, v in check.items() if labels.get(k) != v}
        print("page numbers stable" if not diff else f"page numbers moved after the second pass: {diff}")
        if diff:
            D = assemble(check, OUT)
            shutil.copy(OUT, second)
            render_pages(second)
        keep = os.environ.get("REPORT_RENDER_DIR")
        if keep:
            Path(keep).mkdir(parents=True, exist_ok=True)
            shutil.copy(work_dir / "_render" / "pass2.pdf", Path(keep) / (OUT.stem + ".pdf"))
        print("wrote", OUT, f"({OUT.stat().st_size / 1e6:.2f} MB)")
        unused = sorted(set(E.HUMANISED) - E.HUMANISED_USED)
        print(f"reworded paragraphs applied: {len(E.HUMANISED_USED)} of {len(E.HUMANISED)}" + (f"; not matched (generated text changed): {[u[:60] for u in unused]}" if unused else ""))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
