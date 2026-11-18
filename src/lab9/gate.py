"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def _is_nan_or_inf(val: object) -> bool:
    return isinstance(val, float) and (math.isnan(val) or math.isinf(val))


def _check_ratchet_entry(label: str, base_entry: dict, pr_entry: dict, base_th: dict, pr_th: dict,
                         problems: list[str]) -> None:
    if base_entry.get("blocking") and not pr_entry.get("blocking"):
        problems.append(f"ratchet: {label} became non-blocking")
    if "min" in base_th and ("min" not in pr_th or pr_th["min"] < base_th["min"]):
        problems.append(f"ratchet: {label} min lowered ({base_th['min']} -> {pr_th.get('min')})")
    for upper in ("max", "max_increase"):
        if upper in base_th and (upper not in pr_th or pr_th[upper] > base_th[upper]):
            problems.append(f"ratchet: {label} {upper} raised ({base_th[upper]} -> {pr_th.get(upper)})")
    if base_th.get("no_significant_drop") and not pr_th.get("no_significant_drop"):
        problems.append(f"ratchet: {label} dropped no_significant_drop")


def _ratchet_problems(spec: dict, base_spec: dict) -> list[str]:
    if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return []
    problems: list[str] = []
    spec_metrics = {m["id"]: m for m in spec.get("metrics") or []}
    for bm in base_spec.get("metrics") or []:
        mid = bm["id"]
        if mid not in spec_metrics:
            problems.append(f"ratchet: metric {mid} removed")
            continue
        sm = spec_metrics[mid]
        _check_ratchet_entry(f"metric {mid}", bm, sm, bm.get("threshold") or {}, sm.get("threshold") or {}, problems)

    spec_slices = {(s.get("name"), s.get("metric")): s for s in spec.get("slices") or []}
    for bs in base_spec.get("slices") or []:
        key = (bs.get("name"), bs.get("metric"))
        label = f"slice {bs.get('name')}/{bs.get('metric')}"
        if key not in spec_slices:
            problems.append(f"ratchet: {label} removed")
            continue
        ss = spec_slices[key]
        _check_ratchet_entry(label, bs, ss, bs, ss, problems)
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy)."""
    problems: list[str] = []
    if pr.get("evaluator_failures"):
        problems.append(f"evaluator_failures non-empty ({len(pr['evaluator_failures'])})")

    pr_metrics = pr.get("metrics") or {}
    base_metrics = base.get("metrics") or {}
    for k, v in pr_metrics.items():
        if _is_nan_or_inf(v):
            problems.append(f"metric {k} is {v}")
    for m in spec.get("metrics") or []:
        mid = m["id"]
        if base_metrics.get(mid) is not None and pr_metrics.get(mid) is None:
            problems.append(f"metric {mid} is missing/None")

    rows = pr.get("rows") or []
    base_rows = base.get("rows") or []
    manifest = pr.get("manifest") or {}
    base_manifest = base.get("manifest") or {}
    expected_n = int(manifest.get("items", 0)) * len(manifest.get("seeds") or [])
    if len(rows) != expected_n:
        problems.append(f"row count {len(rows)} != manifest {expected_n}")
    if sorted(manifest.get("seeds") or []) != sorted(base_manifest.get("seeds") or []):
        problems.append(f"seeds {manifest.get('seeds')} != baseline {base_manifest.get('seeds')}")

    pr_keys = [(r.get("item_id"), r.get("seed")) for r in rows]
    base_keys = [(r.get("item_id"), r.get("seed")) for r in base_rows]
    if len(set(pr_keys)) != len(pr_keys):
        problems.append(f"duplicate (item_id, seed) rows ({len(pr_keys) - len(set(pr_keys))} extra)")
    if set(pr_keys) != set(base_keys):
        problems.append("(item_id, seed) set differs from baseline")

    row_metrics = [m["id"] for m in spec.get("metrics") or []
                   if m["id"] in GRADERS or (base_rows and m["id"] in base_rows[0])]
    bad_row_metrics = {
        mid for mid in row_metrics
        for r in rows
        if r.get(mid) is None or _is_nan_or_inf(r.get(mid))
    }
    for mid in sorted(bad_row_metrics):
        problems.append(f"row(s) have None/NaN for metric {mid}")

    base_slices = {r.get("item_id"): sorted(set(r.get("slices") or [])) for r in base_rows}
    mismatched_slices = sorted({
        str(r.get("item_id")) for r in rows
        if r.get("item_id") in base_slices and sorted(set(r.get("slices") or [])) != base_slices[r["item_id"]]
    })
    if mismatched_slices:
        problems.append(f"slice tags modified for {mismatched_slices}")

    if base_spec is not None:
        problems.extend(_ratchet_problems(spec, base_spec))
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices") or []:
        name, mid = s["name"], s["metric"]
        pr_items = per_item(pr, mid, slice_name=name)
        base_items = per_item(base, mid, slice_name=name)
        verdict, note = "ok", ""
        if not pr_items:
            val = None
            verdict = "missing"
        else:
            val = round(sum(pr_items.values()) / len(pr_items), 4)
            if "min" in s and val < s["min"]:
                verdict = "fail"
            if "max" in s and val > s["max"]:
                verdict = "fail"
            if s.get("no_significant_drop"):
                keys = sorted(set(pr_items) & set(base_items))
                if not keys:
                    verdict = "missing"
                else:
                    d, lo, hi = stats.paired_bootstrap(
                        [pr_items[k] for k in keys],
                        [base_items[k] for k in keys],
                        n_resamples=bs.get("n_resamples", 1000),
                        rng=bs.get("rng", 2027),
                        confidence=bs.get("confidence", 0.95),
                    )
                    note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                    if hi < 0:
                        verdict = "fail"
        sid = f"slice:{name}/{mid}"
        is_blocking = s.get("blocking", True)
        if verdict != "ok" and is_blocking:
            blocked.append(sid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if is_blocking else "warn")
        th = {k: s[k] for k in ("min", "max", "no_significant_drop") if k in s}
        lines.append(f"  {sid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
