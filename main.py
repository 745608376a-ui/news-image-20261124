#!/usr/bin/env python3
"""The World in One Picture - Tuesday 24 November 2026.

Renders a one-page news infographic entirely in code and writes it to
/output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png outside the grader).

Pure Python standard library: the PNG is encoded with zlib/struct and every
shape and letter is rasterised by hand, so the program runs in the grader's
bare Python 3.13 container, uses no network, reads no files, and produces
byte-identical output on every run.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (246, 241, 231)
INK = (20, 32, 46)
NAVY = (16, 36, 60)
NAVY2 = (24, 52, 84)
WHITE = (255, 255, 255)
CARD = (255, 253, 246)
CARD_LINE = (216, 208, 190)
GREY = (96, 106, 118)
GOLD = (217, 164, 65)
RED = (200, 53, 43)
TEAL = (31, 122, 109)
BLUE = (43, 96, 160)
PURPLE = (106, 76, 160)
ORANGE = (214, 116, 40)
SKY = (120, 178, 220)

# ---------------------------------------------------------------- canvas
px = bytearray(W * H * 3)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i] = color[0]
        px[i + 1] = color[1]
        px[i + 2] = color[2]


def fill_rect(x0, y0, x1, y1, color):
    x0 = max(0, int(x0)); y0 = max(0, int(y0))
    x1 = min(W, int(x1)); y1 = min(H, int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(color) * (x1 - x0)
    for y in range(y0, y1):
        i = (y * W + x0) * 3
        px[i:i + len(row)] = row


def stamp(cx, cy, r, color):
    """Filled circle used as a round pen nib."""
    r = int(math.ceil(r))
    rr = r * r
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= rr:
                set_px(int(cx + dx), int(cy + dy), color)


def line(x0, y0, x1, y1, color, wdt=3):
    steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    r = wdt / 2.0
    for i in range(steps + 1):
        t = i / steps
        stamp(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, color)


def poly(points, color, wdt=3, close=False):
    pts = list(points)
    if close and pts:
        pts.append(pts[0])
    for a, b in zip(pts, pts[1:]):
        line(a[0], a[1], b[0], b[1], color, wdt)


def fill_circle(cx, cy, r, color):
    stamp(cx, cy, r, color)


def ring(cx, cy, r, color, wdt=4):
    steps = int(2 * math.pi * r) + 8
    for i in range(steps):
        a = 2 * math.pi * i / steps
        stamp(cx + r * math.cos(a), cy + r * math.sin(a), wdt / 2.0, color)


def fill_poly(points, color):
    ys = [p[1] for p in points]
    y0, y1 = int(min(ys)), int(max(ys))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            ax, ay = points[i]
            bx, by = points[(i + 1) % n]
            if (ay <= y < by) or (by <= y < ay):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            fill_rect(int(xs[i]), y, int(xs[i + 1]) + 1, y + 1, color)


def fill_ellipse(cx, cy, rx, ry, color):
    for dy in range(-int(ry), int(ry) + 1):
        dx = rx * math.sqrt(max(0.0, 1.0 - (dy / ry) ** 2)) if ry else 0
        fill_rect(int(cx - dx), int(cy + dy), int(cx + dx) + 1, int(cy + dy) + 1, color)


def rounded_rect(x0, y0, x1, y1, r, color):
    fill_rect(x0 + r, y0, x1 - r, y1, color)
    fill_rect(x0, y0 + r, x1, y1 - r, color)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        fill_circle(cx, cy, r, color)


def card(x0, y0, x1, y1, fill=CARD):
    rounded_rect(x0 + 3, y0 + 4, x1 + 3, y1 + 4, 14, (226, 219, 200))
    rounded_rect(x0, y0, x1, y1, 14, CARD_LINE)
    rounded_rect(x0 + 2, y0 + 2, x1 - 2, y1 - 2, 12, fill)

# ---------------------------------------------------------------- font
# Hand-drawn vector (stroke) font. Glyph space: x in 0..6, y in 0..9,
# y=0 is the baseline, y=9 the cap top. Each glyph is a list of strokes,
# each stroke a list of (x, y) points; a one-point stroke is a dot.
GLYPHS = {
    "A": [[(0, 0), (3, 9), (6, 0)], [(1.4, 3.4), (4.6, 3.4)]],
    "B": [[(0, 0), (0, 9)], [(0, 9), (3.4, 9), (4.8, 7.8), (4.8, 6.2), (3.4, 5.0), (0, 5.0)],
          [(3.4, 5.0), (5.0, 3.9), (5.0, 1.2), (3.4, 0), (0, 0)]],
    "C": [[(5.6, 7.4), (4.2, 8.8), (2.2, 9.0), (0.8, 7.6), (0.6, 4.5), (0.8, 1.4), (2.2, 0.1), (4.2, 0.2), (5.6, 1.6)]],
    "D": [[(0, 0), (0, 9)], [(0, 9), (3.2, 9), (5.2, 6.8), (5.2, 2.2), (3.2, 0), (0, 0)]],
    "E": [[(5.4, 9), (0, 9), (0, 0), (5.4, 0)], [(0, 4.6), (4.4, 4.6)]],
    "F": [[(0, 0), (0, 9), (5.4, 9)], [(0, 4.6), (4.2, 4.6)]],
    "G": [[(5.6, 7.4), (4.2, 8.8), (2.2, 9.0), (0.8, 7.6), (0.6, 4.5), (0.8, 1.4), (2.2, 0.1), (4.4, 0.2), (5.8, 1.2), (5.8, 3.6), (3.6, 3.6)]],
    "H": [[(0, 0), (0, 9)], [(6, 0), (6, 9)], [(0, 4.6), (6, 4.6)]],
    "I": [[(3, 0), (3, 9)], [(1.4, 9), (4.6, 9)], [(1.4, 0), (4.6, 0)]],
    "J": [[(5.4, 9), (5.4, 1.8), (4.4, 0.2), (2.2, 0.0), (0.8, 1.2)]],
    "K": [[(0, 0), (0, 9)], [(5.6, 9), (0.8, 4.2)], [(1.8, 5.4), (6, 0)]],
    "L": [[(0, 9), (0, 0), (5.4, 0)]],
    "M": [[(0, 0), (0, 9), (3, 3.4), (6, 9), (6, 0)]],
    "N": [[(0, 0), (0, 9), (6, 0), (6, 9)]],
    "O": [[(3, 9), (4.8, 8.4), (5.8, 6.4), (5.8, 2.6), (4.8, 0.6), (3, 0), (1.2, 0.6), (0.2, 2.6), (0.2, 6.4), (1.2, 8.4), (3, 9)]],
    "P": [[(0, 0), (0, 9)], [(0, 9), (3.8, 9), (5.2, 7.6), (5.2, 5.8), (3.8, 4.6), (0, 4.6)]],
    "Q": [[(3, 9), (4.8, 8.4), (5.8, 6.4), (5.8, 2.6), (4.8, 0.6), (3, 0), (1.2, 0.6), (0.2, 2.6), (0.2, 6.4), (1.2, 8.4), (3, 9)],
          [(3.6, 2.4), (6.2, -0.4)]],
    "R": [[(0, 0), (0, 9)], [(0, 9), (3.8, 9), (5.2, 7.6), (5.2, 5.8), (3.8, 4.6), (0, 4.6)], [(3.4, 4.6), (6, 0)]],
    "S": [[(5.4, 7.8), (3.8, 9.0), (1.8, 8.8), (0.6, 7.2), (1.0, 5.4), (3.2, 4.4), (5.0, 3.2), (5.4, 1.4), (4.0, 0.1), (1.8, 0.0), (0.4, 1.2)]],
    "T": [[(3, 0), (3, 9)], [(0, 9), (6, 9)]],
    "U": [[(0, 9), (0, 1.8), (1.2, 0.2), (3, 0), (4.8, 0.2), (6, 1.8), (6, 9)]],
    "V": [[(0, 9), (3, 0), (6, 9)]],
    "W": [[(0, 9), (1.4, 0), (3, 6.2), (4.6, 0), (6, 9)]],
    "X": [[(0, 0), (6, 9)], [(0, 9), (6, 0)]],
    "Y": [[(0, 9), (3, 4.6), (6, 9)], [(3, 4.6), (3, 0)]],
    "Z": [[(0, 9), (6, 9), (0, 0), (6, 0)]],
    "0": [[(3, 9), (4.6, 8.2), (5.2, 6.2), (5.2, 2.8), (4.6, 0.8), (3, 0), (1.4, 0.8), (0.8, 2.8), (0.8, 6.2), (1.4, 8.2), (3, 9)]],
    "1": [[(1.4, 7.2), (3.2, 9), (3.2, 0)], [(1.2, 0), (5.2, 0)]],
    "2": [[(0.6, 7.4), (1.8, 9.0), (4.0, 8.8), (5.2, 7.2), (4.8, 5.2), (0.4, 0.0), (5.6, 0.0)]],
    "3": [[(0.6, 7.8), (2.2, 9.0), (4.4, 8.4), (4.6, 6.6), (3.0, 5.2), (4.4, 4.6), (5.2, 2.6), (4.4, 0.6), (2.2, 0.0), (0.6, 1.0)]],
    "4": [[(4.2, 0), (4.2, 9), (0.4, 2.8), (6, 2.8)]],
    "5": [[(5.4, 9), (1.0, 9), (0.8, 5.6), (3.0, 6.2), (5.0, 5.0), (5.4, 2.6), (4.2, 0.4), (1.8, 0.0), (0.4, 1.0)]],
    "6": [[(5.2, 7.8), (3.6, 9.0), (1.6, 7.6), (0.6, 4.6), (0.8, 1.8), (2.4, 0.1), (4.4, 0.3), (5.4, 1.8), (5.2, 3.8), (3.8, 5.0), (1.2, 4.4)]],
    "7": [[(0.4, 9), (6, 9), (2.6, 0)]],
    "8": [[(3, 5.0), (1.6, 5.6), (0.8, 7.2), (1.4, 8.8), (3, 9.2), (4.6, 8.8), (5.2, 7.2), (4.4, 5.6), (3, 5.0),
           (1.4, 4.2), (0.6, 2.2), (1.4, 0.4), (3, 0), (4.6, 0.4), (5.4, 2.2), (4.6, 4.2), (3, 5.0)]],
    "9": [[(0.8, 1.2), (2.4, 0.0), (4.4, 1.4), (5.4, 4.4), (5.2, 7.2), (3.6, 9.0), (1.6, 8.7), (0.6, 7.0), (0.8, 5.2), (2.2, 4.0), (4.8, 4.6)]],
    ".": [[(3, 0.4)]],
    ",": [[(3.2, 0.6), (2.6, -1.2)]],
    ":": [[(3, 1.2)], [(3, 6.2)]],
    ";": [[(3, 6.2)], [(3.2, 1.0), (2.6, -1.2)]],
    "!": [[(3, 9), (3, 2.6)], [(3, 0.3)]],
    "?": [[(0.8, 7.6), (2.0, 9.0), (4.2, 8.8), (5.2, 7.4), (4.6, 5.6), (3, 4.4), (3, 2.8)], [(3, 0.3)]],
    "-": [[(1, 4.4), (5, 4.4)]],
    "\u2013": [[(0.4, 4.4), (5.6, 4.4)]],
    "\u2014": [[(0, 4.4), (6, 4.4)]],
    "'": [[(3, 9), (2.6, 7.4)]],
    "\u2019": [[(3, 9), (2.6, 7.4)]],
    '"': [[(1.8, 9), (1.4, 7.4)], [(4.2, 9), (3.8, 7.4)]],
    "(": [[(4.4, 9), (2.6, 7.0), (2.2, 4.5), (2.6, 2.0), (4.4, 0)]],
    ")": [[(1.6, 9), (3.4, 7.0), (3.8, 4.5), (3.4, 2.0), (1.6, 0)]],
    "/": [[(1, 0), (5.4, 9.4)]],
    "%": [[(0.6, 0), (5.6, 9)], [(1.6, 9), (2.6, 8), (1.6, 7), (0.6, 8), (1.6, 9)], [(4.6, 2), (5.6, 1), (4.6, 0), (3.6, 1), (4.6, 2)]],
    "+": [[(3, 1.6), (3, 7.4)], [(0.8, 4.5), (5.2, 4.5)]],
    "$": [[(5.2, 7.6), (3.6, 8.8), (1.6, 8.6), (0.6, 7.0), (1.2, 5.2), (3.4, 4.2), (5.0, 3.0), (5.2, 1.2), (3.8, 0.0), (1.6, 0.2), (0.4, 1.2)],
          [(3, 10.2), (3, -1.2)]],
    "&": [[(5.4, 0.6), (2.0, 5.8), (1.0, 7.6), (1.6, 9.0), (3.2, 8.8), (3.6, 7.4), (2.4, 5.8), (0.8, 3.4), (0.8, 1.4), (2.2, 0.0), (4.0, 0.6), (5.4, 3.0)]],
    "\u2022": [[(3, 4.5)]],
    "\u00b7": [[(3, 4.5)]],
    "*": [[(3, 1.5), (3, 7.5)], [(1, 3), (5, 6)], [(5, 3), (1, 6)]],
    "=": [[(1, 3.2), (5, 3.2)], [(1, 5.8), (5, 5.8)]],
}

ADV = {" ": 4.6, "I": 5.2, ".": 4.0, ",": 4.0, ":": 4.0, ";": 4.0, "!": 4.0,
       "'": 3.4, "\u2019": 3.4, "\u2022": 5.0, "\u00b7": 5.0}


def char_adv(ch, scale):
    return ADV.get(ch, 8.0) * scale


def text_width(s, scale):
    return sum(char_adv(c, scale) for c in s.upper())


def draw_text(x, y_base, s, scale, color, wdt):
    """Draw s with baseline at y_base; returns the x just past the text."""
    cx = x
    for ch in s.upper():
        glyph = GLYPHS.get(ch)
        if glyph:
            for stroke in glyph:
                pts = [(cx + gx * scale, y_base - gy * scale) for gx, gy in stroke]
                if len(pts) == 1:
                    stamp(pts[0][0], pts[0][1], wdt / 2.0 + 0.6, color)
                else:
                    poly(pts, color, wdt)
        cx += char_adv(ch, scale)
    return cx


def draw_text_center(cx, y_base, s, scale, color, wdt):
    return draw_text(cx - text_width(s, scale) / 2.0, y_base, s, scale, color, wdt)


def wrap(s, scale, max_w):
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        trial = wd if not cur else cur + " " + wd
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_block(x, y_top, s, scale, color, wdt, max_w, leading=13.2, align="left"):
    """Draw wrapped text; y_top is the top of the cap height of line 1.
    Returns the y just below the last line's baseline."""
    lines = wrap(s, scale, max_w)
    base = y_top + 9 * scale
    for ln in lines:
        if align == "center":
            draw_text_center(x + max_w / 2.0, base, ln, scale, color, wdt)
        else:
            draw_text(x, base, ln, scale, color, wdt)
        base += leading * scale
    return base - leading * scale

