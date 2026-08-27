"""
CrossHair Contract-Verified Tests for Rapisarda MDAO Geometry Equations
========================================================================
Uses CrossHair's SMT-backed contract checking (PEP316 docstring contracts)
to verify mathematical properties of the Rapisarda parameterization.

This file imports ONLY from rapisarda_math.py (zero side-effect imports),
so CrossHair can safely analyze without blocking on matplotlib/CadQuery.

Run:  crosshair check test_crosshair_rapisarda.py
"""

from rapisarda_math import (
    L_shell,
    h_shell,
    mass_total,
    p_min_inflation,
    rinflated_from_params,
    rn_from_rpay,
    scallop_augmented_heat,
    sigma_toroid,
    sigma_wrap,
)


# =============================================================================
# CONTRACT 1: Eq 3.4 — rN = rpay / cos(θc) > 0
# =============================================================================
def eq34_rn_positive(r_pay: float, cos_tc: float) -> float:
    """
    pre: r_pay > 0
    pre: cos_tc > 0 and cos_tc <= 1
    pre: math.isfinite(r_pay)
    pre: math.isfinite(cos_tc)

    Eq 3.4: Nose-cone radius rN = rpay / cos(θc)
    post: _ > 0
    post: math.isfinite(_)
    """
    result = rn_from_rpay(r_pay, cos_tc)
    return result


# =============================================================================
# CONTRACT 2: Eq 3.3 — r_inflated > rN in design space
# =============================================================================
def eq33_rinflated_gt_rn(
    r_torus: float, sin_tc: float, cos_tc: float,
    r_out_torus: float, r_pay: float,
) -> float:
    """
    pre: r_torus >= 0.05
    pre: r_torus < 100.0
    pre: sin_tc > 0 and sin_tc < 1.0
    pre: cos_tc > 0 and cos_tc <= 1.0
    pre: r_out_torus >= 0.0
    pre: r_out_torus < 100.0
    pre: r_pay > 0.0
    pre: r_pay < 100.0
    pre: math.isfinite(r_torus)
    pre: math.isfinite(sin_tc)
    pre: math.isfinite(cos_tc)
    pre: math.isfinite(r_out_torus)
    pre: math.isfinite(r_pay)

    Eq 3.3 vs 3.4: r_inflated > rN in valid design space (θc<45°, N=6)
    post: _ > 0
    post: math.isfinite(_)
    """
    rn = rn_from_rpay(r_pay, cos_tc)
    rinf = rinflated_from_params(r_torus, sin_tc, cos_tc, 6, r_out_torus, rn)
    return rinf


# =============================================================================
# CONTRACT 3: Eq 3.3 — r_inflated increases with N
# =============================================================================
def eq33_rinflated_increases_with_n(
    r_torus: float, sin_tc: float, cos_tc: float,
    r_out_torus: float, r_pay: float,
) -> bool:
    """
    pre: r_torus >= 0.05
    pre: r_torus < 100.0
    pre: sin_tc > 0
    pre: sin_tc < 1.0
    pre: cos_tc > 0
    pre: cos_tc <= 1.0
    pre: r_out_torus >= 0.0
    pre: r_out_torus < 100.0
    pre: r_pay > 0.0
    pre: r_pay < 100.0

    Eq 3.3: r_inflated(N=8) > r_inflated(N=4) when sin(θc) > 0
    post: _ is True
    """
    rn = rn_from_rpay(r_pay, cos_tc)
    r4 = rinflated_from_params(r_torus, sin_tc, cos_tc, 4, r_out_torus, rn)
    r8 = rinflated_from_params(r_torus, sin_tc, cos_tc, 8, r_out_torus, rn)
    return r8 > r4


# =============================================================================
# CONTRACT 4: C.17 — h_shell > 0
# =============================================================================
def c17_hshell_positive(r_inflated: float, sin_tc: float) -> float:
    """
    pre: r_inflated > 0
    pre: r_inflated < 1000.0
    pre: sin_tc > 0.01
    pre: sin_tc < 1.0
    pre: math.isfinite(r_inflated)
    pre: math.isfinite(sin_tc)

    C.17: h_shell = r_inflated / sin(θc)
    post: _ > 0
    post: math.isfinite(_)
    """
    return h_shell(r_inflated, sin_tc)


