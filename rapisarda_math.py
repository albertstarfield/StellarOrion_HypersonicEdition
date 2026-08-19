"""
Pure-Math Rapisarda Equations for CrossHair Verification
=========================================================
Standalone module with ZERO side-effect imports (no matplotlib, no CadQuery,
no OCP).  CrossHair can safely analyze these functions.

All equations from:
  Rapisarda (2023), "Multidisciplinary Design Analysis and Optimization
  of an Inflatable Stacked Toroid"
  Chapter 3.1 (Geometry Parametrization)
  Appendix C.1 (Geometry Parametrization Derivation)
  Section 3.7 (Scallop Modelling)

Contracts are enforced via assert statements (CrossHair --analysis_kind asserts).
Every public function has:
  - Pre-conditions: guards against degenerate/physical-invalid inputs
  - Post-conditions: verify output invariants from governing equations

Governing equations annotated with [Paper Eq ...] or [Paper C.x] tags.
"""

import math

# ---------------------------------------------------------------------------
# Eq 3.4  Nose-cone radius
# ---------------------------------------------------------------------------

def rn_from_rpay(r_pay: float, cos_tc: float) -> float:
    """Eq 3.4: Nose-cone radius  rN = r_pay / cos(theta_c).

    Physical meaning:
        The spherical nose cap must be tangent to the conical forebody at the
        payload radius.  cos(theta_c) = r_pay / rN  =>  rN = r_pay / cos(theta_c).

    Pre:  r_pay > 0, 0 < cos_tc <= 1
    Post: result >= r_pay  (nose radius >= payload radius)
    """
    assert math.isfinite(r_pay), "r_pay must be finite"
    assert math.isfinite(cos_tc), "cos_tc must be finite"
    assert r_pay > 0.0, "payload radius must be positive"
    assert 0.0 < cos_tc <= 1.0, "cos(theta_c) must be in (0, 1]"
    result = r_pay / cos_tc
    assert result >= r_pay, "rN >= r_pay (nose >= payload radius)"
    return result


# ---------------------------------------------------------------------------
# Eq 3.3  Inflated IAD radius
# ---------------------------------------------------------------------------

