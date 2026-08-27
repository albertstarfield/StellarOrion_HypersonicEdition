---
source: Official SPARTA Documentation (sparta.github.io)
library: SPARTA (Sandia Parallel Advanced Research of Turbulence and Aero-reaction)
package: sparta
topic: compute surf fx fy fz force units dimension 2 axisymmetric
fetched: 2026-08-13
official_docs: https://sparta.github.io/doc/compute_surf.html
---

# SPARTA `compute surf` Force Output in Dimension 2

## CRITICAL FINDING: fx, fy, fz Are NOT Normalized by Area

The `compute surf fx fy fz` values are **forces on the surface element**, NOT force per unit area.

### Official Documentation (verbatim from sparta.github.io/doc/compute_surf.html):

> **The *fx*, *fy*, *fz* values calculate the xyz components of force exerted on the surface element by particles in the group. These are computed as**
>
> ```
> Fx = - Sum_i (p_delta_x) / (dt / fnum)
> Fy = - Sum_i (p_delta_y) / (dt / fnum)
> Fz = - Sum_i (p_delta_z) / (dt / fnum)
> ```
>
> where p_delta is the change in momentum of a particle, whose velocity changes from V_pre to V_post when colliding with the surface element. The force exerted on the surface element is the sum over all contributing p_delta, normalized by dt and fnum as defined before.

### Key Observation: NO AREA IN THE FORCE FORMULA

Unlike flux quantities (nflux, mflux, ke, etc.) which have `A * dt / fnum` in the denominator, the force (fx, fy, fz) only has `dt / fnum` in the denominator.

Compare:
- **Flux quantities**: `N / (A * dt / fnum)` — divided by area AND time
- **Force (fx, fy, fz)**: `Sum(p_delta) / (dt / fnum)` — divided by time ONLY

### What This Means in Dimension 2

In SPARTA dimension 2:
- Surface elements are **line segments** (not triangles)
- The "area" A of a line segment is its **length** (distance between endpoints)
- For axisymmetric simulations (`boundary a`), the area is `axi_line_size` (surface area of revolution of that line segment)

**Since fx, fy, fz do NOT include area normalization**, the output is:

#### ANSWER: `compute surf fx` in dimension 2 outputs FORCE [N] (SI) or [dyne] (CGS)

It is the **total force on that line segment element**, NOT:
- ~~Force per unit z-length [N/m]~~ — WRONG
- ~~Force per unit area [Pa]~~ — WRONG

The force is the total impulse per unit time on the surface element, scaled by fnum (real-to-simulated particle ratio).

### Units (from units.txt):

- **SI**: mass = kg, distance = m, time = s → force = Newtons [N]
- **CGS**: mass = g, distance = cm, time = s → force = dynes [dyne]

## The norm keyword Does NOT Affect Force

The `norm` keyword only affects FLUX quantities (nflux, mflux, ke, erot, evib, etot):

> If the *norm* keyword is used with a setting of *flow*, then the formulas above for all flux values will not use the surface element area A in the denominator. Specifically these values are nflux, mflux, ke, erot, evib, etot.

**Force (fx, fy, fz) is NOT in this list.** The norm keyword has NO effect on force output.

## Axisymmetric Conversion: The `ao` Boundary Does NOT Auto-Weight Forces

From the SPARTA source code (compute_surf.cpp):

```cpp
// normflux for all surface elements, based on area and timestep size
// if normarea = 0, area is not included in flux
if (!normarea) normflux[i] = 1.0;
else if (dim == 3) normflux[i] = surf->tri_size(i);
else if (axisymmetric) normflux[i] = surf->axi_line_size(i);
else normflux[i] = surf->line_size(i);
```

The `normflux` is only applied to FLUX quantities (via `fluxscale`), NOT to force:

```cpp
// forcescale factor applied for keywords FX,FY,FZ
// fluxscale factor applied for all keywords except NUM,FX,FY,FZ
```