# ---------------------------------------------------------------- icons
def icon_globe(cx, cy, r, color, wdt=3.5):
    ring(cx, cy, r, color, wdt)
    for frac in (0.45, 0.82):
        rx = r * frac
        steps = 60
        prev = None
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            p = (cx + rx * math.cos(a), cy + r * math.sin(a))
            if prev:
                line(prev[0], prev[1], p[0], p[1], color, wdt * 0.8)
            prev = p
    for frac in (-0.52, 0.0, 0.52):
        dy = r * frac
        half = math.sqrt(max(1.0, r * r - dy * dy)) - 2
        line(cx - half, cy + dy, cx + half, cy + dy, color, wdt * 0.8)


def icon_chip(cx, cy, s, color, accent):
    poly([(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)], color, 6, close=True)
    for f in (-0.55, 0.0, 0.55):
        line(cx + f * s, cy - s, cx + f * s, cy - s - 0.34 * s, color, 6)
        line(cx + f * s, cy + s, cx + f * s, cy + s + 0.34 * s, color, 6)
        line(cx - s, cy + f * s, cx - s - 0.34 * s, cy + f * s, color, 6)
        line(cx + s, cy + f * s, cx + s + 0.34 * s, cy + f * s, color, 6)
    poly([(cx - 0.34 * s, cy + 0.38 * s), (cx - 0.05 * s, cy + 0.02 * s),
          (cx + 0.16 * s, cy + 0.16 * s), (cx + 0.52 * s, cy - 0.34 * s)], accent, 7)
    line(cx + 0.52 * s, cy - 0.34 * s, cx + 0.28 * s, cy - 0.36 * s, accent, 7)
    line(cx + 0.52 * s, cy - 0.34 * s, cx + 0.5 * s, cy - 0.1 * s, accent, 7)


