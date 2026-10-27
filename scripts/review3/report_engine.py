"""Small OOXML writer for the Review 3 report: paragraphs, headings, figures, tables, code blocks, bookmarks.

It only emits WordprocessingML strings. build_report.py splices them into the VIT template.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path
from xml.sax.saxutils import escape

EMU = 914400
TNR = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:eastAsia="Times New Roman"/>'
MONO = '<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New" w:eastAsia="Courier New"/>'
BODY_W = 9075                    # text width in twips of the chapter section (see build_report.SECT_BODY)
BODY_IN = BODY_W / 1440


def esc(t: str) -> str:
    return escape(t)


def run(text: str, b=False, i=False, sz=24, hl=False, mono=False, sup=False, color=None, u=False) -> str:
    pr = (MONO if mono else TNR) + ("<w:b/><w:bCs/>" if b else "") + ("<w:i/><w:iCs/>" if i else "")
    if color:
        pr += f'<w:color w:val="{color}"/>'
    pr += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    if u:
        pr += '<w:u w:val="single"/>'
    if hl:
        pr += '<w:highlight w:val="yellow"/>'
    if sup:
        pr += '<w:vertAlign w:val="superscript"/>'
    return f'<w:r><w:rPr>{pr}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


_TOKEN = re.compile(r"(\*\*.+?\*\*|//.+?//|`.+?`|\{\{.+?\}\})")


def inline(text: str, sz=24, b=False, i=False) -> str:
    """Mini markup: **bold**, //italic//, `code`, {{highlighted placeholder}}."""
    out = []
    for part in _TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**"):
            out.append(run(part[2:-2], b=True, i=i, sz=sz))
        elif part.startswith("//"):
            out.append(run(part[2:-2], b=b, i=True, sz=sz))
        elif part.startswith("`"):
            out.append(run(part[1:-1], mono=True, sz=max(sz - 2, 16), b=b))
        elif part.startswith("{{"):
            out.append(run(part[2:-2], b=b, i=i, sz=sz, hl=True))
        else:
            out.append(run(part, b=b, i=i, sz=sz))
    return "".join(out)


def ppr(jc=None, before=0, after=120, line=276, ind_left=None, ind_first=None, hanging=None, keep_next=False, keep_lines=False,
        page_break_before=False, outline=None, shade=None, tabs=None, widow=True) -> str:
    x = ""
    if keep_next:
        x += "<w:keepNext/>"
    if keep_lines:
        x += "<w:keepLines/>"
    if page_break_before:
        x += "<w:pageBreakBefore/>"
    if tabs:
        x += "<w:tabs>" + "".join(f'<w:tab w:val="{v}" w:pos="{p}"' + (f' w:leader="{l}"' if l else "") + "/>" for v, p, l in tabs) + "</w:tabs>"
    if shade:
        x += f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>'
    x += f'<w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>'
    ind = ""
    if ind_left is not None:
        ind += f' w:left="{ind_left}"'
    if ind_first is not None:
        ind += f' w:firstLine="{ind_first}"'
    if hanging is not None:
        ind += f' w:hanging="{hanging}"'
    if ind:
        x += f"<w:ind{ind}/>"
    if jc:
        x += f'<w:jc w:val="{jc}"/>'
    if outline is not None:
        x += f'<w:outlineLvl w:val="{outline}"/>'
    return f"<w:pPr>{x}</w:pPr>"


def para(runs: str, **kw) -> str:
    return f"<w:p>{ppr(**kw)}{runs}</w:p>"


def png_size(path: Path):
    with path.open("rb") as h:
        h.read(16)
        return struct.unpack(">II", h.read(8))


