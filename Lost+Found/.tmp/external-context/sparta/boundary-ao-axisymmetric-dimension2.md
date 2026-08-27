---
source: Official SPARTA Documentation (sparta.github.io)
library: SPARTA
package: sparta
topic: boundary ao axisymmetric dimension 2
fetched: 2026-08-13
official_docs: https://sparta.github.io/doc/boundary.html
---

# SPARTA `boundary` and `dimension` Commands — Axisymmetric

## From boundary.txt:

> Style {a} means an axi-symmetric boundary, which can only be used for the lower y-dimension boundary in a 2d simulation. The simulation box must also have a value of 0.0 for {ylo}; see the "create_box" command. This effectively means that the x-axis is the axis of symmetry. The upper y-dimension boundary cannot be periodic.

### Key Points:

1. `boundary a` can ONLY be used for the **lower y-dimension** boundary
2. The simulation must be **dimension 2**
3. `ylo` must be **0.0**
4. The **x-axis is the axis of symmetry** (NOT the y-axis!)

**CORRECTION**: The documentation says "the x-axis is the axis of symmetry". This means:
- The symmetry axis is the x-axis (y=0 line)
- The y-coordinate represents the radial distance from the symmetry axis
- Particles at y=0 are on the symmetry axis

## From dimension.txt:

> Set the dimensionality of the simulation. By default SPARTA runs 3d simulations, but 2d simulations can also be run.
>
> 2d axi-symmetric models can be run by setting the dimension to 2, and defining the lower boundary in the y-dimension to axi-symmetric via the "boundary" command.

### Implications for Force Calculation:

In 2D axisymmetric mode:
- The symmetry axis is the **x-axis** (y=0)
- The **y-coordinate** is the radial distance from the symmetry axis
- Each surface element at height y represents a ring when revolved around the x-axis
- The circumference of that ring is: **2πy**

### Correct Axisymmetric Force Conversion:

```
F_3D = Sum over all surface elements of: F_2D_element * 2π * y_centroid_element
```

Where:
- `F_2D_element` = fx output from `compute surf` for element i
- `y_centroid_element` = y-coordinate of element i's centroid (radial distance from x-axis)
- The factor `2πy` accounts for the revolution around the x-axis

## Important Note:

The `ao` boundary flag:
- **Does NOT automatically apply axisymmetric weighting to forces**
- **Does affect normflux** (used for flux quantities like nflux, mflux, ke)
- **The user must manually apply 2πy weighting** to convert 2D forces to 3D axisymmetric forces
