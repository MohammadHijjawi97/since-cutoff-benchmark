"""Statistics for plan B.6 (standard library only, deterministic given a seed).

- task-cluster bootstrap (10,000 resamples of tasks, percentile CI)
- exact sign-flip permutation test of per-task differences (2^n sign patterns, computed exactly by
  dynamic programming over the sums; Monte Carlo only above `exact_limit` tasks with non-lattice values)
- Holm step-down adjustment
- exact McNemar (binomial) on each task's majority outcome
- paired geometric-mean ratios with bootstrap CIs
- Wilcoxon signed-rank, exact null distribution with average ranks for ties (zeros dropped)
- non-inferiority: one-sided (1 - alpha) lower bound of the mean difference >= margin
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Sequence


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def percentile(sorted_xs: Sequence[float], q: float) -> float:
    """Linear interpolation between closest ranks (numpy's default), q in [0, 1]."""
    if not sorted_xs:
        return float("nan")
    pos = (len(sorted_xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(sorted_xs[lo])
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (pos - lo)


# -- bootstrap -------------------------------------------------------------------------------------
def bootstrap(items: Sequence, stat: Callable[[list], float], *, resamples: int = 10_000, seed: int = 0
              ) -> list[float]:
    """Statistic over `resamples` resamples of the items (tasks) with replacement; NaNs dropped, sorted."""
    rng = random.Random(seed)
    n = len(items)
    if n == 0:
        return []
    out = []
    for _ in range(resamples):
        sample = [items[rng.randrange(n)] for _ in range(n)]
        v = stat(sample)
        if not math.isnan(v):
            out.append(v)
    out.sort()
    return out


def bootstrap_mean_ci(values: Sequence[float], *, resamples: int = 10_000, alpha: float = 0.05, seed: int = 0
                      ) -> tuple[float, float]:
    dist = bootstrap(list(values), mean, resamples=resamples, seed=seed)
    return percentile(dist, alpha / 2), percentile(dist, 1 - alpha / 2)


def one_sided_lower(values: Sequence[float], *, resamples: int = 10_000, alpha: float = 0.05, seed: int = 0
                    ) -> float:
    dist = bootstrap(list(values), mean, resamples=resamples, seed=seed)
    return percentile(dist, alpha)


# -- sign-flip permutation -------------------------------------------------------------------------
def _lattice(values: Sequence[float], max_den: int = 1000) -> tuple[list[int], Fraction] | None:
    """Express values as integers times a common step when they are (near) rationals with small denominators."""
    fracs = []
    for v in values:
        f = Fraction(v).limit_denominator(max_den)
        if abs(float(f) - v) > 1e-9:
            return None
        fracs.append(f)
    den = 1
    for f in fracs:
        den = den * f.denominator // math.gcd(den, f.denominator)
    return [int(f * den) for f in fracs], Fraction(1, den)


def sign_flip_p(diffs: Sequence[float], *, alternative: str = "two-sided", exact_limit: int = 20,
                mc_samples: int = 200_000, seed: int = 0) -> float:
    """P-value of the mean difference under random sign flips (exact over all 2^n patterns when possible)."""
    d = [float(x) for x in diffs]
    n = len(d)
    if n == 0:
        return float("nan")
    obs = sum(d)
    lattice = _lattice(d)
    if lattice is not None or n <= exact_limit:
        if lattice is not None:
            ints, _ = lattice
            obs_i = sum(ints)
            dist: dict[int, int] = {0: 1}
            for v in ints:
                nxt: dict[int, int] = defaultdict(int)
                for s, c in dist.items():
                    nxt[s + abs(v)] += c
                    nxt[s - abs(v)] += c
                dist = nxt
            total = 2 ** n
            if alternative == "two-sided":
                hits = sum(c for s, c in dist.items() if abs(s) >= abs(obs_i))
            elif alternative == "greater":
                hits = sum(c for s, c in dist.items() if s >= obs_i)
            else:
                hits = sum(c for s, c in dist.items() if s <= obs_i)
            return hits / total
        # exact enumeration over floats (n <= exact_limit)
        sums: dict[float, int] = {0.0: 1}
        for v in d:
            nxt_f: dict[float, int] = defaultdict(int)
            for s, c in sums.items():
                nxt_f[round(s + abs(v), 12)] += c
                nxt_f[round(s - abs(v), 12)] += c
            sums = nxt_f
        eps = 1e-9
        total = 2 ** n
        if alternative == "two-sided":
            hits = sum(c for s, c in sums.items() if abs(s) >= abs(obs) - eps)
        elif alternative == "greater":
            hits = sum(c for s, c in sums.items() if s >= obs - eps)
        else:
            hits = sum(c for s, c in sums.items() if s <= obs + eps)
        return hits / total
    rng = random.Random(seed)
    hits = 0
    for _ in range(mc_samples):
        s = sum(v if rng.random() < 0.5 else -v for v in d)
        if alternative == "two-sided":
            hits += abs(s) >= abs(obs) - 1e-12
        elif alternative == "greater":
            hits += s >= obs - 1e-12
        else:
            hits += s <= obs + 1e-12
    return (hits + 1) / (mc_samples + 1)


# -- multiplicity ----------------------------------------------------------------------------------
def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values (NaNs are left as NaN and not counted)."""
    items = sorted(((p, k) for k, p in pvalues.items() if not math.isnan(p)))
    m = len(items)
    adjusted: dict[str, float] = {k: float("nan") for k in pvalues}
    running = 0.0
    for i, (p, k) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[k] = running
    return adjusted


# -- McNemar ---------------------------------------------------------------------------------------
def binom_two_sided(k: int, n: int) -> float:
    """Exact two-sided binomial test p for k successes in n trials at p = 0.5."""
    if n == 0:
        return 1.0
    k = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


@dataclass
class McNemar:
    fixed: int   # treatment passes, control fails
    broke: int   # treatment fails, control passes
    both: int
    neither: int
    p: float


def mcnemar(treatment: Sequence[bool], control: Sequence[bool]) -> McNemar:
    fixed = sum(1 for t, c in zip(treatment, control, strict=True) if t and not c)
    broke = sum(1 for t, c in zip(treatment, control, strict=True) if c and not t)
    both = sum(1 for t, c in zip(treatment, control, strict=True) if t and c)
    neither = sum(1 for t, c in zip(treatment, control, strict=True) if not t and not c)
    return McNemar(fixed, broke, both, neither, binom_two_sided(fixed, fixed + broke))


# -- Wilcoxon signed-rank --------------------------------------------------------------------------
@dataclass
class Wilcoxon:
    n: int            # non-zero differences
    w_plus: float
    w_minus: float
    statistic: float  # min(W+, W-), as scipy reports it
    p: float


def wilcoxon(diffs: Sequence[float]) -> Wilcoxon:
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n == 0:
        return Wilcoxon(0, 0.0, 0.0, 0.0, 1.0)
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    w_plus = sum(r for r, x in zip(ranks, d, strict=True) if x > 0)
    w_minus = sum(r for r, x in zip(ranks, d, strict=True) if x < 0)
    doubled = [int(round(2 * r)) for r in ranks]
    dist: dict[int, int] = {0: 1}
    for r in doubled:
        nxt: dict[int, int] = defaultdict(int)
        for s, c in dist.items():
            nxt[s] += c
            nxt[s + r] += c
        dist = nxt
    total = 2 ** n
    w = int(round(2 * w_plus))
    lower = sum(c for s, c in dist.items() if s <= w) / total
    upper = sum(c for s, c in dist.items() if s >= w) / total
    return Wilcoxon(n, w_plus, w_minus, min(w_plus, w_minus), min(1.0, 2 * min(lower, upper)))


# -- ratios ----------------------------------------------------------------------------------------
@dataclass
class Ratio:
    ratio: float
    lo: float
    hi: float
    n: int
    offset: float


def geometric_mean_ratio(pairs: Sequence[tuple[float, float]], *, offset: float = 0.0, resamples: int = 10_000,
                         alpha: float = 0.05, seed: int = 0) -> Ratio:
    """exp(mean(log((t + offset) / (c + offset)))) over tasks, with a task-bootstrap CI.

    Pairs with a non-positive value (after the offset) are dropped; `offset=1` is used for counts that can be 0."""
    logs = [math.log((t + offset) / (c + offset)) for t, c in pairs
            if t is not None and c is not None and t + offset > 0 and c + offset > 0]
    if not logs:
        return Ratio(float("nan"), float("nan"), float("nan"), 0, offset)
    dist = bootstrap(logs, mean, resamples=resamples, seed=seed)
    return Ratio(math.exp(mean(logs)), math.exp(percentile(dist, alpha / 2)),
                 math.exp(percentile(dist, 1 - alpha / 2)), len(logs), offset)


# -- summaries -------------------------------------------------------------------------------------
@dataclass
class Contrast:
    treatment: str
    control: str
    n_tasks: int
    delta: float
    ci_lo: float
    ci_hi: float
    p: float
    p_holm: float | None = None


def paired_contrast(per_task: dict[str, dict[str, float]], treatment: str, control: str, *,
                    resamples: int = 10_000, alpha: float = 0.05, seed: int = 0) -> Contrast:
    """per_task[task][condition] = pass rate; tasks missing either condition are skipped."""
    diffs = [v[treatment] - v[control] for v in per_task.values() if treatment in v and control in v]
    if not diffs:
        return Contrast(treatment, control, 0, float("nan"), float("nan"), float("nan"), float("nan"))
    lo, hi = bootstrap_mean_ci(diffs, resamples=resamples, alpha=alpha, seed=seed)
    return Contrast(treatment, control, len(diffs), mean(diffs), lo, hi, sign_flip_p(diffs))


def noninferiority(diffs: Sequence[float], *, margin: float = -0.10, alpha: float = 0.05, resamples: int = 10_000,
                   seed: int = 0) -> dict[str, float | bool | int]:
    if not diffs:
        return {"n_tasks": 0, "delta": float("nan"), "lower": float("nan"), "margin": margin, "non_inferior": False}
    lower = one_sided_lower(diffs, resamples=resamples, alpha=alpha, seed=seed)
    return {"n_tasks": len(diffs), "delta": mean(diffs), "lower": lower, "margin": margin,
            "non_inferior": lower >= margin}


def flakiness(outcomes: dict[str, list[bool]]) -> float:
    """Share of tasks whose repeated outcomes are mixed (some pass, some fail); tasks with < 2 runs skipped."""
    eligible = [v for v in outcomes.values() if len(v) >= 2]
    if not eligible:
        return float("nan")
    return sum(1 for v in eligible if any(v) and not all(v)) / len(eligible)