class Doc:
    def __init__(self, fig_dir: Path, page_labels: dict | None = None):
        self.fig_dir = fig_dir
        self.parts: list[str] = []
        self.rels: list[tuple[str, str]] = []        # (rId, media name)
        self.bm = 1000
        self.chapter = 0
        self.fig_n = 0
        self.tab_n = 0
        self.toc: list[dict] = []                  # level, num, title, bookmark
        self.figs: list[dict] = []
        self.tabs: list[dict] = []
        self.labels = page_labels or {}
        self.img_id = 0

    # ---------------------------------------------------------------- low level
    def add(self, xml: str):
        self.parts.append(xml)

    def bookmark(self, inner: str, name: str) -> str:
        self.bm += 1
        return f'<w:bookmarkStart w:id="{self.bm}" w:name="{name}"/>{inner}<w:bookmarkEnd w:id="{self.bm}"/>'

    # ---------------------------------------------------------------- text
    def p(self, text: str, **kw):
        kw.setdefault("jc", "both")
        self.add(para(inline(text), **kw))

    def pb(self):
        self.add('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def chapter_start(self, title: str):
        self.chapter += 1
        self.fig_n = 0
        self.tab_n = 0
        bm = f"_Toc_ch{self.chapter}"
        self.toc.append({"level": 1, "num": f"{self.chapter}.", "title": title.upper(), "bm": bm})
        self.add(para(run(f"CHAPTER {self.chapter}", b=True, sz=28), jc="center", before=0, after=60, page_break_before=True, keep_next=True))
        self.add(para(self.bookmark(run(title.upper(), b=True, sz=28), bm), jc="center", before=0, after=240, keep_next=True, outline=0))

    def unnumbered_chapter(self, title: str, bm: str, toc_title: str | None = None, page_break=True):
        self.toc.append({"level": 1, "num": "", "title": toc_title or title.upper(), "bm": bm})
        self.add(para(self.bookmark(run(title.upper(), b=True, sz=28), bm), jc="center", before=0, after=240, keep_next=True, outline=0, page_break_before=page_break))

    def h2(self, title: str):
        self.sec = getattr(self, "sec", 0)
        if not hasattr(self, "_h2_for") or self._h2_for != self.chapter:
            self._h2_for, self.sec, self.sub = self.chapter, 0, 0
        self.sec += 1
        self.sub = 0
        num = f"{self.chapter}.{self.sec}"
        bm = f"_Toc_{self.chapter}_{self.sec}"
        self.toc.append({"level": 2, "num": num, "title": title, "bm": bm})
        self.add(para(self.bookmark(run(f"{num}  {title}", b=True, sz=24), bm), before=200, after=100, keep_next=True, outline=1))

    def h3(self, title: str):
        self.sub += 1
        num = f"{self.chapter}.{self.sec}.{self.sub}"
        bm = f"_Toc_{self.chapter}_{self.sec}_{self.sub}"
        self.toc.append({"level": 3, "num": num, "title": title, "bm": bm})
        self.add(para(self.bookmark(run(f"{num}  {title}", b=True, i=True, sz=24), bm), before=140, after=80, keep_next=True, outline=2))

    def h4(self, title: str):
        """Run-in heading without a TOC entry."""
        self.add(para(run(title, b=True, sz=24), before=100, after=60, keep_next=True))

    def bullets(self, items: list[str], num_id: int = 90):
        for it in items:
            self.add(f'<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
                     f'<w:spacing w:before="0" w:after="60" w:line="276" w:lineRule="auto"/><w:ind w:left="720" w:hanging="360"/><w:jc w:val="both"/></w:pPr>{inline(it)}</w:p>')

    def numbered(self, items: list[str], num_id: int):
        for it in items:
            self.add(f'<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
                     f'<w:spacing w:before="0" w:after="60" w:line="276" w:lineRule="auto"/><w:ind w:left="720" w:hanging="360"/><w:jc w:val="both"/></w:pPr>{inline(it)}</w:p>')

    def code(self, lines: list[str], sz=17):
        n = len(lines)
        for k, ln in enumerate(lines):
            self.add(f'<w:p><w:pPr><w:keepLines/><w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
                     f'<w:ind w:left="113" w:right="113"/></w:pPr>{run(ln if ln else " ", mono=True, sz=sz)}</w:p>')
        self.add(para("", after=120, line=240))

    # ---------------------------------------------------------------- figures
    def figure(self, file: str, caption: str, width_in: float = 6.0, alt: str | None = None):
        path = self.fig_dir / file
        pw, ph = png_size(path)
        width_in = min(width_in, BODY_IN)
        cx = int(width_in * EMU)
        cy = int(cx * ph / pw)
        rid = f"rIdImg{len(self.rels) + 1}"
        self.rels.append((rid, file))
        self.img_id += 1
        self.fig_n += 1
        label = f"{self.chapter}.{self.fig_n}"
        bm = f"_Fig_{self.chapter}_{self.fig_n}"
        self.figs.append({"num": label, "title": caption, "bm": bm})
        desc = esc(alt or caption)
        self.add(
            f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{500 + self.img_id}" name="Figure {label}" descr="{desc}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{self.img_id}" name="{file}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            f'</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
        cap = self.bookmark(run(f"Figure {label}: ", b=True, sz=20) + run(caption, sz=20), bm)
        self.add(para(cap, jc="center", before=0, after=200, line=240))

    # ---------------------------------------------------------------- tables
    def table(self, caption: str, header: list[str], rows: list[list[str]], widths: list[float], sz=20, align=None, bold_first=False, keep=None):
        """widths are relative; align is a list of 'left'/'center'/'right' per column."""
        self.tab_n += 1
        label = f"{self.chapter}.{self.tab_n}"
        bm = f"_Tab_{self.chapter}_{self.tab_n}"
        self.tabs.append({"num": label, "title": caption, "bm": bm})
        cap = self.bookmark(run(f"Table {label}: ", b=True, sz=20) + run(caption, sz=20), bm)
        self.add(para(cap, jc="center", before=160, after=80, line=240, keep_next=True))
        keep = (len(rows) <= 9) if keep is None else keep
        tot = sum(widths)
        tw = [int(BODY_W * w / tot) for w in widths]
        align = align or ["left"] * len(header)
        border = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="808080"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
        out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(tw)}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{border}</w:tblBorders><w:tblLayout w:type="fixed"/>'
               f'<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
               f'<w:tblGrid>{"".join(f"<w:gridCol w:w=\"{w}\"/>" for w in tw)}</w:tblGrid>']

        def cell(text, w, head=False, k=0, kn=False):
            shade = '<w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/>' if head else ""
            jc = "center" if head else align[k]
            body = inline(text, sz=sz, b=head or (bold_first and k == 0))
            return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shade}<w:vAlign w:val="center"/></w:tcPr>'
                    f'<w:p><w:pPr>{"<w:keepNext/>" if kn else ""}<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="{jc}"/></w:pPr>{body}</w:p></w:tc>')
        out.append('<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' + "".join(cell(h, tw[k], True, k, keep) for k, h in enumerate(header)) + "</w:tr>")
        for n, r in enumerate(rows):
            out.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(cell(c, tw[k], False, k, keep and n < len(rows) - 1) for k, c in enumerate(r)) + "</w:tr>")
        out.append("</w:tbl>")
        self.add("".join(out))
        self.add(para("", after=120, line=240))

    # ---------------------------------------------------------------- front-matter helpers
    def toc_rows(self) -> list[dict]:
        return self.toc


