#!/usr/bin/env python3
"""Draw every figure for the Review 3 deck and the project report (PNG, 200 dpi).

Result charts read the numbers from realdata/results/*.csv, so they cannot drift from the analysis.
Run: realdata/.venv/bin/python scripts/review3/make_figures.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "review-3" / "figures"
RES = ROOT / "realdata" / "results"
OUT.mkdir(parents=True, exist_ok=True)

INK, MUTED, GRID, SURFACE = "#1f2328", "#5b616b", "#e3e6ea", "#ffffff"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#9aa1ab"
FILL, FILL_B, FILL_O, FILL_A = "#f3f6fa", "#e6f0fc", "#fdeee7", "#e3f6ee"
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "axes.edgecolor": MUTED, "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "savefig.facecolor": SURFACE, "figure.facecolor": SURFACE,
                     "pdf.fonttype": 42})   # TrueType fonts in PDFs (publishers reject Type 3)


def canvas(w=100, h=58, size=(10, 5.8)):
    fig, ax = plt.subplots(figsize=(size[0] * 0.84, size[1] * 0.84))
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.set_aspect("equal"); ax.axis("off")
    fig.subplots_adjust(0.005, 0.005, 0.995, 0.995)
    return fig, ax


def box(ax, x, y, w, h, text, fc=FILL, ec=BLUE, fs=10, bold=False, dashed=False, color=INK, lw=1.5, r=1.2, va="center", ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, ls="--" if dashed else "-"))
    tx = x + (w / 2 if ha == "center" else 1.2)
    ty = y + (h / 2 if va == "center" else h - 1.2)
    ax.text(tx, ty, text, ha=ha, va=va if va == "center" else "top", fontsize=fs, fontweight="bold" if bold else "normal", color=color, linespacing=1.35)


def arrow(ax, p, q, ls="-", color=INK, lw=1.4, rad=0.0, style="-|>", ms=11):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=ms, lw=lw, color=color, ls=ls, connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


PAPER_FIGS = {"fig_regimes.png", "fig_rank_activity.png", "fig_rank_entity.png"}   # also written as vector PDF for the journal manuscript


def save(fig, name):
    fig.savefig(OUT / name, dpi=200)
    if name in PAPER_FIGS:
        fig.savefig(OUT / name.replace(".png", ".pdf"))
    plt.close(fig)
    print("wrote", name)


# ------------------------------------------------------------------ system diagrams
def architecture():
    fig, ax = canvas()
    box(ax, 1, 10, 17, 38, "Seven real\npublic logs\n\nCROP (Gerrit)\nOULAD\nAngular commits\nGerman Bundestag\nEnron e-mail\nEthereum DApps\nAge of Empires\n\nall CC BY 4.0", fs=9.5, bold=False)
    box(ax, 22, 34, 19, 14, "Acquire and verify\nfetch_sources.py\nchecksums, resume", fs=9.5)
    box(ax, 22, 14, 19, 14, "Extract safely\nextract_archives.py\nrejects unsafe paths", fs=9.5)
    box(ax, 45, 14, 19, 14, "Convert and load\nconvert_crop / _oulad\nocel_io (OCEL 2.x)", fs=9.5)
    box(ax, 45, 34, 19, 12, "OCEL 2.0 tables\nevents, objects,\nE2O and O2O links", fs=9.5, fc=FILL_B)
    box(ax, 45, 50, 19, 7, "Future: capstone portal\nadapter (AuditLog to OCEL)", fs=8.5, dashed=True, ec=GRAY, color=MUTED)
    box(ax, 68, 40, 20, 8, "Distortion metrics\ndistortion.py", fs=9.5, fc=FILL_O, ec=ORANGE)
    box(ax, 68, 29, 20, 8, "Consequence analysis\nconsequence.py", fs=9.5, fc=FILL_O, ec=ORANGE)
    box(ax, 68, 18, 20, 8, "COOC rules (appendix)\ncooc.py, registry.py", fs=9.0, fc=FILL_O, ec=ORANGE)
    box(ax, 68, 3, 20, 11, "Validation\nSQL cross-check\nbrute-force self-check\nindependent recomputation", fs=8.8, fc=FILL_A, ec=AQUA)
    box(ax, 90.5, 18, 8.5, 30, "results/\n\nCSV\nJSON\nMD\n\nreport\nand paper", fs=8.6, fc=FILL)
    arrow(ax, (18, 41), (22, 41)); arrow(ax, (31.5, 34), (31.5, 28)); arrow(ax, (41, 21), (45, 21)); arrow(ax, (54.5, 28), (54.5, 34))
    arrow(ax, (54.5, 50), (54.5, 46), ls="--", color=GRAY)
    for yy in (44, 33, 22):
        arrow(ax, (64, 40), (68, yy))
    arrow(ax, (78, 18), (78, 14))
    for yy in (44, 33, 22):
        arrow(ax, (88, yy), (90.5, yy))
    arrow(ax, (88, 8.5), (94.7, 8.5), color=AQUA); arrow(ax, (94.7, 8.5), (94.7, 18), color=AQUA)
    save(fig, "fig_architecture.png")


def _process(ax, cx, cy, r, num, text, fs=8.6):
    ax.add_patch(Circle((cx, cy), r, fc=FILL_B, ec=BLUE, lw=1.5))
    ax.text(cx, cy + r * 0.45, num, ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(cx, cy - r * 0.18, text, ha="center", va="center", fontsize=fs, linespacing=1.25)


def _store(ax, x, y, w, h, label, fs=9):
    ax.add_patch(Rectangle((x, y), w, h, fc=FILL, ec="none"))
    ax.plot([x, x + w], [y + h, y + h], color=INK, lw=1.5); ax.plot([x, x + w], [y, y], color=INK, lw=1.5); ax.plot([x, x], [y, y + h], color=INK, lw=1.5)
    ax.text(x + w / 2 + 0.5, y + h / 2, label, ha="center", va="center", fontsize=fs, linespacing=1.3)


def dfd0():
    fig, ax = canvas(size=(10, 4.6), h=46)
    box(ax, 2, 28, 22, 12, "Public data publishers\n(Zenodo, UCI)", fc=FILL, ec=INK, fs=10, r=0.2)
    box(ax, 2, 4, 22, 16, "Researcher\nand guide", fc=FILL, ec=INK, fs=10, r=0.2)
    ax.add_patch(Circle((70, 23), 15, fc=FILL_B, ec=BLUE, lw=1.8))
    ax.text(70, 31, "0", ha="center", fontsize=10, fontweight="bold")
    ax.text(70, 22.5, "Flattening analysis\nsystem\n(OCEL, distortion,\nconsequence)", ha="center", va="center", fontsize=10, linespacing=1.3)
    arrow(ax, (24, 36), (57.2, 30.5)); ax.text(39, 36.6, "dataset archives, licences", fontsize=9, ha="center")
    arrow(ax, (24, 16), (55.4, 19.5)); ax.text(38, 19.6, "run commands, settings", fontsize=9, ha="center")
    arrow(ax, (61, 11), (24, 8)); ax.text(42, 4.2, "tables, figures, validation status", fontsize=9, ha="center")
    save(fig, "fig_dfd0.png")


def dfd1():
    fig, ax = canvas(h=58, size=(10, 5.8))
    box(ax, 1, 40, 14, 10, "Public data\npublishers", fc=FILL, ec=INK, fs=9, r=0.2)
    _process(ax, 27, 45, 7.3, "1.0", "Acquire\nand verify")
    _store(ax, 38, 40, 13, 10, "D1  Verified\nraw archives", 8.5)
    _process(ax, 65, 45, 7.3, "2.0", "Extract and\nconvert to OCEL")
    _store(ax, 78, 40, 20, 10, "D2  OCEL logs\n(events, objects, relations)", 8.2)
    _process(ax, 72, 22, 7.3, "3.0", "Distortion\nmetrics")
    _process(ax, 90, 22, 7.3, "4.0", "Consequence\nanalysis")
    _store(ax, 60, 3, 38, 9, "D3  Metric tables and JSON results", 9)
    _process(ax, 44, 9, 6.8, "5.0", "Validate")
    _process(ax, 24, 9, 6.8, "6.0", "Summarise")
    box(ax, 1, 3.5, 12, 11, "Researcher\nand guide", fc=FILL, ec=INK, fs=9, r=0.2)
    arrow(ax, (15, 45), (19.7, 45)); arrow(ax, (34.3, 45), (38, 45)); arrow(ax, (51, 45), (57.7, 45)); arrow(ax, (72.3, 45), (78, 45))
    arrow(ax, (82, 40), (75, 28.8)); arrow(ax, (92, 40), (91, 29.5))
    arrow(ax, (72, 14.7), (72, 12)); arrow(ax, (90, 14.7), (90, 12))
    arrow(ax, (60, 7.5), (50.8, 9)); arrow(ax, (37.2, 9), (30.8, 9)); arrow(ax, (17.2, 9), (13, 9))
    arrow(ax, (7, 14.5), (21, 40.5), ls="--", color=GRAY)
    ax.text(10.6, 27, "run request", fontsize=8.2, color=MUTED, rotation=58)
    save(fig, "fig_dfd1.png")


def stick(ax, x, y, label):
    ax.add_patch(Circle((x, y + 8), 2.2, fc=SURFACE, ec=INK, lw=1.5))
    ax.plot([x, x], [y + 5.8, y + 0.8], color=INK, lw=1.5); ax.plot([x - 3.5, x + 3.5], [y + 4.4, y + 4.4], color=INK, lw=1.5)
    ax.plot([x, x - 3], [y + 0.8, y - 3], color=INK, lw=1.5); ax.plot([x, x + 3], [y + 0.8, y - 3], color=INK, lw=1.5)
    ax.text(x, y - 5.6, label, ha="center", va="center", fontsize=9.5, linespacing=1.2)


def usecase():
    fig, ax = canvas(h=60, size=(10, 6))
    ax.add_patch(Rectangle((21, 2), 58, 56, fc="none", ec=MUTED, lw=1.4, ls="--"))
    ax.text(50, 56, "Flattening analysis system", ha="center", fontsize=10, fontweight="bold")
    cases = ["Download and verify datasets", "Convert a source to OCEL 2.0", "Compute distortion metrics", "Run consequence analysis",
             "Validate against independent code", "Export summary tables", "Review results and approve"]
    ys = [49, 42, 35, 28, 21, 14, 7]
    for t, yy in zip(cases, ys):
        ax.add_patch(Ellipse((50, yy), 40, 5.6, fc=FILL_B, ec=BLUE, lw=1.4)); ax.text(50, yy, t, ha="center", va="center", fontsize=9.3)
    stick(ax, 9, 27, "Researcher\n(team)"); stick(ax, 91, 14, "Guide /\npanel")
    for yy in ys[:6]:
        arrow(ax, (13, 33), (30.2, yy), style="-", lw=1.1, color=MUTED)
    arrow(ax, (87.5, 19), (69.8, 7.4), style="-", lw=1.1, color=MUTED); arrow(ax, (87.5, 19), (69.8, 14.2), style="-", lw=1.1, color=MUTED)
    save(fig, "fig_usecase.png")


def classdiagram():
    fig, ax = canvas(h=60, size=(10, 6))
    def cls(x, top, w, name, attrs, ops, ec=BLUE, fc=FILL):
        row = 2.6
        h = 4.6 + (row * len(attrs) + 1.0 if attrs else 1.2) + row * len(ops) + 1.2
        y = top - h
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.5))
        ax.text(x + w / 2, top - 2.3, name, ha="center", va="center", fontsize=10, fontweight="bold")
        ax.plot([x, x + w], [top - 4.6, top - 4.6], color=ec, lw=1.2)
        for i, t in enumerate(attrs):
            ax.text(x + 1, top - 4.6 - 1.7 - row * i, t, fontsize=8.2, va="center")
        sep = top - 4.6 - ((row * len(attrs) + 1.0) if attrs else 1.2)
        ax.plot([x, x + w], [sep, sep], color=ec, lw=1.2)
        for i, t in enumerate(ops):
            ax.text(x + 1, sep - 1.7 - row * i, t, fontsize=8.2, va="center")
        return y, h
    cls(2, 58, 28, "OcelLoader", [], ["load_ocel(path, options)", "load_ocel_bundle(dir)", "split_roles(ocel, types)", "pseudonymise(ids)"], fc=FILL_A, ec=AQUA)
    cls(36, 58, 28, "Ocel", ["name: str", "events: DataFrame", "objects: DataFrame", "relations: DataFrame", "o2o: DataFrame"], ["object_types(): list"])
    cls(70, 58, 28, "Prepared", ["act_of: ndarray", "rel: DataFrame", "types: list"], ["rows(t)", "pairs(t): (e1, e2)", "sequences(t): Series"], fc=FILL_O, ec=ORANGE)
    cls(2, 28, 28, "View", ["kind: native|flat|dflat", "ev: DataFrame", "rel: DataFrame", "types, attrs: set"], ["events_of(scope)"])
    cls(36, 28, 28, "Predicate", ["pid, family, template", "scope: str", "params: dict", "req_types, req_attrs: set"], ["expressible(view)", "evaluate(view): set"])
    cls(70, 28, 28, "Registry", [], ["build(key, ocel): list", "LEADING: dict"], fc=FILL_A, ec=AQUA)
    arrow(ax, (30, 50), (36, 50), lw=1.3); ax.text(33, 51.4, "creates", fontsize=8.2, ha="center", color=MUTED)
    arrow(ax, (70, 50), (64, 50), lw=1.3); ax.text(67, 51.4, "wraps", fontsize=8.2, ha="center", color=MUTED)
    arrow(ax, (42, 35.6), (18, 28.2), lw=1.3); ax.text(26, 33.6, "built from", fontsize=8.2, color=MUTED, rotation=17)
    arrow(ax, (36, 17), (30, 17), lw=1.3); ax.text(33, 18.4, "runs on", fontsize=8.2, ha="center", color=MUTED)
    arrow(ax, (70, 17), (64, 17), lw=1.3); ax.text(67, 18.4, "creates", fontsize=8.2, ha="center", color=MUTED)
    save(fig, "fig_class.png")


def sequence():
    fig, ax = canvas(h=62, size=(10, 6.4))
    names = ["Researcher", "fetch_sources", "convert", "ocel_io", "distortion", "consequence", "check", "results"]
    xs = [6 + i * 12.6 for i in range(len(names))]
    for n, x in zip(names, xs):
        box(ax, x - 5.4, 55, 10.8, 5, n, fs=8.8, fc=FILL_B)
        ax.plot([x, x], [55, 2], color=GRAY, lw=1, ls=(0, (4, 3)))
    msgs = [(0, 1, 51, "1 run (manifest)"), (1, 1, 47, "2 download, verify MD5 + size, write SHA-256"), (0, 2, 42, "3 extract, convert CROP / OULAD"),
            (2, 3, 38, "4 write OCEL 2.0 SQLite"), (0, 4, 33.5, "5 analyse(log)"), (4, 3, 30, "6 load_ocel(path, options)"),
            (3, 4, 26.5, "7 Ocel tables"), (4, 7, 23, "8 write distortion JSON"), (0, 5, 18.5, "9 analyse(log)"),
            (5, 7, 15, "10 write consequence JSON"), (0, 6, 10.5, "11 brute-force self-check"), (6, 0, 7, "12 passed"), (0, 7, 3.6, "13 summarise tables")]
    for a, b, y, t in msgs:
        if a == b:
            ax.add_patch(FancyArrowPatch((xs[a], y + 1.6), (xs[a], y - 1.0), connectionstyle="arc3,rad=-1.6", arrowstyle="-|>", mutation_scale=9, lw=1.2, color=INK))
            ax.text(xs[a] + 2.5, y + 0.3, t, fontsize=8.1, va="center", bbox=dict(fc="white", ec="none", pad=1.2))
            continue
        arrow(ax, (xs[a], y), (xs[b], y), ms=9, lw=1.2, ls="--" if b < a else "-")
        mid = (xs[a] + xs[b]) / 2
        ax.text(mid, y + 1.2, t, fontsize=8.1, ha="center", va="bottom", bbox=dict(fc="white", ec="none", pad=1.2))
    save(fig, "fig_sequence.png")


def capstone_schema():
    fig, ax = canvas(h=56, size=(10, 5.6))
    objs = {"Student": (6, 40), "Team": (30, 40), "Project": (54, 40), "Faculty\n(guide)": (78, 40), "Report": (54, 20), "ReportVersion": (30, 20), "Score\n(write-once)": (30, 3.5), "Review\nstage": (78, 20)}
    for t, (x, y) in objs.items():
        box(ax, x, y, 16, 9, t, fs=9.5, fc=FILL_B, bold=True)
    def link(p, q, label, lx=None, ly=None):
        arrow(ax, p, q, lw=1.3, style="-|>", ms=9)
        ax.text((p[0] + q[0]) / 2 if lx is None else lx, (p[1] + q[1]) / 2 + 1.1 if ly is None else ly, label, fontsize=8.3, ha="center", color=MUTED)
    link((22, 44.5), (30, 44.5), "member-of"); link((46, 44.5), (54, 44.5), "executes"); link((78, 44.5), (70, 44.5), "guides")
    link((62, 40), (62, 29), "has-report", lx=67); link((54, 24.5), (46, 24.5), "has-version"); link((38, 20), (38, 12.5), "has-score", lx=43); link((78, 24.5), (70, 24.5), "at-stage")
    link((86, 40), (86, 29), "reviews", lx=90.8)
    box(ax, 50, 1, 46, 12, "Events (documented AuditLog actions)\nPROJECT_CREATED, COMPILATION_STARTED / SUCCESS / FAILED,\nSTUDENT_SUBMITTED, FACULTY_STARTED_VERIFICATION,\nFACULTY_ACCEPTED, FACULTY_REJECTED", fs=7.9, fc=FILL, ec=GRAY, color=INK)
    save(fig, "fig_capstone_schema.png")


def timeline():
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    phases = [("Literature review and scope", 0.0, 1.6, BLUE), ("Platform study and OCEL schema", 0.8, 2.4, BLUE), ("Review 2 prototype (since removed)", 2.0, 3.1, GRAY),
              ("Re-scope to real data only", 3.3, 3.9, ORANGE), ("Download, convert, profile 7 logs", 3.5, 4.6, ORANGE), ("Distortion and consequence analysis", 3.9, 4.8, ORANGE),
              ("Verification, report and deck", 4.5, 5.0, AQUA), ("Journal manuscript (planned)", 5.0, 7.0, GRAY)]
    for i, (t, a, b, c) in enumerate(phases):
        y = len(phases) - i
        ax.barh(y, b - a, left=a, height=0.52, color=c, alpha=0.9 if "planned" not in t and "removed" not in t else 0.45, ec="none")
        ax.text(b + 0.08 if b < 6 else a - 0.08, y, t, va="center", ha="left" if b < 6 else "right", fontsize=9.6)
    ax.set_xticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5]); ax.set_xticklabels(["Aug", "early Sep", "late Sep", "early Oct", "late Oct", "Nov", "Dec"], fontsize=9.5)
    ax.set_yticks([]); ax.set_xlim(0, 7.2); ax.set_ylim(0.2, len(phases) + 0.9)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=1); ax.set_axisbelow(True)
    ax.set_xlabel("Approximate calendar, 2026 (grey = not part of delivered work)", fontsize=9.5, color=MUTED)
    fig.tight_layout()
    save(fig, "fig_timeline.png")


# ------------------------------------------------------------------ result charts
def rows(name):
    with (RES / name).open(encoding="utf-8") as h:
        return {r["log"]: r for r in csv.DictReader(h)}


LABEL = {"angular_commits": "Angular", "aoe2": "Age of Empires", "bundestag": "Bundestag", "crop": "CROP (Gerrit)", "enron": "Enron", "ethereum": "Ethereum", "oulad": "OULAD"}


def style_axes(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.grid(color=GRID, lw=1); ax.set_axisbelow(True)


def regimes():
    L = rows("log_level_summary.csv")
    reg = {"crop": "star", "oulad": "star", "bundestag": "partitioned", "aoe2": "partitioned", "ethereum": "partitioned", "angular_commits": "fan-out", "enron": "fan-out"}
    col = {"star": BLUE, "partitioned": ORANGE, "fan-out": AQUA}
    fig, ax = plt.subplots(figsize=(7.8, 4.7))
    style_axes(ax)
    for k, r in L.items():
        ax.scatter([float(r["max_copies_per_event"])], [100 * float(r["median_deficiency"])], s=150, color=col[reg[k]], zorder=3, ec=SURFACE, lw=1.5)
    spot = {"crop": (1.08, 3.0, "left", "CROP and OULAD"), "oulad": None, "bundestag": (1.22, 96.0, "left", None), "aoe2": (1.9, 86.3, "left", None),
            "ethereum": (1.18, 68.9, "left", None), "angular_commits": (70, 7.5, "right", None), "enron": (2.35, 23.0, "left", None)}
    for k, r in L.items():
        s = spot[k]
        if s is None:
            continue
        x, y = float(r["max_copies_per_event"]), 100 * float(r["median_deficiency"])
        name = s[3] or LABEL[k]
        ax.text(s[0], s[1], f"{name}  {x:.2f}x", fontsize=10, ha=s[2], va="center")
    ax.set_xscale("log"); ax.set_xlim(0.8, 160); ax.set_ylim(-8, 104)
    ax.set_xticks([1, 2, 5, 10, 20, 50, 100]); ax.set_xticklabels(["1x", "2x", "5x", "10x", "20x", "50x", "100x"], fontsize=10)
    ax.set_xlabel("Largest event duplication when flattening (copies per event, log scale)", fontsize=10.5)
    ax.set_ylabel("Events one case notion drops (median, %)", fontsize=10.5)
    ax.text(3.2, 76, "partitioned logs", color=ORANGE, fontsize=11, fontweight="bold")
    ax.text(7, 14, "fan-out logs", color=AQUA, fontsize=11, fontweight="bold")
    ax.text(1.08, 12, "star logs", color=BLUE, fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, "fig_regimes.png")


def dumbbell(name, a_key, b_key, a_label, b_label, title_x, xlim, logs=None):
    C = rows("consequence_by_log.csv")
    items = [(k, float(r[a_key]), float(r[b_key])) for k, r in C.items() if r[a_key] not in ("", "None") and r[b_key] not in ("", "None")]
    items.sort(key=lambda t: t[2])
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    style_axes(ax); ax.grid(axis="y", visible=False)
    for i, (k, a, b) in enumerate(items):
        ax.plot([a, b], [i, i], color=GRAY, lw=2.2, zorder=1)
        ax.scatter([a], [i], s=95, color=BLUE, zorder=3, ec=SURFACE, lw=1.4); ax.scatter([b], [i], s=95, color=ORANGE, zorder=3, ec=SURFACE, lw=1.4)
        ax.text(b - 0.03 if b <= a else b - 0.03, i + 0.33, f"{b:.2f}", fontsize=8.8, color=ORANGE, ha="center")
        ax.text(a + 0.03 if a >= b else a + 0.03, i - 0.42, f"{a:.2f}", fontsize=8.8, color=BLUE, ha="center")
    ax.set_yticks(range(len(items))); ax.set_yticklabels([LABEL[k] for k, _, _ in items], fontsize=10.5)
    ax.set_xlim(*xlim); ax.set_ylim(-0.8, len(items) - 0.2); ax.set_xlabel(title_x, fontsize=10.5)
    ax.scatter([], [], s=95, color=BLUE, label=a_label); ax.scatter([], [], s=95, color=ORANGE, label=b_label)
    ax.legend(loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=2, frameon=False, fontsize=9.6)
    fig.tight_layout()
    save(fig, name)


def bars(name, series, xlabel, fmt="{:.1f}%", color=BLUE, xmax=None, figsize=(7.2, 3.9)):
    series = sorted(series, key=lambda t: t[1])
    fig, ax = plt.subplots(figsize=figsize)
    style_axes(ax); ax.grid(axis="y", visible=False)
    ax.barh([LABEL[k] for k, _ in series], [v for _, v in series], color=color, height=0.55)
    for i, (_, v) in enumerate(series):
        ax.text(v + (xmax or max(v for _, v in series)) * 0.012, i, fmt.format(v), va="center", fontsize=10)
    ax.set_xlabel(xlabel, fontsize=10.5); ax.tick_params(axis="y", labelsize=10.5)
    if xmax: ax.set_xlim(0, xmax)
    fig.tight_layout()
    save(fig, name)


def main():
    architecture(); dfd0(); dfd1(); usecase(); classdiagram(); sequence(); capstone_schema(); timeline()
    regimes()
    dumbbell("fig_rank_activity.png", "activity_rank_rho_dup_only_min", "activity_rank_rho_all_median", "duplication alone (worst case notion)", "versus the whole process (median case notion)",
             "Spearman rank correlation of the activity-frequency ranking", (-0.15, 1.12))
    dumbbell("fig_rank_entity.png", "entity_rho_visible_median", "entity_rho_visible_min", "median over entity types", "worst entity type", "Spearman rank correlation of entity rankings from a denormalised export", (-0.5, 1.15))
    C = rows("consequence_by_log.csv"); Lg = rows("log_level_summary.csv")
    bars("fig_spurious.png", [(k, 100 * float(C[k]["df_spurious_edge_mass_max"])) for k in ("crop", "oulad", "aoe2", "ethereum", "bundestag")],
         "Adjacent event pairs whose edge type never occurs\ninside a nested child (worst case notion, %)", xmax=33)
    bars("fig_coupling.png", [(k, 100 * int(r["pairs_with_ge50pct_shared_objects"]) / int(r["type_pairs"])) for k, r in Lg.items()],
         "Object-type pairs sharing more than half of their objects across cases (%)", xmax=112, fmt="{:.0f}%")


if __name__ == "__main__":
    main()