def icon_ship(cx, cy, s, color):
    fill_poly([(cx - s, cy + 0.05 * s), (cx + s, cy + 0.05 * s),
               (cx + 0.68 * s, cy + 0.52 * s), (cx - 0.68 * s, cy + 0.52 * s)], color)
    fill_rect(cx - 0.52 * s, cy - 0.28 * s, cx + 0.05 * s, cy + 0.05 * s, color)
    fill_rect(cx + 0.18 * s, cy - 0.48 * s, cx + 0.38 * s, cy + 0.05 * s, color)
    line(cx - 0.25 * s, cy - 0.28 * s, cx - 0.25 * s, cy - 0.78 * s, color, 5)
    fill_poly([(cx - 0.25 * s, cy - 0.78 * s), (cx + 0.12 * s, cy - 0.66 * s), (cx - 0.25 * s, cy - 0.54 * s)], color)
    for k, yy in enumerate((0.7, 0.86)):
        pts = []
        for i in range(41):
            x = cx - s + 2 * s * i / 40
            pts.append((x, cy + yy * s + 0.09 * s * math.sin(i / 40 * 4 * math.pi + k * 1.7)))
        poly(pts, color, 4)


def icon_tanker(cx, cy, s, color):
    fill_poly([(cx - s, cy + 0.12 * s), (cx + s, cy + 0.12 * s),
               (cx + 0.74 * s, cy + 0.5 * s), (cx - 0.8 * s, cy + 0.5 * s)], color)
    line(cx - 0.95 * s, cy + 0.12 * s, cx + 0.95 * s, cy + 0.12 * s, color, 6)
    fill_rect(cx + 0.52 * s, cy - 0.38 * s, cx + 0.86 * s, cy + 0.12 * s, color)
    for fx in (-0.55, -0.12, 0.31):
        fill_circle(cx + fx * s, cy + 0.02 * s, 0.13 * s, color)
    mx, my = cx - 0.68 * s, cy - 0.52 * s
    ring(mx, my, 0.17 * s, color, 5)
    for i in range(8):
        a = i * math.pi / 4
        line(mx + 0.17 * s * math.cos(a), my + 0.17 * s * math.sin(a),
             mx + 0.3 * s * math.cos(a), my + 0.3 * s * math.sin(a), color, 4)


