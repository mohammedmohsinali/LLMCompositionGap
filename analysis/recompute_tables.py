"""Recompute every table in the paper from the per-example prediction logs.

Usage:  python analysis/recompute_tables.py
Reads:  experiments_v2/<domain>/results/predictions_*.json,
        experiments_v2/mechanism/results/*.json,
        experiments_v2/mitigation/results/*.json
Writes: analysis/recompute_out.json plus a printed report covering the main
        results table, CoT and cross-domain permutation tests, the mechanism
        and mitigation tables, the Pass-1 false-positive sensitivity table,
        the shared-eligible-subset table, and the 916 error-case counts.
No API access or model inference is needed; everything reproduces from logs.
"""
import json, os, random
from pathlib import Path
from itertools import combinations

ROOT = Path(__file__).resolve().parent.parent / "experiments_v2"
DOMAINS = ["contracts", "math", "sql", "code", "logic"]
CONFIGS = ["gpt4o", "gpt4o-cot", "deepseek", "deepseek-cot", "qwen7b", "qwen7b-cot", "llama8b", "llama8b-cot"]
BASE4 = ["gpt4o", "deepseek", "qwen7b", "llama8b"]
random.seed(42)

def load_preds(domain, cfg):
    p = ROOT / domain / "results" / f"predictions_{cfg}.json"
    return json.load(open(p)) if p.exists() else None

def gap_stats(preds):
    elig = [p for p in preds if p.get("pieces_all_correct")]
    gap_cases = [p for p in elig if not p.get("composed_correct")]
    n = len(elig)
    g = len(gap_cases) / n * 100 if n else None
    return {"total": len(preds), "eligible": n, "gap_cases": len(gap_cases), "gap_pct": round(g, 1) if g is not None else None}

def boot_ci(preds, iters=10000):
    elig = [0 if p.get("composed_correct") else 1 for p in preds if p.get("pieces_all_correct")]
    n = len(elig)
    if n == 0: return None
    means = []
    for _ in range(iters):
        s = [elig[random.randrange(n)] for _ in range(n)]
        means.append(sum(s) / n * 100)
    means.sort()
    return [round(means[int(0.025 * iters)], 1), round(means[int(0.975 * iters) - 1], 1)]

def perm_test(a, b, iters=10000):
    """Two-sample permutation test on gap indicator lists (1 = gap case)."""
    obs = abs(sum(a)/len(a) - sum(b)/len(b))
    pool = a + b
    na = len(a)
    cnt = 0
    for _ in range(iters):
        random.shuffle(pool)
        d = abs(sum(pool[:na])/na - sum(pool[na:])/(len(pool)-na))
        if d >= obs - 1e-12: cnt += 1
    return cnt / iters

def elig_indicators(preds):
    return [0 if p.get("composed_correct") else 1 for p in preds if p.get("pieces_all_correct")]

out = {}

# ---------- 1. Baselines (Table 2 + Table 9) ----------
base = {}
for d in DOMAINS:
    base[d] = {}
    for c in CONFIGS:
        preds = load_preds(d, c)
        if preds is None:
            base[d][c] = None; continue
        s = gap_stats(preds)
        s["ci"] = boot_ci(preds)
        base[d][c] = s
out["baseline"] = base

# ---------- 2. Run-to-run ("-cot" = identical-prompt repeat run) checks ----------
cot_tests = {}
for d in DOMAINS:
    for fam in BASE4:
        pb, pc = load_preds(d, fam), load_preds(d, fam + "-cot")
        if pb is None or pc is None:
            cot_tests[f"{d}/{fam}"] = None; continue
        identical = json.dumps(pb, sort_keys=True) == json.dumps(pc, sort_keys=True)
        p = 1.0 if identical else perm_test(elig_indicators(pb), elig_indicators(pc))
        cot_tests[f"{d}/{fam}"] = {"identical": identical, "p": round(p, 4)}
