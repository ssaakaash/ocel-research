#!/usr/bin/env python3
"""Turn docs/research/Journal_Manuscript_Draft.md into a submission-style Word file.

A4, 2.5 cm margins, Times New Roman 12, 1.5 line spacing, continuous line numbers (reviewers like them), page numbers in the
footer, figures and tables with numbered captions. The internal status block and the reference-check note are left out. Items
the authors must supply (affiliations, e-mail, ORCID, contributions, AI-use statement) are highlighted yellow.

Run: realdata/.venv/bin/python scripts/review3/build_manuscript_docx.py
Output: docs/publication/Manuscript_v0.4.docx  (render to PDF with soffice if you need one)
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_engine import Doc, para, run, inline  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "research" / "Journal_Manuscript_Draft.md"
FIG = ROOT / "docs" / "review-3" / "figures"
TEMPLATE = Path("/Users/aakaash/Downloads/BCSE497J Project I Report - Template FINAlL Updated (2).docx")
OUT = ROOT / "docs" / "publication" / "Manuscript_v0.4.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
LINE = 360                                                        # 1.5 line spacing

SECT = ('<w:sectPr><w:headerReference w:type="default" r:id="rId11"/><w:footerReference w:type="default" r:id="rId10"/><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417" w:header="709" w:footer="709" w:gutter="0"/><w:lnNumType w:countBy="1" w:restart="continuous"/>'
        '<w:pgNumType w:start="1"/><w:cols w:space="720"/></w:sectPr>')


def md_inline(t: str) -> str:
    """Markdown emphasis to the engine's mini markup."""
    t = re.sub(r"\*([A-Za-z]+)_([A-Za-z]+)\*", r"//\1//_{\2}", t)                 # *R_T* -> italic R, subscript T
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"//\1//", t)                # *x* -> //x//
    return t