def icon_scales(cx, cy, s, color):
    line(cx, cy - 0.78 * s, cx, cy + 0.62 * s, color, 6)
    line(cx - 0.88 * s, cy - 0.78 * s, cx + 0.88 * s, cy - 0.78 * s, color, 6)
    stamp(cx, cy - 0.92 * s, 5, color)
    for side in (-1, 1):
        bx = cx + side * 0.88 * s
        line(bx, cy - 0.78 * s, bx - 0.22 * s, cy - 0.08 * s, color, 4)
        line(bx, cy - 0.78 * s, bx + 0.22 * s, cy - 0.08 * s, color, 4)
        pts = []
        for i in range(21):
            a = math.pi * i / 20
            pts.append((bx + 0.3 * s * math.cos(a), cy - 0.08 * s + 0.16 * s * math.sin(a)))
        poly(pts, color, 5)
    line(cx - 0.42 * s, cy + 0.78 * s, cx + 0.42 * s, cy + 0.78 * s, color, 7)
    line(cx - 0.2 * s, cy + 0.62 * s, cx + 0.2 * s, cy + 0.62 * s, color, 6)


def icon_robot(cx, cy, s, color, bg):
    poly([(cx - 0.8 * s, cy - 0.5 * s), (cx + 0.8 * s, cy - 0.5 * s),
          (cx + 0.8 * s, cy + 0.62 * s), (cx - 0.8 * s, cy + 0.62 * s)], color, 6, close=True)
    line(cx, cy - 0.5 * s, cx, cy - 0.88 * s, color, 5)
    stamp(cx, cy - 0.95 * s, 0.1 * s, color)
    fill_circle(cx - 0.34 * s, cy - 0.08 * s, 0.12 * s, color)
    fill_circle(cx + 0.34 * s, cy - 0.08 * s, 0.12 * s, color)
    line(cx - 0.36 * s, cy + 0.34 * s, cx + 0.36 * s, cy + 0.34 * s, color, 5)
    fill_rect(cx - 0.98 * s, cy - 0.18 * s, cx - 0.8 * s, cy + 0.22 * s, color)
    fill_rect(cx + 0.8 * s, cy - 0.18 * s, cx + 0.98 * s, cy + 0.22 * s, color)


