"""Figures from the public data of this repository.

    pixi run figures      (or: python3 -I figures/make_figures.py)

Writes PDF and SVG versions of each figure, and numbers.json with the values
they show, to _build/figures/.
"""

import datetime as dt
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import ConnectionPatch, Patch

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "review" / "data"
OUT = REPO / "_build" / "figures"

# Sized to be included at their natural size in a 12 pt, 6.5 in wide single-column
# document typeset in Computer Modern; STIX supplies glyphs cmr10 lacks (dashes).
plt.rcParams.update({
    "font.family": ["cmr10", "STIXGeneral"], "mathtext.fontset": "cm", "axes.formatter.use_mathtext": True,
    "font.size": 12, "axes.labelsize": 12, "xtick.labelsize": 12, "ytick.labelsize": 12,
    "legend.fontsize": 12, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "lines.linewidth": 1.2, "pdf.fonttype": 42,
    "svg.fonttype": "path", "legend.frameon": False,
})
# Petroff's ten-colour cycle (matplotlib style "petroff10"), chosen for colour-blind legibility.
P = plt.style.library["petroff10"]["axes.prop_cycle"].by_key()["color"]
BLUE, ORANGE, RED, GREY, PURPLE = P[0], P[1], P[2], P[3], P[4]
INK, MID, LIGHT = "#1a1a1a", "#6b6b6b", "#d9dcdc"
WIDTH, WIDE = 5.6, 6.5  # inches
WINDOW = (dt.date(2026, 4, 18), dt.date(2026, 10, 18))
BOLD = {"fontfamily": "cmb10"}


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"{name}.{ext}")
    plt.close(fig)


def d(s):
    return dt.date.fromisoformat(s[:10])