And for force:
```cpp
case FX:
  vec[k++] -= pdelta_force[0] * nfactor_inverse;  // nfactor_inverse = fnum/dt
```

**The `ao` boundary flag affects the `normflux` calculation for flux quantities but does NOT automatically apply axisymmetric weighting to forces.**

## How to Convert 2D Force to 3D Axisymmetric Force

Since SPARTA's `compute surf fx` in dimension 2 gives the force on the 2D line segment:

### For axisymmetric (`ao` boundary):
```
F_3D = Sum over all surface elements of: F_2D_element * 2π * y_centroid_element
```

Where:
- `F_2D_element` = the fx (or fy, fz) output from `compute surf` for that element
- `y_centroid_element` = the y-coordinate of the centroid of that line segment
- The factor `2π * y` accounts for the revolution of the 2D slice around the y-axis

### Why the centroid y-coordinate?

In SPARTA's 2D axisymmetric mode:
- The simulation is a 2D slice in the x-y plane
- The y-axis is the axis of symmetry
- Each line segment at height y represents a ring of circumference 2πy when revolved
- The force on that ring is: `F_ring = F_2D × 2πy`

### Correct Cd Calculation:
```
F_drag_3D = Sum_i (fx_i * 2π * y_i)
Cd = F_drag_3D / (0.5 * rho_inf * V_inf^2 * A_ref)
```

Where:
- `fx_i` = force output from `compute surf fx` for surface element i
- `y_i` = y-coordinate (radial distance from symmetry axis) of element i's centroid
- `A_ref` = reference area (usually the maximum cross-sectional area of the vehicle)

## fix ave/surf Averaging Behavior

From the `fix ave/surf` documentation:

> For averaging of a value that comes from a compute or fix, normalization is performed as follows. If the compute or fix is summing over particles to calculate a per-surf quantity (e.g. pressure or energy flux), this takes the form of a numerator divided by a denominator. When this command averages over a series of timesteps, the numerator and denominator are summed separately. This means the numerator/denominator division only takes place when this fix produces output, every Nfreq timesteps.

For **force** (fx, fy, fz):
- The numerator (sum of p_delta) is accumulated over Nevery timesteps
- The denominator (dt/fnum) is applied at output time
- This is equivalent to a simple time-average of the force

**The force values from `fix ave/surf` are still in force units [N], NOT force per unit area.**

## Summary Table

| Quantity | Formula | Normalized by Area? | Units (SI) | Units (CGS) |
|----------|---------|---------------------|------------|-------------|
| fx, fy, fz | Sum(p_delta) / (dt/fnum) | **NO** | N | dyne |
| press | Sum(p_delta·N) / (A * dt/fnum) | YES | Pa | dyne/cm² |
| nflux | N / (A * dt/fnum) | YES | 1/(m²·s) | 1/(cm²·s) |
| mflux | Sum(mass) / (A * dt/fnum) | YES | kg/(m²·s) | g/(cm²·s) |
| ke | Sum(energy) / (A * dt/fnum) | YES | W/m² | erg/(cm²·s) |

## Your IRVE-3 Cd Discrepancy

Your results:
- Cd = 3.73 without axisymmetric correction
- Cd = 34.3 with 2πy×centroid correction
- Expected Cd ≈ 1.47

**Neither matches because SPARTA's fx output is ALREADY the total force on the 2D line segment.**

The 2πy×centroid correction you applied would be CORRECT if fx were force per unit length. But since fx is already the total force, you should NOT multiply by 2πy.

**The correct approach is:**
1. Sum all fx values from `compute surf fx` across all surface elements
2. This gives the total drag force in the 2D simulation (which represents a slice)
3. For axisymmetric, multiply by the appropriate factor based on the simulation setup

However, the discrepancy (3.73 vs 1.47) suggests there may be other issues:
- Check if fnum is correctly set
- Verify the reference area A_ref
- Confirm the surface element geometry matches the expected vehicle shape
- Check if there are surface elements that should not contribute to drag