def icon_rocket(cx, cy, s, color, accent):
    body = [(cx, cy - 0.95 * s), (cx + 0.3 * s, cy - 0.45 * s), (cx + 0.38 * s, cy + 0.05 * s),
            (cx + 0.38 * s, cy + 0.45 * s), (cx - 0.38 * s, cy + 0.45 * s),
            (cx - 0.38 * s, cy + 0.05 * s), (cx - 0.3 * s, cy - 0.45 * s)]
    poly(body, color, 5, close=True)
    ring(cx, cy - 0.22 * s, 0.15 * s, color, 4)
    fill_poly([(cx - 0.38 * s, cy + 0.15 * s), (cx - 0.78 * s, cy + 0.72 * s), (cx - 0.38 * s, cy + 0.55 * s)], color)
    fill_poly([(cx + 0.38 * s, cy + 0.15 * s), (cx + 0.78 * s, cy + 0.72 * s), (cx + 0.38 * s, cy + 0.55 * s)], color)
    fill_poly([(cx - 0.14 * s, cy + 0.55 * s), (cx + 0.14 * s, cy + 0.55 * s), (cx, cy + 0.98 * s)], accent)


def icon_flame(cx, cy, s, color, inner):
    outer = [(cx, cy - 0.95 * s), (cx + 0.3 * s, cy - 0.35 * s), (cx + 0.55 * s, cy + 0.1 * s),
             (cx + 0.45 * s, cy + 0.6 * s), (cx + 0.15 * s, cy + 0.85 * s), (cx - 0.15 * s, cy + 0.85 * s),
             (cx - 0.45 * s, cy + 0.6 * s), (cx - 0.55 * s, cy + 0.1 * s), (cx - 0.28 * s, cy - 0.3 * s)]
    fill_poly(outer, color)
    small = [(cx + (x - cx) * 0.52, cy + 0.28 * s + (y - cy) * 0.52) for x, y in outer]
    fill_poly(small, inner)