def momentum(numbers, ax):
    hist = json.loads((REPO / "corpus" / "history" / "half-year-counts.json").read_text())
    edges, rates, mids = [], [], []
    for p in hist["periods"]:
        a, b = d(p["start"]), d(p["end"])
        edges.append(a)
        rates.append(p["candidates"] / p["days"] * 30.44)
        mids.append(a + (b - a) / 2)
    edges.append(d(hist["periods"][-1]["end"]))
    # Exponential fit to the half-year rates.
    t = np.array([m.toordinal() for m in mids], float)
    slope, icpt = np.polyfit(t, np.log(rates), 1)
    doubling = math.log(2) / slope / 30.44
    # The papers studied: arXiv records in the window with a substantive or proposed role of a language model.
    cls = json.loads((REPO / "classification" / "classified.json").read_text())
    sub = [r for r in cls if r["llm_role"] in ("substantive", "proposed")]
    days = (WINDOW[1] - WINDOW[0]).days + 1
    per_month = len(sub) / days * 30.44
    numbers["momentum"] = {"half_year_per_month": [[x.isoformat(), round(y, 1)] for x, y in zip(mids, rates)],
                           "doubling_months": round(doubling, 1),
                           "papers": len(sub), "papers_per_day": round(len(sub) / days, 2),
                           "papers_per_month": round(per_month, 1)}

    ax.axvspan(*WINDOW, color=LIGHT, lw=0, label="window studied")
    ax.plot(mids, rates, "o", color=PURPLE, ms=5, label="keyword matches")
    fit_x = [edges[0], edges[-1]]
    ax.plot(fit_x, [math.exp(icpt + slope * x.toordinal()) for x in fit_x], ls=(0, (4, 3)), color=MID, lw=0.8,
            label=rf"$\propto 2^{{t/T}}$, $T = {doubling:.0f}$ months")
    ax.plot(list(WINDOW), [per_month] * 2, color=RED, lw=3, solid_capstyle="butt",
            label=rf"studied: ${len(sub) / days:.1f}\,\mathrm{{day}}^{{-1}}$")
    ax.legend(loc="upper left", bbox_to_anchor=(0.02, 1.08), ncol=2, handlelength=1.6, labelspacing=0.3,
              columnspacing=1.0, handletextpad=0.5)
    ax.set_yscale("log")
    ax.set_ylabel(r"$\mathrm{d}N/\mathrm{d}t$ (month$^{-1}$)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(edges[0] - dt.timedelta(days=20), edges[-1] + dt.timedelta(days=20))
    ax.set_ylim(0.5, 6000)
    ax.set_yticks([1, 10, 100, 1000])


def lag(numbers, ax):
    m = json.loads((DATA / "model_lag.json").read_text())
    median_lag = json.loads((DATA / "aggregates.json").read_text())["model_lag"]["lag_days_any_role"]["median"]
    papers = [p for p in m["papers"] if p.get("lag_days") is not None and p["lag_days"] >= 0]
    month = 30.44  # days
    cap = 6  # months, the length of the window; older models are drawn as triangles above it
    for cls, colour, label in (("frontier-api", BLUE, "proprietary"), ("open-weights", ORANGE, "open weights")):
        sel = [p for p in papers if (p["newest_class"] == "open-weights") == (cls == "open-weights")]
        inside = [p for p in sel if p["lag_days"] / month <= cap]
        above = [p for p in sel if p["lag_days"] / month > cap]
        ax.scatter([d(p["date"]) for p in inside], [p["lag_days"] / month for p in inside], s=18,
                   color=colour, alpha=0.85, lw=0, label=label, zorder=3)
        ax.scatter([d(p["date"]) for p in above], [cap + 0.25] * len(above), s=30,
                   marker="^", color=colour, alpha=0.85, lw=0, zorder=3)
    us = sorted((d(f["date"]), f["model"]) for f in m["frontier"]
                if f["vendor"] in ("OpenAI", "Anthropic", "Google DeepMind", "xAI"))
    days = [WINDOW[0] + dt.timedelta(days=i) for i in range((WINDOW[1] - WINDOW[0]).days + 1)]
    newest = [(t - max(x for x, _ in us if x <= t)).days / month for t in days]
    ax.plot(days, newest, color=INK, lw=1.0, zorder=2, label="newest flagship")
    ax.axhline(median_lag / month, ls=(0, (1, 2)), color=MID, lw=1.2, zorder=1)
    box = {"boxstyle": "square,pad=0.1", "fc": "white", "ec": "none", "alpha": 0.85}
    ax.text(WINDOW[1] - dt.timedelta(days=2), median_lag / month + 0.08, "median", ha="right", va="bottom",
            color=MID, bbox=box, zorder=4)
    ax.scatter([], [], s=30, marker="^", color=MID, lw=0, label=rf"$\Delta t > {cap}$ months")
    ax.set_xlim(*WINDOW)
    ax.set_ylim(0, cap + 0.5)
    ax.set_yticks(range(cap + 1))
    ax.set_xlabel("paper submitted (2026)")
    ax.set_ylabel(r"$\Delta t$ (months)")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(k) for k in ("proprietary", "open weights", rf"$\Delta t > {cap}$ months", "newest flagship")]
    ax.legend([handles[i] for i in order], [labels[i] for i in order], loc="upper center",
              bbox_to_anchor=(0.43, -0.2), ncol=4, handlelength=1.2, handletextpad=0.4, columnspacing=1.0)
    flag = [x for x, n in us if WINDOW[0] <= x <= WINDOW[1] and "Pro" not in n and "ultra" not in n]
    numbers["lag"] = {**{k: m["summary"][k] for k in ("lag_days_any_role", "flagship_releases_since",
                                                       "share_lag_over_180d", "share_lag_over_365d",
                                                       "share_using_current_frontier")},
                      "us_flagships_in_window": len(flag),
                      "days_per_flagship": round(((WINDOW[1] - WINDOW[0]).days + 1) / len(flag), 1)}


def pace(numbers):
    fig = plt.figure(figsize=(WIDE, 4.6))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.9, 2.6], left=0.15, right=0.97, top=0.99, bottom=0.18, hspace=0.42)
    a1, a2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    momentum(numbers, a1)
    lag(numbers, a2)
    # Panel (b) magnifies the shaded window of panel (a).
    for x, corner in ((WINDOW[0], 0), (WINDOW[1], 1)):
        fig.add_artist(ConnectionPatch((mdates.date2num(x), 0), (corner, 1), coordsA=a1.get_xaxis_transform(),
                                       coordsB=a2.transAxes, color=MID, lw=0.7, zorder=0))
    for a, lab in ((a1, "(a)"), (a2, "(b)")):
        a.text(-0.15, 1.0, lab, transform=a.transAxes, va="top")
    fig.align_ylabels([a1, a2])
    save(fig, "fig-pace")


SHORT = {
    "missing-artifacts": "materials for reproduction not accessible",
    "underspecified-methods": "essential methods underspecified",
    "inconsistent-reporting": "numbers inconsistent within the paper",
    "confounded-attribution": "agent's contribution not isolated",
    "unsupported-scope": "generalised beyond what was tested",
    "unvalidated-scientific-results": "scientific outputs not validated",
    "inadequate-comparisons": "missing or unequal baselines",
    "unquantified-uncertainty": "no uncertainty where it matters",
    "invalid-success-measure": "success metric misses the claim",
    "unvalidated-judging": "judge or reference not validated",
    "test-contamination": "test contamination or tuning on test",
    "technical-error": "physics, maths or statistics error",
}
GROUPS = [("reproducibility-and-reporting", "Reproducibility and reporting"),
          ("claims-and-inference", "Claims and inference"),
          ("evaluation-design", "Evaluation design"),
          ("correctness-and-assurance", "Correctness")]


