---
source: Official SPARTA Documentation (sparta.github.io)
library: SPARTA
package: sparta
topic: fix ave/surf averaging behavior
fetched: 2026-08-13
official_docs: https://sparta.github.io/doc/fix_ave_surf.html
---

# SPARTA `fix ave/surf` Averaging Behavior

## From Official Documentation:

> For averaging of a value that comes from a compute or fix, normalization is performed as follows. Note that no normalization is performed on a value produced by a surf-style variable.
>
> If the compute or fix is summing over particles to calculate a per-surf quantity (e.g. pressure or energy flux), this takes the form of a numerator divided by a denominator. For example, see the formulas discussed on the compute surf doc page, where the denominator is 1 (for keyword n), area times dt (timestep) for the other quantities (press, shx, ke, etc). When this command averages over a series of timesteps, the numerator and denominator are summed separately. This means the numerator/denominator division only takes place when this fix produces output, every Nfreq timesteps.

## For Force (fx, fy, fz):

The force formula is:
```
Fx = - Sum(p_delta_x) / (dt / fnum)
```

This is equivalent to:
- Numerator: Sum of momentum changes (p_delta_x)
- Denominator: dt / fnum

When `fix ave/surf` averages:
- The numerator (sum of p_delta_x) is accumulated over Nrepeat timesteps
- The denominator (dt/fnum) is applied at output time
- Result: Time-averaged force in force units [N]

**The force values from `fix ave/surf` are still in force units [N], NOT force per unit area.**

## Example Usage:

```sparta
compute 1 surf all all fx fy
fix 1 ave/surf all 10 100 1000 c_1[*]
compute 2 reduce sum f_1[1] f_1[2]
stats 1000
stats_style step cpu np c_2[1] c_2[2]
```

This computes:
1. `compute 1` — per-surface-element fx and fy forces
2. `fix 1` — time-averages these forces over 100 timesteps (10 repeats × every 10 steps)
3. `compute 2` — sums across all surface elements to get total drag (fx) and lift (fy)
4. Output — total drag and lift forces in force units

## Key Points:

1. **Force values are time-averaged**, not spatially averaged
2. **The averaging preserves force units** — no division by area
3. **To get total force**, use `compute reduce sum` to sum across surface elements
4. **The force is per 2D slice** in dimension 2 — multiply by 2πy for axisymmetric 3D