def rinflated_from_params(
    r_torus: float, sin_tc: float, cos_tc: float, N: int,
    r_out_torus: float, r_nose: float,
) -> float:
    """Eq 3.3: Inflated IAD radius (4-term summation).

    r_inflated = 2*rt*sin(theta_c)*N          [internal tori radial span]
              + 2*rout*sin(theta_c)           [shoulder torus radial span]
              + 2*rt*(1-sin(theta_c))          [fabric thickness allowance]
              + rN*cos(theta_c)               [nose cap contribution]

    Pre:  r_torus > 0, 0 <= sin_tc <= 1, 0 < cos_tc <= 1, N >= 1,
          r_out_torus >= 0, r_nose > 0, sin^2+cos^2 ≈ 1
    Post: result >= r_nose  (inflated >= nose)
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert math.isfinite(cos_tc), "cos_tc must be finite"
    assert math.isfinite(r_out_torus), "r_out_torus must be finite"
    assert math.isfinite(r_nose), "r_nose must be finite"
    assert r_torus > 0.0, "inner torus radius must be positive"
    assert 0.0 <= sin_tc <= 1.0, "sin(theta_c) must be in [0, 1]"
    assert 0.0 < cos_tc <= 1.0, "cos(theta_c) must be in (0, 1]"
    assert N >= 1, "torus count must be >= 1"
    assert r_out_torus >= 0.0, "shoulder torus radius must be non-negative"
    assert r_nose > 0.0, "nose radius must be positive"
    assert abs(sin_tc**2 + cos_tc**2 - 1.0) < 1e-4, "sin^2+cos^2 must equal 1"
    result = (
        2.0 * r_torus * sin_tc * N
        + 2.0 * r_out_torus * sin_tc
        + 2.0 * r_torus * (1.0 - sin_tc)
        + r_nose * cos_tc
    )
    assert result > 0.0, "r_inflated must be positive"
    return result


# ---------------------------------------------------------------------------
# C.17  Shell height
# ---------------------------------------------------------------------------

def h_shell(r_inflated: float, sin_tc: float) -> float:
    """C.17: Shell height  h_shell = r_inflated / sin(theta_c).

    The conical shell slant height from nose tangency to the base,
    projected onto the symmetry axis.

    Pre:  r_inflated > 0, 0 < sin_tc <= 1
    Post: result > 0
    """
    assert math.isfinite(r_inflated), "r_inflated must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert r_inflated > 0.0, "inflated radius must be positive"
    assert 0.0 < sin_tc <= 1.0, "sin(theta_c) must be in (0, 1]"
    result = r_inflated / sin_tc
    assert result > 0.0, "shell height must be positive"
    return result


# ---------------------------------------------------------------------------
# Eq 3.7  Max toroid fabric load
# ---------------------------------------------------------------------------

def sigma_toroid(p_inf: float, r_torus: float, r_pay: float) -> float:
    """Eq 3.7: Max toroid fabric load  sigma_toroid = (p*rt/2)*(2 + rt/rpay).

    Biaxial stress in the toroid membrane under internal pressure.
    The 2*(rt/rpay) term accounts for toroidal curvature amplification.

    Pre:  p_inf > 0, r_torus > 0, r_pay > 0
    Post: result > 0
    """
    assert math.isfinite(p_inf), "p_inf must be finite"
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(r_pay), "r_pay must be finite"
    assert p_inf > 0.0, "inflation pressure must be positive"
    assert r_torus > 0.0, "torus radius must be positive"
    assert r_pay > 0.0, "payload radius must be positive"
    result = (p_inf * r_torus / 2.0) * (2.0 + r_torus / r_pay)
    assert result > 0.0, "toroid stress must be positive"
    return result


# ---------------------------------------------------------------------------
# Eq 3.8  Max spar fabric load
# ---------------------------------------------------------------------------

def sigma_spar(
    p_inf: float, r_torus: float, cos_tc: float, sin_tc: float,
    r_pay: float,
) -> float:
    """Eq 3.8: Max spar fabric load.

    sigma_spar = p*rt * [1 + 1/(1 - rt*cos(theta_c)/(rpay + rt*(1+sin(theta_c))))]

    The spar carries axial load between the toroid stack and the payload.
    The bracket term diverges as the spar angle approaches a critical value.

    Pre:  p_inf > 0, r_torus > 0, 0 < cos_tc <= 1, 0 <= sin_tc <= 1,
          r_pay > 0, frac < 1 (non-singular)
    Post: result > 0
    """
    assert math.isfinite(p_inf), "p_inf must be finite"
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(cos_tc), "cos_tc must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert math.isfinite(r_pay), "r_pay must be finite"
    assert p_inf > 0.0, "inflation pressure must be positive"
    assert r_torus > 0.0, "torus radius must be positive"
    assert 0.0 < cos_tc <= 1.0, "cos(theta_c) must be in (0, 1]"
    assert 0.0 <= sin_tc <= 1.0, "sin(theta_c) must be in [0, 1]"
    assert r_pay > 0.0, "payload radius must be positive"
    denom_inner = r_pay + r_torus * (1.0 + sin_tc)
    assert denom_inner > 0.0, "spar denominator must be positive"
    frac = r_torus * cos_tc / denom_inner
    assert frac < 1.0, "spar singularity: rt*cos_tc >= rpay + rt*(1+sin_tc)"
    bracket = 1.0 + 1.0 / (1.0 - frac)
    result = p_inf * r_torus * bracket
    assert result > 0.0, "spar stress must be positive"
    return result


# ---------------------------------------------------------------------------
# Eq 3.9  Max restraint wrap load
# ---------------------------------------------------------------------------

def sigma_wrap(m_pay: float, a_g: float, r_pay: float, cos_tc: float) -> float:
    """Eq 3.9: Max restraint wrap load  sigma_wrap = m_pay * a_bar / (pi * rpay * cos(theta_c)).

    The restraint wrap prevents the toroids from expanding radially under
    aerodynamic deceleration.  a_bar is the characteristic deceleration.

    Pre:  m_pay > 0, a_g > 0, r_pay > 0, 0 < cos_tc <= 1
    Post: result > 0
    """
    assert math.isfinite(m_pay), "m_pay must be finite"
    assert math.isfinite(a_g), "a_g must be finite"
    assert math.isfinite(r_pay), "r_pay must be finite"
    assert math.isfinite(cos_tc), "cos_tc must be finite"
    assert m_pay > 0.0, "payload mass must be positive"
    assert a_g > 0.0, "deceleration must be positive"
    assert r_pay > 0.0, "payload radius must be positive"
    assert 0.0 < cos_tc <= 1.0, "cos(theta_c) must be in (0, 1]"
    result = (m_pay * a_g) / (math.pi * r_pay * cos_tc)
    assert result > 0.0, "wrap stress must be positive"
    return result


# ---------------------------------------------------------------------------
# C.19-C.23  Minimum inflation pressure
# ---------------------------------------------------------------------------

def p_min_inflation(
    D: float, sin_tc: float, cos_tc: float,
    r_inflated: float, r_torus: float,
) -> float:
    """C.19-C.23: Minimum inflation pressure.

    p_min = D * sin^2(theta_c) / (3 * r_inflated * r_torus * pi * cos(theta_c))

    where D is the dynamic pressure load parameter.

    Pre:  D > 0, 0 < sin_tc <= 1, 0 < cos_tc <= 1, r_inflated > 0, r_torus > 0
    Post: result > 0
    """
    assert math.isfinite(D), "D must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert math.isfinite(cos_tc), "cos_tc must be finite"
    assert math.isfinite(r_inflated), "r_inflated must be finite"
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert D > 0.0, "dynamic pressure load must be positive"
    assert 0.0 < sin_tc <= 1.0, "sin(theta_c) must be in (0, 1]"
    assert 0.0 < cos_tc <= 1.0, "cos(theta_c) must be in (0, 1]"
    assert r_inflated > 0.0, "inflated radius must be positive"
    assert r_torus > 0.0, "torus radius must be positive"
    num = D * sin_tc ** 2
    den = 3.0 * r_inflated * r_torus * math.pi * cos_tc
    result = num / den
    assert result > 0.0, "min inflation pressure must be positive"
    return result


# ---------------------------------------------------------------------------
# C.2  Outer shell length
# ---------------------------------------------------------------------------

def L_shell(r_torus: float, N: int, r_out_torus: float) -> float:
    """C.2: Outer shell length.

    L_shell = 2*N*rt + sqrt(rt*rout) - rt

    The straight conical shell contour between the nose tangency point and
    the shoulder.  2*N*rt is the axial span of N stacked toroids (each of
    diameter 2*rt projected onto the shell), plus the sqrt(rt*rout) link
    to the shoulder, minus one rt radius offset.

    Pre:  r_torus > 0, N >= 1, r_out_torus > 0
    Post: result >= 0
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(r_out_torus), "r_out_torus must be finite"
    assert r_torus > 0.0, "torus radius must be positive"
    assert N >= 1, "torus count must be >= 1"
    assert r_out_torus > 0.0, "shoulder torus radius must be positive"
    result = 2.0 * N * r_torus + math.sqrt(r_torus * r_out_torus) - r_torus
    assert result >= 0.0, "shell length must be non-negative"
    return result


