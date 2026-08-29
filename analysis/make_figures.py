"""Regenerate the paper's data-derived figures from the prediction logs.

Usage:  python analysis/make_figures.py   (requires matplotlib)
Writes: analysis/figures/*.png

Figures produced here: the implicitness-gradient line chart, the CoT-delta
heatmap, the mechanism bar chart, and the two mitigation figures. The
failure-type distribution figure is not regenerated because the per-example
error-taxonomy labels live in the annotation spreadsheet, not in these logs;
its aggregate counts are given in the paper (Table 6).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent / "experiments_v2"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False})

DOMAINS = ["contracts", "math", "sql", "code", "logic"]
DOM_LABELS = ["Contracts", "Math", "SQL", "Code$^\\dagger$", "Logic"]


def gap(domain, cfg):
    p = ROOT / domain / "results" / f"predictions_{cfg}.json"
    preds = json.load(open(p))
    elig = [x for x in preds if x.get("pieces_all_correct")]
    return sum(1 for x in elig if not x.get("composed_correct")) / len(elig) * 100


def mech(domain, cfg, cond):
    m = json.load(open(ROOT / "mechanism" / "results" / f"mechanism_{domain}_{cfg}.json"))
    return m[cond]["gap_pct"]


def mit(domain, cfg, cond):
    m = json.load(open(ROOT / "mitigation" / "results" / f"mitigation_{domain}_{cfg}.json"))
    return m[cond]["gap_pct"]


# ---------- Figure: implicitness gradient ----------
series = {
    "GPT-4o":           ("gpt4o",        "#1f77b4", "-",  "o"),
    "GPT-4o+CoT":       ("gpt4o-cot",    "#000000", "--", "^"),
    "DeepSeek (pilot)": ("deepseek",     "#2ca02c", "-",  "s"),
    "Qwen-7B":          ("qwen7b",       "#ff7f0e", "-",  "D"),
    "Llama-8B":         ("llama8b",      "#9467bd", "-",  "X"),
}
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(5)
for name, (cfg, col, ls, mk) in series.items():
    ys = [gap(d, cfg) for d in DOMAINS]
    ax.plot(x, ys, ls, color=col, marker=mk, markersize=9, linewidth=2.5, label=name)
ax.set_xticks(x); ax.set_xticklabels(DOM_LABELS)
ax.set_ylabel("Composition gap (%)")
ax.set_xlabel("Domain ordered by structural implicitness")
ax.set_ylim(0, 100)
ax.grid(axis="y", alpha=0.3)
ax.legend(ncol=3, frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "figure1_implicitness_gradient.png", dpi=300)
plt.close(fig)

# ---------- Figure: CoT delta heatmap ----------
fams = [("GPT-4o", "gpt4o"), ("Qwen-7B", "qwen7b"), ("Llama-8B", "llama8b")]
delta = np.array([[gap(d, f + "-cot") - gap(d, f) for d in DOMAINS] for _, f in fams])
fig, ax = plt.subplots(figsize=(9, 3.2))
im = ax.imshow(delta, cmap="coolwarm", vmin=-5, vmax=5, aspect="auto")
ax.set_xticks(range(5)); ax.set_xticklabels([d.title() for d in DOMAINS])
ax.set_yticks(range(3)); ax.set_yticklabels([n for n, _ in fams])
for i in range(3):
    for j in range(5):
        ax.text(j, i, f"{delta[i, j]:+.1f}", ha="center", va="center", fontsize=10)
fig.colorbar(im, ax=ax, label="CoT $-$ Base (pp)")
fig.savefig(OUT / "figure2_cot_delta.png", dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------- Figure: mechanism (3 full-scale family averages, code excluded) ----------
mdoms = ["contracts", "math", "sql", "logic"]
fams3 = ["gpt4o", "qwen7b", "llama8b"]
vals = {c: [np.mean([mech(d, f, c) for f in fams3]) for d in mdoms]
        for c in ["original", "hint_correct", "hint_wrong"]}
fig, ax = plt.subplots(figsize=(10, 4.5))
x = np.arange(4); w = 0.26
for off, cond, col, hatch, lab in [(-w, "original", "#7f7f7f", "", "Original"),
                                   (0, "hint_correct", "#1f77b4", "//", "Correct hint"),
                                   (w, "hint_wrong", "#d62728", "xx", "Wrong hint")]:
    bars = ax.bar(x + off, vals[cond], w, color=col, hatch=hatch, edgecolor="white", label=lab)
    for b, v in zip(bars, vals[cond]):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}", ha="center", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels([d.title() for d in mdoms])
ax.set_ylabel("Composition gap (%)")
ax.set_ylim(0, 80)
ax.grid(axis="y", alpha=0.3)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT / "figure4_mechanism.png", dpi=300)
plt.close(fig)

# ---------- Figures: mitigation bars and delta heatmap (code excluded) ----------
mnames = [("GPT-4o", "gpt4o"), ("Qwen-7B", "qwen7b"), ("Llama-8B", "llama8b")]
fig, axes = plt.subplots(2, 2, figsize=(11, 7))
for ax, d in zip(axes.flat, mdoms):
    x = np.arange(3); w = 0.26
    for off, cond, col, lab in [(-w, "original", "#7f7f7f", "Original"),
                                (0, "self_structure", "#1f77b4", "Self-structure"),
                                (w, "cot_structure", "#ff7f0e", "CoT-structure")]:
        ax.bar(x + off, [mit(d, f, cond) for _, f in mnames], w, color=col, label=lab)
    ax.set_xticks(x); ax.set_xticklabels([n for n, _ in mnames])
    ax.set_title(d.title(), fontsize=12)
    ax.set_ylabel("Gap (%)")
    ax.grid(axis="y", alpha=0.3)
axes.flat[0].legend(frameon=False, fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "figure5_mitigation_gap_by_domain.png", dpi=300)
plt.close(fig)

d_self = np.array([[mit(d, f, "self_structure") - mit(d, f, "original") for d in mdoms] for _, f in mnames])
d_cot = np.array([[mit(d, f, "cot_structure") - mit(d, f, "original") for d in mdoms] for _, f in mnames])
vmax = max(abs(d_self).max(), abs(d_cot).max())
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
for ax, mat, title in [(axes[0], d_self, "$\\Delta$ Self-structure (pp)"),
                       (axes[1], d_cot, "$\\Delta$ CoT-structure (pp)")]:
    im = ax.imshow(mat, cmap="RdYlGn_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(4)); ax.set_xticklabels([d.title() for d in mdoms])
    ax.set_yticks(range(3)); ax.set_yticklabels([n for n, _ in mnames])
    ax.set_title(title, fontsize=12)
    for i in range(3):
        for j in range(4):
            ax.text(j, i, f"{mat[i, j]:+.1f}", ha="center", va="center", fontsize=10)
fig.colorbar(im, ax=axes, shrink=0.85, label="Gap change (pp)")
fig.savefig(OUT / "figure6_mitigation_delta_heatmap.png", dpi=300, bbox_inches="tight")
plt.close(fig)

print("wrote:", sorted(p.name for p in OUT.iterdir()))