def frag(xml: str) -> list:
    root = etree.fromstring(f'<root xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                            f'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">{xml}</root>')
    return list(root)


def body_p(D: Doc, text: str, **kw):
    kw.setdefault("jc", "left")
    kw.setdefault("line", LINE)
    kw.setdefault("after", 120)
    D.add(para(inline(md_inline(text), sz=24), **kw))


def heading(D: Doc, text: str, level: int):
    if level == 1:
        D.add(para(run(text, b=True, sz=28), before=280, after=120, line=LINE, keep_next=True, outline=0))
    else:
        D.add(para(run(text, b=True, i=False, sz=24), before=200, after=80, line=LINE, keep_next=True, outline=1))


def parse(md: str):
    lines = md.split("\n")
    title = lines[0].lstrip("# ").strip()
    abstract, keywords, body = [], "", []
    mode = "head"
    for ln in lines[1:]:
        if mode == "head":
            if ln.strip() == "---":
                mode = "pre"
            continue
        if mode == "pre":
            if ln.startswith("## Abstract"):
                mode = "abs"
            continue
        if mode == "abs":
            if ln.startswith("**Keywords:**"):
                keywords = ln.replace("**Keywords:**", "").strip()
                mode = "wait"
            elif ln.strip():
                abstract.append(ln.strip())
            continue
        if mode == "wait":
            if ln.strip() == "---":
                mode = "body"
            continue
        body.append(ln)
    return title, abstract, keywords, body


def build_body(D: Doc, title: str, abstract: list[str], keywords: str, body: list[str]) -> int:
    D.chapter = 0
    D.add(para(run(title, b=True, sz=34), jc="center", before=0, after=240, line=LINE))
    D.add(para(inline("Aakaash Sathya Saravanan, Mitisha Sharma, Tanmay Khambete", sz=24) , jc="center", after=60, line=LINE))
    D.add(para(run("[Affiliation of each author: School of Computer Science and Engineering, Vellore Institute of Technology, Vellore, India. Confirm, add department and ORCID iDs.]", sz=22, hl=True), jc="center", after=60, line=LINE))
    D.add(para(run("[Corresponding author: name and e-mail]", sz=22, hl=True), jc="center", after=240, line=LINE))
    D.add(para(run("Abstract", b=True, sz=28), before=120, after=80, line=LINE, keep_next=True))
    for t in abstract:
        body_p(D, t, jc="both")
    D.add(para(run("Keywords: ", b=True, sz=24) + inline(md_inline(keywords), sz=24), after=200, line=LINE))
    words = 0
    i = 0
    in_main = False
    while i < len(body):
        ln = body[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("## "):
            h = ln[3:].strip()
            in_main = bool(re.match(r"\d\.", h)) and not h.startswith("References")
            heading(D, h, 1)
        elif ln.startswith("### "):
            heading(D, ln[4:].strip(), 2)
        elif ln.startswith("!["):
            m = re.match(r"!\[Figure (\d+)\. (.+?)\]\((.+?)\)", ln)
            D.figure(m.group(3), m.group(2), 5.6, num=m.group(1))
            D.parts[-1] = D.parts[-1].replace('w:before="120" w:after="60" w:line="240"', 'w:before="120" w:after="60" w:line="240"')
        elif ln.startswith("**Table "):
            m = re.match(r"\*\*Table (\d+)\.\*\* (.+)", ln)
            num, cap = m.group(1), m.group(2)
            j = i + 1
            while not body[j].lstrip().startswith("|"):
                j += 1
            rows = []
            while j < len(body) and body[j].lstrip().startswith("|"):
                cells = [c.strip() for c in body[j].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append([md_inline(c) for c in cells])
                j += 1
            n = len(rows[0])
            numeric = [all(re.fullmatch(r"[\d.,%/\- ]+( of [\d.,%/\- ]+)?", r[k]) for r in rows[1:]) for k in range(n)]
            D.table(cap.rstrip("."), rows[0], rows[1:], [1.6] + [1.0] * (n - 1), sz=18, align=["right" if numeric[k] else "left" for k in range(n)], num=num)
            i = j
            continue
        elif ln.startswith("- "):
            D.bullets([md_inline(ln[2:])])
        elif re.match(r"\d+\. ", ln):
            body_p(D, ln, ind_left=720, hanging=360)
        elif re.match(r"\[\d+\] ", ln):
            m = re.match(r"(\[\d+\]) (.+)", ln)
            D.add(para(run(m.group(1) + "  ", sz=22) + inline(md_inline(m.group(2)), sz=22), jc="left", after=80, line=300, ind_left=567, hanging=567))
        elif ln.startswith("*Reference check"):
            pass                                                   # internal note, not for the submission file
        else:
            text = md_inline(ln)
            if "{{" in text:
                D.add(para(inline(text, sz=24), jc="left", after=120, line=LINE))
            else:
                body_p(D, ln, jc="both" if in_main else "left")
            if in_main:
                words += len(re.sub(r"[*`]|//", "", ln).split())
        i += 1
    return words


def main() -> None:
    title, abstract, keywords, body = parse(SRC.read_text(encoding="utf-8"))
    D = Doc(FIG)
    words = build_body(D, title, abstract, keywords, body)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "pkg"
        with zipfile.ZipFile(TEMPLATE) as z:
            z.extractall(work)
        doc_path = work / "word" / "document.xml"
        tree = etree.parse(str(doc_path))
        bodyel = tree.getroot().find(f"{{{W}}}body")
        for c in list(bodyel):
            bodyel.remove(c)
        for el in frag("".join(D.parts) + SECT):
            bodyel.append(el)
        tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)
        rels = work / "word" / "_rels" / "document.xml.rels"
        add = ""
        for rid, name in D.rels:
            Image.open(FIG / name).save(work / "word" / "media" / name, "PNG")
            add += f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>'
        rels.write_text(rels.read_text(encoding="utf-8").replace("</Relationships>", add + "</Relationships>"), encoding="utf-8")
        ct = work / "[Content_Types].xml"
        c = ct.read_text(encoding="utf-8")
        if 'Extension="png"' not in c:
            c = c.replace('<Default Extension="rels"', '<Default Extension="png" ContentType="image/png"/><Default Extension="rels"')
        ct.write_text(c, encoding="utf-8")
        num = work / "word" / "numbering.xml"
        n = num.read_text(encoding="utf-8")
        absn = ('<w:abstractNum w:abstractNumId="90"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/>'
                '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:hint="default"/></w:rPr></w:lvl></w:abstractNum>')
        k = n.index("<w:num ")
        n = n[:k] + absn + n[k:]
        num.write_text(n.replace("</w:numbering>", '<w:num w:numId="90"><w:abstractNumId w:val="90"/></w:num></w:numbering>'), encoding="utf-8")
        core = work / "docProps" / "core.xml"
        if core.exists():
            t = core.read_text(encoding="utf-8")
            t = re.sub(r"<dc:title>.*?</dc:title>|<dc:title/>", f"<dc:title>{title}</dc:title>", t, flags=re.S)
            t = re.sub(r"<dc:creator>.*?</dc:creator>|<dc:creator/>", "<dc:creator>Saravanan, Sharma, Khambete</dc:creator>", t, flags=re.S)
            t = re.sub(r"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>", "<cp:lastModifiedBy></cp:lastModifiedBy>", t, flags=re.S)
            t = re.sub(r"(<dcterms:created[^>]*>)[^<]*", r"\g<1>2026-10-27T00:00:00Z", t)
            t = re.sub(r"(<dcterms:modified[^>]*>)[^<]*", r"\g<1>2026-10-27T00:00:00Z", t)
            core.write_text(t, encoding="utf-8")
        app = work / "docProps" / "app.xml"
        if app.exists():
            t = app.read_text(encoding="utf-8")
            for tag in ("TotalTime", "Pages", "Words", "Characters", "Lines", "Paragraphs", "CharactersWithSpaces"):
                t = re.sub(rf"<{tag}>[^<]*</{tag}>", "", t)
            t = re.sub(r"<HeadingPairs>.*?</TitlesOfParts>", "", t, flags=re.S)
            app.write_text(t, encoding="utf-8")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        if OUT.exists():
            OUT.unlink()
        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(work / "[Content_Types].xml", "[Content_Types].xml")
            for f in sorted(work.rglob("*")):
                if f.is_file() and f.name != "[Content_Types].xml":
                    z.write(f, f.relative_to(work).as_posix())
    print(f"wrote {OUT} (main text about {words} words; abstract {sum(len(a.split()) for a in abstract)} words)")


if __name__ == "__main__":
    main()