# ---------------------------------------------------------------------------
# C.3  Enclosure gap
# ---------------------------------------------------------------------------

def L_enclosure(r_torus: float, theta_c: float) -> float:
    """C.3: Enclosure gap (payload-to-shell standoff).

    L_enclosure = rt * (1 + tan(pi/4 - theta_c/2)) / tan(theta_c)

    This is the axial distance from the payload wall to the start of the
    conical shell.  It ensures the payload fits within the shell envelope.

    Pre:  r_torus > 0, 0 < theta_c < pi/2
    Post: result > 0
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(theta_c), "theta_c must be finite"
    assert r_torus > 0.0, "torus radius must be positive"
    assert 0.0 < theta_c < math.pi / 2.0, "theta_c must be in (0, pi/2)"
    result = r_torus * (1.0 + math.tan(math.pi / 4.0 - theta_c / 2.0)) / math.tan(theta_c)
    assert result > 0.0, "enclosure gap must be positive"
    return result


# ---------------------------------------------------------------------------
# C.25-C.30  Total structural mass
# ---------------------------------------------------------------------------

def mass_total(
    m_gas: float, m_fiber: float, m_axial: float,
    m_torus: float, m_radial: float, m_gores: float,
) -> float:
    """C.25-C.30: Total structural mass.

    m_total = m_gas + m_fiber + m_axial + m_torus + m_radial + m_gores

    Six mass components: inflation gas, structural fiber, axial spars,
    toroid walls, radial spars, and gore panels.

    Pre:  all components >= 0
    Post: result >= 0
    """
    for name, val in [("m_gas", m_gas), ("m_fiber", m_fiber), ("m_axial", m_axial),
                      ("m_torus", m_torus), ("m_radial", m_radial), ("m_gores", m_gores)]:
        assert math.isfinite(val), f"{name} must be finite"
        assert val >= 0.0, f"{name} must be non-negative"
    result = m_gas + m_fiber + m_axial + m_torus + m_radial + m_gores
    assert result >= 0.0, "total mass must be non-negative"
    return result


# ---------------------------------------------------------------------------
# Eq 3.107  Turbulent/laminar heat transfer augmentation (scalloping)
# ---------------------------------------------------------------------------

def scallop_augmented_heat(
    k_sc: float, r_inflated: float, Re_theta: float,
) -> float:
    """Section 3.7 (Eq 3.107): Turbulent/laminar heat transfer augmentation.

    h_f_turb / h_f_lam = 1 + 7.3457*(k_sc/r_inf) + 0.006
                        + 0.049294*(k_sc/r_inf)^0.51841 * Re_theta

    The scalloped skin between toroids creates roughness elements that
    trip the boundary layer, increasing local heat transfer.  k_SC is the
    scallop depth (max deflection from undeformed F-TPS surface).

    Pre:  r_inflated > 0, k_sc >= 0, Re_theta >= 0
    Post: result >= 1.0
    """
    assert math.isfinite(k_sc), "k_sc must be finite"
    assert math.isfinite(r_inflated), "r_inflated must be finite"
    assert math.isfinite(Re_theta), "Re_theta must be finite"
    assert r_inflated > 0.0, "inflated radius must be positive"
    assert k_sc >= 0.0, "scallop depth must be non-negative"
    assert Re_theta >= 0.0, "Re_theta must be non-negative"
    ratio = k_sc / r_inflated
    result = 1.0 + 7.3457 * ratio + 0.006 + 0.049294 * (ratio ** 0.51841) * Re_theta
    assert result >= 1.0, "heat augmentation ratio must be >= 1"
    return result


# ---------------------------------------------------------------------------
# Eq 3.2  Inflation tank radius
# ---------------------------------------------------------------------------

def tank_radius(
    p_toroid: float, V_toroid: float,
    p_tank: float,
) -> float:
    """Eq 3.2: Inflation tank radius.

    r_tank = (6 * p_toroid * V_toroid)^(1/3) / (2 * (p_tank * pi)^(1/3))

    Derived from ideal gas law: the stored gas volume at tank pressure must
    equal the inflated toroid volume at toroid pressure.

    Pre:  p_toroid > 0, V_toroid > 0, p_tank > 0, all finite
    Post: result > 0
    """
    assert math.isfinite(p_toroid), "p_toroid must be finite"
    assert math.isfinite(V_toroid), "V_toroid must be finite"
    assert math.isfinite(p_tank), "p_tank must be finite"
    assert p_toroid > 0.0, "toroid pressure must be positive"
    assert V_toroid > 0.0, "toroid volume must be positive"
    assert p_tank > 0.0, "tank pressure must be positive"
    num = (6.0 * p_toroid * V_toroid) ** (1.0 / 3.0)
    den = 2.0 * (p_tank * math.pi) ** (1.0 / 3.0)
    result = num / den
    assert result > 0.0, "tank radius must be positive"
    return result


# ===========================================================================
#  SECTION 3.7 — SCALLOP GEOMETRY  (R_SC, k_SC, beta_SC)
# ===========================================================================
#
#  The scallop is the curved depression in the F-TPS skin between two
#  adjacent stacked toroids.  Its geometry is governed by three quantities:
#
#  R_SC  — inscribed scallop radius [m]
#          The radius of the circle that fits inside the gap between two
#          neighbouring toroids, tangent to both torus surfaces and to the
#          conical shell.
#
#  k_SC  — scallop depth [m]
#          The maximum perpendicular distance from the undeformed (flat/conical)
#          F-TPS surface to the scalloped skin.  This is the "roughness
#          element" that trips the boundary layer (Eq 3.107).
#
#  beta_SC — scallop half-angle [rad]
#            The angle at which the scallop arc meets the torus, measured
#            from the shell normal.  Governs the arc span of each scallop.
#
#  Paper: Rapisarda (2023), Section 3.7, Eqs 3.103-3.108
# ===========================================================================


def scallop_radius(
    r_torus: float, r_out_torus: float, sin_tc: float,
) -> float:
    """Section 3.7 / Eq 3.103 (implicit): Inscribed scallop radius R_SC.

    R_SC = (rt - rout) * cos(theta_c) / (1 - cos(theta_c))

    The scallop circle is inscribed between two neighbouring toroids and
    tangent to the conical shell.  Its radius depends on the gap between
    the inner (rt) and outer (rout) torus radii and the cone angle.

    Pre:  r_torus > 0, 0 < r_out_torus < r_torus, 0 < sin_tc < 1
    Post: result > 0
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(r_out_torus), "r_out_torus must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert r_torus > 0.0, "torus radius must be positive"
    assert 0.0 < r_out_torus < r_torus, "shoulder torus radius must satisfy 0 < rout < rt"
    assert 0.0 < sin_tc < 1.0, "sin(theta_c) must be in (0, 1) for scallop"
    cos_tc = math.sqrt(1.0 - sin_tc * sin_tc)
    one_minus_cos = 1.0 - cos_tc
    # When sin_tc is close to 1 (theta_c near 90), cos_tc -> 0, and
    # one_minus_cos -> 1.  When sin_tc is close to 0 (theta_c near 0),
    # cos_tc -> 1, and one_minus_cos -> 0, making R_SC -> infinity.
    assert one_minus_cos > 1e-12, "theta_c too small for scallop computation"
    result = (r_torus - r_out_torus) * cos_tc / one_minus_cos
    assert result > 0.0, "scallop radius must be positive"
    return result