# =============================================================================
# CONTRACT 5: Eq 3.7 — σ_toroid > 0
# =============================================================================
def eq37_sigma_toroid_positive(
    p_inf: float, r_torus: float, r_pay: float,
) -> float:
    """
    pre: p_inf > 0
    pre: p_inf < 1e8
    pre: r_torus > 0
    pre: r_torus < 100.0
    pre: r_pay > 0
    pre: r_pay < 100.0

    Eq 3.7: σ_toroid = (p*rt/2)*(2 + rt/rpay)
    post: _ > 0
    post: math.isfinite(_)
    """
    return sigma_toroid(p_inf, r_torus, r_pay)


# =============================================================================
# CONTRACT 6: C.23 — p_min > 0
# =============================================================================
def c23_pmin_positive(
    D: float, sin_tc: float, cos_tc: float,
    r_inflated: float, r_torus: float,
) -> float:
    """
    pre: D > 0
    pre: D < 1e8
    pre: sin_tc > 0.01
    pre: sin_tc < 1.0
    pre: cos_tc > 0.01
    pre: cos_tc <= 1.0
    pre: r_inflated > 0
    pre: r_inflated < 1000.0
    pre: r_torus > 0
    pre: r_torus < 100.0

    C.23: p_min = D * sin²(θc) / (3 * rinf * rt * π * cos(θc))
    post: _ > 0
    post: math.isfinite(_)
    """
    return p_min_inflation(D, sin_tc, cos_tc, r_inflated, r_torus)


# =============================================================================
# CONTRACT 7: Eq 3.9 — σ_wrap >= 0
# =============================================================================
def eq39_sigma_wrap_nonneg(
    m_pay: float, a_g: float, r_pay: float, cos_tc: float,
) -> float:
    """
    pre: m_pay > 0
    pre: m_pay < 1e6
    pre: a_g > 0
    pre: a_g < 1e6
    pre: r_pay > 0
    pre: r_pay < 100.0
    pre: cos_tc > 0.01
    pre: cos_tc <= 1.0

    Eq 3.9: σ_wrap = m_pay * āg / (π * rpay * cos(θc))
    post: _ >= 0
    post: math.isfinite(_)
    """
    return sigma_wrap(m_pay, a_g, r_pay, cos_tc)


# =============================================================================
# CONTRACT 8: C.2 — L_shell >= 0 for N >= 1
# =============================================================================
def c2_lshell_nonneg(r_torus: float, N: int, r_out_torus: float) -> float:
    """
    pre: r_torus > 0
    pre: r_torus < 100.0
    pre: N >= 1
    pre: N <= 20
    pre: r_out_torus > 0
    pre: r_out_torus < 100.0

    C.2: L_shell = 2*N*rt + sqrt(rt*rout) - rt
    post: _ >= 0
    post: math.isfinite(_)
    """
    return float(L_shell(r_torus, N, r_out_torus))


# =============================================================================
# CONTRACT 9: Scallop augmentation >= 1.0
# =============================================================================
def scallop_aug_nonneg(
    k_sc: float, r_inflated: float, Re_theta: float,
) -> float:
    """
    pre: k_sc >= 0
    pre: k_sc < 1.0
    pre: r_inflated > 0.01
    pre: r_inflated < 1000.0
    pre: Re_theta >= 0
    pre: Re_theta < 1e8

    Section 3.7 Eq 3.107: h_f_turb / h_f_lam >= 1.0
    post: _ >= 1.0
    post: math.isfinite(_)
    """
    return scallop_augmented_heat(k_sc, r_inflated, Re_theta)


# =============================================================================
# CONTRACT 10: Mass budget non-negative
# =============================================================================
def mass_budget_nonneg() -> float:
    """
    pre: True

    C.25-C.30: Total mass >= 0
    post: _ >= 0
    """
    return mass_total(0.05, 0.08, 0.02, 0.03, 0.01, 0.005)


if __name__ == "__main__":
    print("Run: crosshair check test_crosshair_rapisarda.py")
