"""Render front/back previews from the Gerber files (black mask, white silk, ENIG pads)."""
import numpy as np
from PIL import Image, ImageDraw
import board as B
from check import raster, read_drill, PX, WPX, HPX


def board_mask():
    img = Image.new("L", (WPX, HPX), 0)
    dr = ImageDraw.Draw(img)
    from geom import rounded_rect
    dr.polygon([(x / PX, y / PX) for x, y in rounded_rect(0, 0, B.W, B.H, B.CORNER_R)], fill=255)
    holes = [(x, y, d) for (x, y, d) in B.holes_cut()] + read_drill("avionics-PTH.drl") + read_drill("avionics-NPTH.drl")
    for (x, y, d) in holes:
        r = d / 2 / PX
        dr.ellipse([x / PX - r, y / PX - r, x / PX + r, y / PX + r], fill=0)
    return np.array(img) > 127


def render(side, out):
    cu = raster(f"avionics-{side}_Cu.{'gtl' if side == 'F' else 'gbl'}")
    mk = raster(f"avionics-{side}_Mask.{'gts' if side == 'F' else 'gbs'}")
    sk = raster(f"avionics-{side}_Silkscreen.{'gto' if side == 'F' else 'gbo'}")
    bd = board_mask()
    img = np.zeros((HPX, WPX, 3), np.uint8)
    img[:] = (235, 235, 235)                       # background
    img[bd] = (22, 22, 24)                         # black soldermask
    img[bd & cu] = (40, 40, 44)                    # copper under mask
    img[bd & sk & ~mk] = (245, 245, 245)           # silkscreen
    img[bd & mk & cu] = (214, 172, 70)             # ENIG pads
    im = Image.fromarray(img)
    if side == "B":
        im = im.transpose(Image.FLIP_LEFT_RIGHT)   # as seen from the back
    im = im.resize((WPX // 2, HPX // 2), Image.LANCZOS)
    im.save(out)


render("F", "render-front.png")
render("B", "render-back.png")
print("rendered")