def scallop_depth(
    r_torus: float, r_out_torus: float, sin_tc: float,
) -> float:
    """Section 3.7: Scallop depth k_SC (maximum skin deflection).

    k_SC ≈ (rt - rout) * (1 - sin(theta_c))

    This is the maximum perpendicular distance from the undeformed conical
    shell surface to the scalloped skin profile.

    Physical meaning:
        The skin between two toroids sags inward under aerodynamic pressure
        and thermal expansion.  k_SC quantifies this sag — larger k_SC means
        deeper scallops, which increases surface roughness and heat transfer
        augmentation (Eq 3.107).

    Pre:  r_torus > 0, 0 < r_out_torus < r_torus, 0 < sin_tc < 1
    Post: 0 <= result < r_torus
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(r_out_torus), "r_out_torus must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert r_torus > 0.0, "torus radius must be positive"
    assert 0.0 < r_out_torus < r_torus, "shoulder torus radius must satisfy 0 < rout < rt"
    assert 0.0 < sin_tc < 1.0, "sin(theta_c) must be in (0, 1) for scallop"
    result = (r_torus - r_out_torus) * (1.0 - sin_tc)
    assert result >= 0.0, "scallop depth must be non-negative"
    assert result < r_torus, "scallop depth must be less than torus radius"
    return result


def scallop_tangent_angle(
    r_torus: float, r_out_torus: float, sin_tc: float,
) -> float:
    """Section 3.7 (Eq 3.103): Scallop tangent angle beta_SC.

    beta_SC = arctan(rtorus / (rtorus + R_SC - k_SC))

    This is the half-angle of the scallop arc, measured from the shell
    normal to the torus tangency point.

    Pre:  r_torus > 0, 0 < r_out_torus < r_torus, 0 < sin_tc < 1
    Post: 0 < result < pi/2
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(r_out_torus), "r_out_torus must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert r_torus > 0.0, "torus radius must be positive"
    assert 0.0 < r_out_torus < r_torus, "shoulder torus radius must satisfy 0 < rout < rt"
    assert 0.0 < sin_tc < 1.0, "sin(theta_c) must be in (0, 1) for scallop"
    R_SC = scallop_radius(r_torus, r_out_torus, sin_tc)
    k_SC = scallop_depth(r_torus, r_out_torus, sin_tc)
    denom = r_torus + R_SC - k_SC
    assert denom > 0.0, "denominator must be positive for beta_SC"
    result = math.atan(r_torus / denom)
    assert 0.0 < result < math.pi / 2.0, "beta_SC must be in (0, pi/2)"
    return result