def issues(numbers):
    s = json.loads((DATA / "aggregates.json").read_text())["issue_taxonomy"]
    cats = {c["id"]: c for c in s["categories"] if c["id"] in SHORT}
    rows = []
    for g, title in GROUPS:
        members = sorted((c for c in cats.values() if c["supergroup"] == g), key=lambda c: -c["paper_share"])
        rows.append(("group", title))
        rows += [("cat", c) for c in members]
    fig, ax = plt.subplots(figsize=(WIDE, 4.2))
    y, ticks, labels = 0, [], []
    for kind, item in rows:
        if kind == "group":
            ax.text(-0.01, y, item, transform=ax.get_yaxis_transform(), ha="right", va="center", **BOLD)
        else:
            early, late = 100 * item["paper_share_apr_jun"], 100 * item["paper_share_jul_oct"]
            ax.barh(y, 100 * item["paper_share"], height=0.7, color=LIGHT, lw=0)
            ax.plot([early, late], [y, y], color=MID, lw=0.8)
            ax.plot(early, y, "o", color=ORANGE, ms=5.5)
            ax.plot(late, y, "o", color=BLUE, ms=5.5)
            ticks.append(y)
            labels.append(SHORT[item["id"]])
        y -= 1
    ax.set_yticks(ticks, labels)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("papers with such a major issue (%)")
    ax.set_xlim(0, 60)
    ax.legend(handles=[Patch(color=LIGHT, label="all 228 papers"),
                       ax.plot([], [], "o", color=ORANGE, ms=5.5, label="April–June")[0],
                       ax.plot([], [], "o", color=BLUE, ms=5.5, label="July–October")[0]],
              loc="lower right")
    fig.tight_layout(pad=0.3)
    save(fig, "fig-issues")
    numbers["issues"] = {SHORT[c["id"]]: round(100 * c["paper_share"]) for c in cats.values()}


def trend(numbers):
    by = json.loads((DATA / "aggregates.json").read_text())["by_month"]
    months = sorted(by)
    xs = [dt.date.fromisoformat(m + "-15") for m in months]
    xs[0] = WINDOW[0] + (dt.date(2026, 4, 30) - WINDOW[0]) / 2  # the window starts on 18 April
    fig, a1 = plt.subplots(figsize=(WIDTH, 2.5))
    a2 = a1.twinx()
    mean = [by[m]["claims_mean"] for m in months]
    se = [by[m]["claims_se"] for m in months]
    share = [100 * by[m]["ai_use_share"] for m in months]
    sse = [100 * by[m]["ai_use_se"] for m in months]
    # The two series are offset by two days so that their error bars do not overlap.
    shift = dt.timedelta(days=2)
    a1.errorbar([x - shift for x in xs], mean, yerr=se, fmt="o-", color=BLUE, ms=5, capsize=0, lw=1.2,
                elinewidth=1.0, zorder=3)
    a2.errorbar([x + shift for x in xs], share, yerr=sse, fmt="s--", color=ORANGE, ms=4.5, capsize=0, lw=1.2,
                elinewidth=1.0)
    a1.set_zorder(a2.get_zorder() + 1)
    a1.patch.set_visible(False)
    a2.spines["right"].set_visible(True)
    for ax, colour, label, lim in ((a1, BLUE, "claims match\nevidence (1–5)", (2.3, 3.8)),
                                   (a2, ORANGE, "AI-use\nstatement (%)", (0, 70))):
        ax.set_ylabel(label, color=colour)
        ax.tick_params(axis="y", colors=colour)
        ax.set_ylim(*lim)
    a2.spines["right"].set_color(ORANGE)
    a1.spines["left"].set_color(BLUE)
    a1.xaxis.set_major_locator(mdates.MonthLocator())
    a1.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    a1.set_xlabel("paper submitted (2026)")
    fig.tight_layout(pad=0.3)
    save(fig, "fig-trend")
    numbers["trend"] = {m: {"n": by[m]["n"], "claims_mean": round(a, 2), "ai_use_pct": round(b)}
                        for m, a, b in zip(months, mean, share)}


QUESTION_NAMES = {
    "method-capability": "can a method or agent do this task?", "model-evaluation": "how well do models perform?",
    "workflow-automation": "automating an existing workflow", "ai-workflow-perspective": "review or perspective on AI",
    "research-infrastructure": "a tool or data resource", "physical-findings": "a new physical or mathematical finding",
    "targeted-design": "targeted design", "literature-findings": "knowledge from published evidence",
}