def pageref(bm: str, cached: str, sz=24, b=False) -> str:
    rp = f'<w:rPr>{TNR}{"<w:b/>" if b else ""}<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>'
    return (f'<w:r>{rp}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{rp}<w:instrText xml:space="preserve"> PAGEREF {bm} \\h </w:instrText></w:r>'
            f'<w:r>{rp}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{rp}<w:t>{esc(cached)}</w:t></w:r><w:r>{rp}<w:fldChar w:fldCharType="end"/></w:r>')


def plain_table(rows: list[list[str]], widths: list[int], sz=22, bold_cols=(), jcs=None, header=None, borders=False) -> str:
    """Borderless layout table used for the contents / list pages."""
    jcs = jcs or ["left"] * len(widths)
    b = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="808080"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV")) if borders else ""
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{b}</w:tblBorders><w:tblLayout w:type="fixed"/>'
           f'<w:tblCellMar><w:top w:w="15" w:type="dxa"/><w:left w:w="60" w:type="dxa"/><w:bottom w:w="15" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           f'<w:tblGrid>{"".join(f"<w:gridCol w:w=\"{w}\"/>" for w in widths)}</w:tblGrid>']
    allrows = ([header] if header else []) + rows
    for n, r in enumerate(allrows):
        is_head = bool(header) and n == 0
        out.append('<w:tr><w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if is_head else "") + '</w:trPr>')
        for k, c in enumerate(r):
            content = c if c.startswith("<w:r") or c.startswith("<w:bookmark") else inline(c, sz=sz, b=is_head or k in bold_cols)
            out.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[k]}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                       f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="300" w:lineRule="auto"/><w:jc w:val="{"center" if is_head else jcs[k]}"/></w:pPr>{content}</w:p></w:tc>')
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)