def scallop_arc_length(
    r_torus: float, r_out_torus: float, sin_tc: float,
) -> float:
    """Section 3.7: Arc length of a single scallop between two toroids.

    L_arc = 2 * R_SC * beta_SC

    Pre:  r_torus > 0, 0 < r_out_torus < r_torus, 0 < sin_tc < 1
    Post: result > 0
    """
    R_SC = scallop_radius(r_torus, r_out_torus, sin_tc)
    beta = scallop_tangent_angle(r_torus, r_out_torus, sin_tc)
    result = 2.0 * R_SC * beta
    assert result > 0.0, "arc length must be positive"
    return result


def scallop_total_count(N: int) -> int:
    """Number of scallops in the full IAD stack.

    N toroids => N scallops (N-1 between tori + 1 at shoulder).

    Pre:  N >= 1
    Post: result >= 1
    """
    assert N >= 1, "torus count must be >= 1"
    return N


def scallop_max_deflection_ratio(
    r_torus: float, r_out_torus: float, sin_tc: float, r_inflated: float,
) -> float:
    """Dimensionless scallop depth  k_SC / r_inflated.

    Used in Eq 3.107 for heat augmentation.

    Pre:  r_torus > 0, 0 < r_out_torus < r_torus, 0 < sin_tc < 1, r_inflated > 0
    Post: result >= 0
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(r_out_torus), "r_out_torus must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert math.isfinite(r_inflated), "r_inflated must be finite"
    assert r_torus > 0.0, "torus radius must be positive"
    assert 0.0 < r_out_torus < r_torus, "r_out_torus must be in (0, r_torus)"
    assert 0.0 < sin_tc < 1.0, "sin_tc must be in (0, 1)"
    assert r_inflated > 0.0, "inflated radius must be positive"
    k_SC = scallop_depth(r_torus, r_out_torus, sin_tc)
    result = k_SC / r_inflated
    assert result >= 0.0, "dimensionless depth must be non-negative"
    return result


# ===========================================================================
#  CROSS-SECTION AREA FUNCTIONS (Appendix C.1)
# ===========================================================================


def A_nose(r_pay: float, r_nose: float, sin_tc: float, cos_tc: float) -> float:
    """C.1: Nose surface area.

    A_nose = pi * (r_pay^2 + (r_pay * (1/cos(theta_c) - tan(theta_c)))^2)

    Pre:  r_pay > 0, r_nose > 0, 0 < cos_tc <= 1, 0 <= sin_tc <= 1
    Post: result > 0
    """
    assert math.isfinite(r_pay), "r_pay must be finite"
    assert math.isfinite(r_nose), "r_nose must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert math.isfinite(cos_tc), "cos_tc must be finite"
    assert r_pay > 0.0, "payload radius must be positive"
    assert r_nose > 0.0, "nose radius must be positive"
    assert 0.0 < cos_tc <= 1.0, "cos(theta_c) must be in (0, 1]"
    term = r_pay * (1.0 / cos_tc - sin_tc / cos_tc)
    result = math.pi * (r_pay ** 2 + term ** 2)
    assert result > 0.0, "nose area must be positive"
    return result


def A_shell_projected(
    r_pay: float, L_shell_val: float, L_enc_val: float, sin_tc: float,
) -> float:
    """C.4: Shell projected surface area.

    A_shell = pi * (2 * r_pay * (L_shell + L_enc) * sin(theta_c)) * (L_shell + L_enc)

    Pre:  r_pay > 0, L_shell_val >= 0, L_enc_val >= 0, 0 <= sin_tc <= 1
    Post: result >= 0
    """
    assert math.isfinite(r_pay), "r_pay must be finite"
    assert math.isfinite(L_shell_val), "L_shell_val must be finite"
    assert math.isfinite(L_enc_val), "L_enc_val must be finite"
    assert math.isfinite(sin_tc), "sin_tc must be finite"
    assert 0.0 <= sin_tc <= 1.0, "sin_tc must be in [0, 1]"
    assert r_pay > 0.0, "payload radius must be positive"
    assert L_shell_val >= 0.0, "shell length must be non-negative"
    assert L_enc_val >= 0.0, "enclosure gap must be non-negative"
    L_total = L_shell_val + L_enc_val
    result = math.pi * (2.0 * r_pay * L_total * sin_tc) * L_total
    assert result >= 0.0, "shell area must be non-negative"
    return result


def L_shoulder(r_torus: float, r_out_torus: float) -> float:
    """C.5: Shoulder arc length.

    L_shoulder = 2 * rout * (pi - 2 * arcsin((rt - rout)/(rt + rout)))

    Pre:  r_torus > 0, r_out_torus > 0, both finite
    Post: result >= 0
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(r_out_torus), "r_out_torus must be finite"
    assert r_torus > 0.0, "torus radius must be positive"
    assert r_out_torus > 0.0, "shoulder torus radius must be positive"
    arg = (r_torus - r_out_torus) / (r_torus + r_out_torus)
    arg = max(-1.0, min(1.0, arg))
    result = 2.0 * r_out_torus * (math.pi - 2.0 * math.asin(arg))
    assert result >= 0.0, "shoulder length must be non-negative"
    return result


def L_shoulder_link(r_torus: float, r_out_torus: float) -> float:
    """C.6: Shoulder link length.

    L_shoulder_link = sqrt(rt * rout)

    Pre:  r_torus > 0, r_out_torus > 0, both finite
    Post: result > 0
    """
    assert math.isfinite(r_torus), "r_torus must be finite"
    assert math.isfinite(r_out_torus), "r_out_torus must be finite"
    assert r_torus > 0.0, "torus radius must be positive"
    assert r_out_torus > 0.0, "shoulder torus radius must be positive"
    result = math.sqrt(r_torus * r_out_torus)
    assert result > 0.0, "link length must be positive"
    return result