FIELD_NAMES = {
    "quantum-software": "algorithms, circuits, software", "quantum-information": "information theory, codes",
    "quantum-hardware": "devices and control", "structural-materials": "metals, alloys, structural",
    "molecular-soft": "polymers, soft matter", "porous-hosts": "porous frameworks",
    "energy-reactive": "batteries and catalysts", "electronic-functional": "electronic, optical, functional",
    "quantum-matter": "magnetism, correlated matter", "atomistic-simulation": "DFT, atomistic simulation",
    "diffraction-spectroscopy": "diffraction, spectroscopy", "microscopy": "microscopy",
    "synthesis-labs": "synthesis, lab automation", "materials-informatics": "materials informatics",
    "cross-materials": "broad reviews, benchmarks", "other-fields": "chemistry, biology, other physics",
}
FIELD_GROUPS = {"quantum": "quantum", "materials": "material class", "methods": "technique", "other": "other fields"}


def subjects(numbers):
    base = REPO / "classification" / "subjects"
    s = json.loads((base / "summary.json").read_text())
    qcb = {c["id"]: c["supergroup"] for c in json.loads((base / "codebook-question.json").read_text())["categories"]}
    fgroup = {c["id"]: c["supergroup"] for c in json.loads((base / "codebook-field.json").read_text())["categories"]}
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(WIDE, 5.6), gridspec_kw={"height_ratios": [20.6, 8.2]})

    def axis(ax, ys, labels, top):
        ax.set_yticks(ys, labels)
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ax.set_ylim(0.4, top + 0.6)

    # (a) field, grouped by super-group; each bar split by whether the question is about the physical world.
    ys, labels, y = [], [], 0
    for g in reversed(list(FIELD_GROUPS)):
        items = [(k, v) for k, v in s["field_shares"].items() if fgroup[k] == g][::-1]
        for k, v in items:
            y += 1
            split = s["field_by_question_supergroup"][k]
            a1.barh(y, 100 * split["physical-world"], height=0.8, color=ORANGE, lw=0)
            a1.barh(y, 100 * split["ai-workflow"], left=100 * split["physical-world"], height=0.8, color=LIGHT, lw=0)
            a1.plot([100 * v["lo"], 100 * v["hi"]], [y, y], color=INK, lw=0.8)
            ys.append(y)
            labels.append(FIELD_NAMES[k])
        y += 0.9
        share = 100 * s["field_supergroup_shares"][g]["share"]
        a1.text(0.1, y, f"{FIELD_GROUPS[g]}: {share:.0f}%", ha="left", va="center", color=MID)
        y += 0.2
    axis(a1, ys, labels, y - 0.2)
    a1.set_xlim(0, 5 * math.ceil(20 * max(v["hi"] for v in s["field_shares"].values())))
    # (b) question, with the same colours.
    items = list(s["question_shares"].items())
    ys = list(range(len(items), 0, -1))
    for y, (k, v) in zip(ys, items):
        a2.barh(y, 100 * v["share"], height=0.8, color=ORANGE if qcb[k] == "physical-world" else LIGHT, lw=0)
        a2.plot([100 * v["lo"], 100 * v["hi"]], [y, y], color=INK, lw=0.8)
    axis(a2, ys, [QUESTION_NAMES[k] for k, _ in items], len(items))
    a2.set_xlim(0, 10 * math.ceil(10 * max(v["hi"] for v in s["question_shares"].values())))
    a2.legend(handles=[Patch(color=ORANGE, label="about the physical world"),
                       Patch(color=LIGHT, label="about the AI or workflow")], loc="lower right", handlelength=1.2)
    a2.set_xlabel(f"share of the {s['n']} papers (%)")
    for a, lab in ((a1, "(a) field"), (a2, "(b) question")):
        a.text(-0.02, 1.0, lab, transform=a.transAxes, ha="right", va="bottom")
    fig.tight_layout(pad=0.3, h_pad=0.6)
    save(fig, "fig-subjects")
    numbers["subjects"] = {"physical_world": s["question_supergroup_shares"]["physical-world"],
                           "field_supergroups": s["field_supergroup_shares"],
                           "agreement": {k: v["kappa"] for k, v in s["agreement"].items()}}


def main():
    numbers = {}
    pace(numbers)
    issues(numbers)
    trend(numbers)
    # Fig. 2 has many labelled rows: one point smaller type leaves room between them.
    with plt.rc_context({k: 11 for k in ("font.size", "axes.labelsize", "xtick.labelsize", "ytick.labelsize",
                                         "legend.fontsize")}):
        subjects(numbers)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "numbers.json").write_text(json.dumps(numbers, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(numbers, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