out["cot_tests"] = cot_tests

# ---------- 3. Cross-domain permutation tests (4 base fams x 10 pairs) ----------
cross = {}
sig = 0; tot = 0
for fam in BASE4:
    for d1, d2 in combinations(DOMAINS, 2):
        a = elig_indicators(load_preds(d1, fam) or [])
        b = elig_indicators(load_preds(d2, fam) or [])
        if not a or not b: continue
        p = perm_test(a, b)
        tot += 1; sig += (p < 0.05)
        cross[f"{fam}:{d1}-vs-{d2}"] = round(p, 4)
out["cross_domain"] = {"tests": cross, "significant": sig, "total": tot}

# ---------- 4. Mechanism (Tables 4 and 7) ----------
mech = {}
for d in DOMAINS:
    mech[d] = {}
    for c in CONFIGS:
        p = ROOT / "mechanism" / "results" / f"mechanism_{d}_{c}.json"
        if not p.exists(): mech[d][c] = None; continue
        m = json.load(open(p))
        row = {}
        for cond in ["original", "hint_correct", "hint_wrong"]:
            blk = m.get(cond, {})
            row[cond] = {"n": blk.get("eligible_examples"), "gap_pct": blk.get("gap_pct")}
        mech[d][c] = row
out["mechanism"] = mech

# averaged across base 4 (Table 4 recompute)
mech_avg = {}
for d in DOMAINS:
    rows = [mech[d][c] for c in BASE4 if mech[d].get(c)]
    if not rows: continue
    mech_avg[d] = {cond: round(sum(r[cond]["gap_pct"] for r in rows) / len(rows), 1)
                   for cond in ["original", "hint_correct", "hint_wrong"]}
out["mechanism_avg_base4"] = mech_avg
# averaged over the three full-scale families (paper Table 4; DeepSeek pilots excluded)
FULL3 = ["gpt4o", "qwen7b", "llama8b"]
mech_avg3 = {}
for d in DOMAINS:
    rows = [mech[d][c] for c in FULL3 if mech[d].get(c)]
    if rows:
        mech_avg3[d] = {cond: round(sum(r[cond]["gap_pct"] for r in rows) / len(rows), 1)
                        for cond in ["original", "hint_correct", "hint_wrong"]}
out["mechanism_avg_fullscale3"] = mech_avg3

# ---------- 5. Mitigation (Tables 5/8/10/11) ----------
mit = {}
for d in DOMAINS:
    mit[d] = {}
    for c in CONFIGS:
        p = ROOT / "mitigation" / "results" / f"mitigation_{d}_{c}.json"
        if not p.exists(): mit[d][c] = None; continue
        m = json.load(open(p))
        row = {}
        for cond in ["original", "self_structure", "cot_structure"]:
            blk = m.get(cond, {})
            row[cond] = {"n": blk.get("eligible_examples"), "gap_pct": blk.get("gap_pct")}
        mit[d][c] = row
out["mitigation"] = mit

# ---------- 6. Pass-1 FP sensitivity ----------
FP = {"contracts": 0.04, "math": 0.06, "sql": 0.11, "code": 0.14, "logic": 0.08}
def corrected(g, f): return round(max(0.0, (g - f * 100) / (1 - f)), 1)
sens = {}
for d in DOMAINS:
    sens[d] = {}
    for c in CONFIGS:
        s = base[d].get(c)
        if not s or s["gap_pct"] is None: continue
        g = s["gap_pct"]
        sens[d][c] = {"audited": corrected(g, FP[d]),
                      "f5": corrected(g, 0.05), "f10": corrected(g, 0.10), "f15": corrected(g, 0.15)}
out["sensitivity"] = sens

