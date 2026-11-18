"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

import numpy as np
import scipy.stats

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def _normalize_labels(human: Sequence[str], judge: Sequence[str]) -> tuple[list[str], list[str]]:
    if len(human) != len(judge):
        raise ValueError(f"label length mismatch: human={len(human)} vs judge={len(judge)}")
    return [str(h).strip().upper() for h in human], [str(j).strip().upper() for j in judge]


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    hs, js = _normalize_labels(human, judge)
    tp = sum(h == POS and j == POS for h, j in zip(hs, js))
    fp = sum(h != POS and j == POS for h, j in zip(hs, js))
    fn = sum(h == POS and j != POS for h, j in zip(hs, js))
    tn = sum(h != POS and j != POS for h, j in zip(hs, js))
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    if not human:
        raise ValueError("cohen_kappa undefined for empty sequences")
    cm = confusion(human, judge)
    n = cm["tp"] + cm["fp"] + cm["fn"] + cm["tn"]
    p_o = (cm["tp"] + cm["tn"]) / n
    p_human_pos = (cm["tp"] + cm["fn"]) / n
    p_judge_pos = (cm["tp"] + cm["fp"]) / n
    p_e = p_human_pos * p_judge_pos + (1.0 - p_human_pos) * (1.0 - p_judge_pos)
    if abs(1.0 - p_e) <= 1e-12:
        raise ValueError("cohen_kappa undefined when p_e == 1")
    return (p_o - p_e) / (1.0 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denom = sensitivity + specificity - 1.0
    if abs(denom) <= 1e-12:
        raise ValueError("rogan_gladen undefined when sensitivity + specificity == 1")
    est = (observed_rate + specificity - 1.0) / denom
    return min(1.0, max(0.0, est))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    arr_a = np.asarray(a, dtype=float)
    arr_b = np.asarray(b, dtype=float)
    if arr_a.shape != arr_b.shape or arr_a.ndim != 1 or len(arr_a) == 0:
        raise ValueError("a and b must be non-empty 1D sequences of equal length")
    if np.array_equal(arr_a, arr_b):
        return (0.0, 0.0, 0.0)
    diff = float(np.mean(arr_a) - np.mean(arr_b))
    if len(arr_a) == 1:
        return (diff, diff, diff)
    res = scipy.stats.bootstrap(
        (arr_a, arr_b),
        lambda x, y: np.mean(x, axis=-1) - np.mean(y, axis=-1),
        paired=True,
        n_resamples=n_resamples,
        confidence_level=confidence,
        method="percentile",
        rng=np.random.default_rng(rng),
    )
    return (diff, float(res.confidence_interval.low), float(res.confidence_interval.high))


def _validate_nck(n: int, c: int, k: int) -> None:
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (n, c, k)):
        raise ValueError(f"n, c, k must be integers, got ({n!r}, {c!r}, {k!r})")
    if n < 1 or c < 0 or c > n or k < 1 or k > n:
        raise ValueError(f"invalid (n={n}, c={c}, k={k}): require 1 <= k <= n and 0 <= c <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_nck(n, c, k)
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_nck(n, c, k)
    if c < k:
        return 0.0
    return math.comb(c, k) / math.comb(n, k)
