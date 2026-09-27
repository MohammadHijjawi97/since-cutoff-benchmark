"""Known values for the statistics in plan B.6."""

import math

import pytest

from bench import stats


def test_holm_known_values():
    adj = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.005})
    # sorted 0.005*4=0.02, 0.01*3=0.03, 0.03*2=0.06, max(0.04*1, 0.06)=0.06
    assert adj == pytest.approx({"a": 0.03, "b": 0.06, "c": 0.06, "d": 0.02})


def test_holm_caps_at_one_and_skips_nan():
    adj = stats.holm({"a": 0.6, "b": 0.7, "c": float("nan")})
    assert adj["a"] == 1.0 and adj["b"] == 1.0 and math.isnan(adj["c"])


def test_mcnemar_exact_known_value():
    # 6 tasks fixed, 1 broken: two-sided exact binomial p = 2 * (C(7,0)+C(7,1)) / 2^7 = 0.125
    t = [True] * 6 + [False] + [True] * 3 + [False] * 2
    c = [False] * 6 + [True] + [True] * 3 + [False] * 2
    m = stats.mcnemar(t, c)
    assert (m.fixed, m.broke, m.both, m.neither) == (6, 1, 3, 2)
    assert m.p == pytest.approx(0.125)


def test_binomial_edge_cases():
    assert stats.binom_two_sided(0, 0) == 1.0
    assert stats.binom_two_sided(3, 6) == 1.0          # perfectly balanced
    assert stats.binom_two_sided(0, 5) == pytest.approx(2 / 32)


def test_sign_flip_exact_known_values():
    assert stats.sign_flip_p([1, 1, 1, 1, 1]) == pytest.approx(2 / 32)
    # sum of five +-1: P(|S| >= 3) = 2 * (C(5,0) + C(5,1)) / 32
    assert stats.sign_flip_p([1, 1, 1, 1, -1]) == pytest.approx(12 / 32)
    assert stats.sign_flip_p([1, 1, 1, 1, 1], alternative="greater") == pytest.approx(1 / 32)
    assert stats.sign_flip_p([0, 0, 0]) == 1.0


def test_sign_flip_thirds_lattice_19_tasks():
    # pass-rate differences are multiples of 1/3 with 3 reps; 2^19 patterns enumerated exactly
    diffs = [1 / 3] * 10 + [0.0] * 6 + [-1 / 3] * 3
    p = stats.sign_flip_p(diffs)
    # exact: 13 non-zero +-1/3 values, observed sum 7/3 -> P(|S| >= 7) over 13 fair signs
    k_needed = 10  # S = 2k - 13 >= 7 -> k >= 10
    tail = sum(math.comb(13, k) for k in range(k_needed, 14)) / 2 ** 13
    assert p == pytest.approx(2 * tail)


def test_sign_flip_matches_brute_force_on_floats():
    import itertools
    d = [0.3, -0.1, 0.25, 0.05, -0.2, 0.4, 0.15]
    obs = abs(sum(d))
    count = sum(1 for signs in itertools.product([1, -1], repeat=len(d))
                if abs(sum(s * abs(x) for s, x in zip(signs, d, strict=True))) >= obs - 1e-12)
    assert stats.sign_flip_p(d) == pytest.approx(count / 2 ** len(d))


def test_wilcoxon_darwin_known_value():
    # scipy.stats.wilcoxon docs example (Darwin's plant heights): statistic 24.0, p = 0.041259765625 (exact)
    d = [6, 8, 14, 16, 23, 24, 28, 29, 41, -48, 49, 56, 60, -67, 75]
    w = stats.wilcoxon(d)
    assert w.statistic == 24.0 and w.n == 15
    assert w.p == pytest.approx(0.041259765625)


def test_wilcoxon_all_positive_and_zeros():
    w = stats.wilcoxon([1, 2, 3, 4, 5, 0, 0])
    assert w.n == 5 and w.w_plus == 15 and w.p == pytest.approx(2 / 32)
    assert stats.wilcoxon([0, 0]).p == 1.0


def test_wilcoxon_ties_use_average_ranks():
    w = stats.wilcoxon([1, 1, -1, 2])
    # |d| ranks: 1,1,1 -> 2 each; 2 -> 4. W+ = 2+2+4 = 8, W- = 2
    assert (w.w_plus, w.w_minus) == (8.0, 2.0)
    assert 0 < w.p <= 1


def test_bootstrap_is_deterministic_and_degenerate_for_constants():
    lo, hi = stats.bootstrap_mean_ci([0.2] * 10, resamples=500, seed=3)
    assert lo == pytest.approx(0.2) and hi == pytest.approx(0.2)
    a = stats.bootstrap_mean_ci([0, 1, 0, 1, 1, 0, 1], resamples=2000, seed=11)
    b = stats.bootstrap_mean_ci([0, 1, 0, 1, 1, 0, 1], resamples=2000, seed=11)
    assert a == b and a[0] < 4 / 7 < a[1]


def test_percentile_linear_interpolation():
    assert stats.percentile([1, 2, 3, 4], 0.5) == 2.5
    assert stats.percentile([1, 2, 3, 4], 0.0) == 1 and stats.percentile([1, 2, 3, 4], 1.0) == 4


def test_geometric_mean_ratio():
    r = stats.geometric_mean_ratio([(2, 1), (8, 4), (4, 2)], resamples=500)
    assert r.ratio == pytest.approx(2.0) and r.lo == pytest.approx(2.0) and r.hi == pytest.approx(2.0)
    r = stats.geometric_mean_ratio([(1, 4), (4, 1)], resamples=500)
    assert r.ratio == pytest.approx(1.0)
    # counts can be zero: +1 offset
    r = stats.geometric_mean_ratio([(0, 1), (1, 3)], offset=1.0, resamples=200)
    assert r.ratio == pytest.approx(math.sqrt((1 / 2) * (2 / 4)))
    assert math.isnan(stats.geometric_mean_ratio([(0, 1)]).ratio)


def test_paired_contrast_and_noninferiority():
    per_task = {f"t{i}": {"A": 0.0, "C": 1.0} for i in range(6)}
    per_task["t6"] = {"A": 1.0}  # missing C: skipped
    c = stats.paired_contrast(per_task, "C", "A", resamples=500)
    assert c.n_tasks == 6 and c.delta == 1.0 and c.ci_lo == 1.0
    assert c.p == pytest.approx(2 / 64)
    ni = stats.noninferiority([0.0, -1 / 3, 0.0, 1 / 3, 0.0], margin=-0.10, resamples=2000)
    assert ni["n_tasks"] == 5 and ni["lower"] < 0
    assert stats.noninferiority([0.0] * 5)["non_inferior"] is True


def test_flakiness():
    assert stats.flakiness({"a": [True, True, True], "b": [True, False, True], "c": [False]}) == 0.5