# ---------- 7. Shared eligible intersection (gpt4o, qwen7b, llama8b) ----------
shared = {}
FAMS3 = ["gpt4o", "qwen7b", "llama8b"]
for d in DOMAINS:
    preds = {f: load_preds(d, f) for f in FAMS3}
    if any(v is None for v in preds.values()): continue
    elig_sets = {f: {p["idx"] for p in preds[f] if p.get("pieces_all_correct")} for f in FAMS3}
    inter = set.intersection(*elig_sets.values())
    row = {"n_shared": len(inter)}
    for f in FAMS3:
        by_idx = {p["idx"]: p for p in preds[f]}
        wrong = sum(1 for i in inter if not by_idx[i].get("composed_correct"))
        row[f] = round(wrong / len(inter) * 100, 1) if inter else None
    shared[d] = row
out["shared_subset"] = shared

# ---------- 8. Error-analysis reconciliation (916 = gpt4o + qwen gap cases) ----------
recon = {}
for fam in ["gpt4o", "qwen7b"]:
    tot_cases = {d: base[d][fam]["gap_cases"] for d in DOMAINS if base[d].get(fam)}
    recon[fam] = {"per_domain": tot_cases, "sum": sum(tot_cases.values())}
out["error_916"] = recon

json.dump(out, open(Path(__file__).parent / "recompute_out.json", "w"), indent=1)

# ---------- printed report ----------
print("=== TABLE 2 (baseline gap %, eligible n) ===")
hdr = ["domain"] + CONFIGS
print(" | ".join(f"{h:>12}" for h in hdr))
for d in DOMAINS:
    cells = []
    for c in CONFIGS:
        s = base[d].get(c)
        cells.append(f"{s['gap_pct']} (n={s['eligible']})" if s else "-")
    print(f"{d:>12} | " + " | ".join(f"{x:>12}" for x in cells))

print("\n=== GPT-4o row CIs ===")
for d in DOMAINS:
    s = base[d]["gpt4o"]
    print(f"{d}: {s['gap_pct']} CI {s['ci']} n={s['eligible']} total={s['total']}")

print("\n=== Run-1 vs run-2 permutation tests ('-cot' files are identical-prompt repeats) ===")
for k, v in cot_tests.items(): print(f"{k}: {v}")

print(f"\n=== Cross-domain: {out['cross_domain']['significant']}/{out['cross_domain']['total']} significant ===")

print("\n=== MECHANISM per model (base 4) ===")
for d in DOMAINS:
    for c in BASE4:
        r = mech[d].get(c)
        if r: print(f"{d:>10} {c:>8}: orig {r['original']['gap_pct']} (n={r['original']['n']})  correct {r['hint_correct']['gap_pct']}  wrong {r['hint_wrong']['gap_pct']}")

print("\n=== MECHANISM avg (paper Table 4: GPT-4o/Qwen/Llama) ===")
for d, r in mech_avg3.items(): print(f"{d}: {r}")
print("\n=== MECHANISM avg incl. DeepSeek pilots (not used in paper) ===")
for d, r in mech_avg.items(): print(f"{d}: {r}")

print("\n=== MITIGATION (gpt4o / qwen7b / llama8b) ===")
for d in DOMAINS:
    for c in ["gpt4o", "qwen7b", "llama8b", "deepseek"]:
        r = mit[d].get(c)
        if r: print(f"{d:>10} {c:>8}: orig {r['original']['gap_pct']} (n={r['original']['n']})  self {r['self_structure']['gap_pct']} (n={r['self_structure']['n']})  cot {r['cot_structure']['gap_pct']} (n={r['cot_structure']['n']})")

print("\n=== SENSITIVITY (audited FP) ===")
for d in DOMAINS:
    print(d, {c: sens[d][c]["audited"] for c in CONFIGS if c in sens[d]})

print("\n=== SHARED SUBSET ===")
for d, r in shared.items(): print(d, r)

print("\n=== 916 RECONCILIATION ===")
print(recon, "sum =", recon["gpt4o"]["sum"] + recon["qwen7b"]["sum"])
