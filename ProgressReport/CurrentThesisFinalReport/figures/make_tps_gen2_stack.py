#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).with_name("tps_gen2_stack.png")

layers = [
    ("Nicalon SiC", 0.506, "#b8b0a4", "outer fabric"),
    ("Nicalon SiC", 0.506, "#b8b0a4", "outer fabric"),
    ("Pyrogel 3350", 3.047, "#e7dcc5", "insulation"),
    ("Pyrogel 3350", 3.047, "#e7dcc5", "insulation"),
    ("Kapton", 0.025, "#d9b65a", "gas barrier"),
]
total = sum(thickness for _, thickness, _, _ in layers)

font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 26)
small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 30)

W, H = 1600, 820
margin, title_h = 90, 70
band_top = 210
band_height = 340
left, right = 110, 100
width_avail = W - left - right

# Scale the two main families numerically and make the Kapton strip wide
# enough to be visible; its actual thickness is given by the callout.
display = [max(t * 118, 58.0) for _, t, _, _ in layers]
scale = width_avail / sum(display)
xs = [left]
for t in display:
    xs.append(xs[-1] + t * scale)
# Actual positions are computed from cumulative true thickness below.
true_x = [0.0]
for _, t, _, _ in layers:
    true_x.append(true_x[-1] + t)
true_x = [(p / total) * width_avail + left for p in true_x]

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)
draw.text((W // 2, 38), "Second-generation flexible TPS stack used in this work",
          font=title, fill="#202020", anchor="mm")
draw.text((W // 2, 74), "5 plies, 7.131 mm total; outer hot face on the left, cold face on the right",
          font=small, fill="#404040", anchor="mm")

for i, (name, thickness, color, role) in enumerate(layers):
    x0 = xs[i]
    x1 = xs[i + 1]
    frac = thickness / total * 100.0
    bbox = (x0, band_top, x1, band_top + band_height)
    draw.rectangle(bbox, fill=color, outline="#202020", width=2)
    if name != "Kapton":
        draw.text(((x0+x1)/2, band_top + band_height/2), f"{name}\n{thickness:.3f} mm\n{frac:.2f} % of stack",
                  font=font, fill="#111111", anchor="mm", align="center")
    else:
        draw.text(((x0+x1)/2, band_top + band_height/2), "Kapton\ngas barrier", font=small,
                  fill="#111111", anchor="mm", align="center")
        draw.text((x0 + 30, band_top - 24), f"{thickness:.3f} mm\n({frac:.2f}% of total)", font=small,
                  fill="#111111", anchor="lm")
        draw.line([(x0 + x1) / 2, band_top - 4, (x0 + x1)/2, band_top - 18], fill="#444444", width=1)

# hot/cold face labels
draw.text((xs[0] - 12, band_top + band_height/2), "hot\nface", font=small, fill="#b00000",
          anchor="rm", align="center")
draw.text((xs[-1] + 12, band_top + band_height/2), "cold\nface", font=small, fill="#1f4fa3",
          anchor="lm", align="center")

# total dimension line
ydim = band_top + band_height + 30
draw.line([(xs[0], ydim), (xs[-1], ydim)], fill="#202020", width=2)
arrow = 8
for xtick in (xs[0], xs[-1]):
    draw.line([(xtick, ydim), (xtick, ydim-arrow)], fill="#202020", width=2)
draw.text(((xs[0]+xs[-1])/2, ydim + 12), "Total stack thickness 7.131 mm (not drawn to scale for the Kapton barrier)",
          font=small, fill="#404040", anchor="mt")
draw.text(((xs[0]+xs[-1])/2, ydim + 42), "Series resistance R = 0.305583 m^2 K/W; outer emissivity epsilon = 0.80",
          font=small, fill="#404040", anchor="mt")

# ply index / bracket marks below each true-width block
for i in range(5):
    xleft = xs[i]
    xright = xs[i+1]
    draw.text(((xleft+xright)/2, band_top + band_height + 12), str(i+1), font=small, fill="#202020", anchor="mt")

# bottom legend
y_legend = H - 76
labels_legend = ["1 Nicalon SiC 0.506 mm", "2 Nicalon SiC 0.506 mm", "3 Pyrogel 3350 3.047 mm",
                 "4 Pyrogel 3350 3.047 mm", "5 Kapton gas barrier 0.025 mm"]
draw.text((120, y_legend - 8), "Ply from hot to cold: " + " | ".join(labels_legend),
          font=small, fill="#202020")
draw.text((120, y_legend + 22), "Source: Gen-2 IRVE-3 schedule used in this work (ada_pinn wrapper / validation pipeline); generated for this thesis.",
          font=small, fill="#555555")
img.save(OUT)
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