# ---------------------------------------------------------------- layout
def tag_chip(x, y, text, color, scale=1.7):
    tw = text_width(text, scale)
    rounded_rect(x, y, x + tw + 30, y + 36, 10, color)
    draw_text(x + 15, y + 28, text, scale, WHITE, 3)
    return x + tw + 30


def story_card(x0, y0, tag, tag_color, headline, body, icon):
    x1, y1 = x0 + 464, y0 + 208
    card(x0, y0, x1, y1)
    fill_circle(x0 + 58, y0 + 54, 37, tag_color)
    icon(x0 + 58, y0 + 54)
    draw_text(x0 + 112, y0 + 48, tag, 1.6, tag_color, 3.2)
    line(x0 + 112, y0 + 60, x0 + 440, y0 + 60, CARD_LINE, 3)
    draw_block(x0 + 24, y0 + 72, headline, 2.85, INK, 4.4, 416, leading=13.4)
    draw_block(x0 + 24, y0 + 142, body, 1.6, (52, 62, 74), 2.6, 416, leading=12.6)


def build():
    fill_rect(0, 0, W, H, PAPER)

    # masthead
    fill_rect(0, 0, W, 166, NAVY)
    fill_rect(0, 166, W, 172, GOLD)
    draw_text(48, 50, "THE WORLD IN ONE PICTURE", 2.1, GOLD, 3.4)
    draw_text(48, 116, "24 NOVEMBER 2026", 6.3, WHITE, 8)
    draw_text(48, 150, "TUESDAY - THE DAY'S WORLD NEWS, SUMMED UP IN A SINGLE IMAGE", 1.85, SKY, 3)
    icon_globe(930, 82, 52, SKY, 3.5)

    # lead story: Nvidia
    card(40, 190, 984, 462)
    rounded_rect(58, 206, 322, 446, 12, NAVY2)
    icon_chip(190, 276, 48, WHITE, GOLD)
    draw_text_center(190, 390, "+31%", 4.2, GOLD, 6)
    draw_text_center(190, 416, "SHARE JUMP IN ONE DAY", 1.4, WHITE, 2.6)
    draw_text_center(190, 440, "NASDAQ +6.5%", 1.4, GOLD, 2.6)
    tag_chip(348, 208, "TECH + MARKETS - UNITED STATES", RED)
    draw_block(348, 254, "NVIDIA BRINGS BACK HUANG - SHARES +31%", 4.3, INK, 6, 612, leading=13.2)
    draw_block(348, 368, "The board reinstated founder Jensen Huang as chief executive days after "
                         "his sudden exit, under pressure from President Trump.", 1.9, (52, 62, 74), 3, 612, leading=13.0)

    # grid of four
    story_card(40, 490, "CONFLICT - LIBYA", RED,
               "RUSSIAN WARSHIP SUNK OFF LIBYA",
               "Kyiv said seven naval drones sank the corvette Merkury in Benghazi port.",
               lambda cx, cy: icon_ship(cx, cy - 2, 32, WHITE))
    story_card(520, 490, "ENERGY - STRAIT OF HORMUZ", ORANGE,
               "TANKERS HIT MINES IN HORMUZ STRAIT",
               "Iran said three tankers struck mines in the world's key oil chokepoint.",
               lambda cx, cy: icon_tanker(cx, cy, 32, WHITE))
    story_card(40, 710, "JUSTICE - MYANMAR", PURPLE,
               "14 NATIONS BACK ICJ ROHINGYA RULING",
               "They affirmed the World Court's genocide finding; Britain sanctioned Myanmar's rulers.",
               lambda cx, cy: icon_scales(cx, cy, 30, WHITE))
    story_card(520, 710, "TECH + LAW - UNITED STATES", BLUE,
               "US STATES SUE MUSK FIRMS OVER GROK",
               "States sued Elon Musk's companies over sexualised images made by the Grok chatbot.",
               lambda cx, cy: icon_robot(cx, cy, 30, WHITE, BLUE))

    # sources line
    draw_text_center(512, 934, "COMPILED FROM THE DAY'S REPORTING - BBC - THE GUARDIAN - AP - AFP - SCMP",
                     1.15, GREY, 2.2)

    # footer briefs
    fill_rect(0, 946, W, H, NAVY)
    icon_rocket(72, 985, 26, WHITE, GOLD)
    draw_block(108, 954, "SPACE: Pakistani Zeeshan Ali to be the first foreign astronaut "
                         "aboard China's Tiangong station.", 1.55, WHITE, 2.8, 372, leading=13.0)
    icon_flame(548, 985, 24, ORANGE, GOLD)
    draw_block(584, 954, "INDONESIA: Factory fire in Banten kills at least 24 people; "
                         "dozens are still missing.", 1.55, WHITE, 2.8, 396, leading=13.0)


# ---------------------------------------------------------------- png out
def png_bytes():
    raw = bytearray()
    rowlen = W * 3
    for y in range(H):
        raw.append(0)
        raw += px[y * rowlen:(y + 1) * rowlen]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def main():
    build()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(png_bytes())


if __name__ == "__main__":
    main()
