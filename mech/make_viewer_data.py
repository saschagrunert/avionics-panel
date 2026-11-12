"""Geometry for the 3D view (viewer/geometry.js, a plain script so the page also opens from disk), taken from
board.py, stack.py, make_mech.py and make_caps.py, so the viewer never carries hand copies of them.

Board coordinates in mm (x to the right, y from the back edge towards the user), heights with z = 0 at the PCB
top. The file is byte-stable (sorted keys, fixed rounding), so CI can check it is up to date.
Needs pythonocc-core and pillow (make_mech.py and make_caps.py import them).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pcb"))
import board as B
import make_caps as MC
import make_mech as MM
import stack as S


def rounded(v):
    if isinstance(v, float):
        return round(v, 4) + 0.0
    if isinstance(v, dict):
        return {k: rounded(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [rounded(x) for x in v]
    return v


def dump(v, pad=""):
    """JSON with sorted keys: one key or one nested list per line, a list of plain values on one line."""
    if isinstance(v, dict):
        return ("{\n" + ",\n".join(f"{pad} {json.dumps(k)}: {dump(x, pad + ' ')}" for k, x in sorted(v.items()))
                + f"\n{pad}}}")
    if isinstance(v, list) and any(isinstance(x, (dict, list)) for x in v):
        return "[\n" + ",\n".join(f"{pad} {dump(x, pad + ' ')}" for x in v) + f"\n{pad}]"
    return json.dumps(v)


pads = B.build()
# The bottom-side parts are only drawn: nominal or estimated package height by footprint name (pcb/board.py's BODY
# has their outlines), and the footprints with a metal face.
PART_H = {"0603": 0.8, "0402": 0.5, "1206": 0.8, "SOD-123": 0.9, "SOT-23": 1.1, "SOT-23-6": 1.1,
          "SOIC-8 150mil": 1.5, "LQFN-56 7x7": 0.9, "3225 4-pad": 0.8, "1206 reverse": 0.28}
PART_METAL = ("3225 4-pad", "1206 reverse", "USB-C 16P")
if missing := sorted(set(B.BODY) - set(PART_H)):
    raise SystemExit(f"make_viewer_data.py: no height in PART_H for the footprints {missing} of board.BODY")
# their bodies: outline (x0, y0, x1, y1), height under the board, metal or black
bodies = [[*box, MM.J1_H if ref == "J1" else PART_H[B.FOOTPRINT[ref]], B.FOOTPRINT[ref] in PART_METAL]
          for ref, box in B.bodies().items()]

geometry = {
    "board": {"w": B.W, "h": B.H, "corner_r": B.CORNER_R, "t": S.PCB_T, "mounts": B.MOUNTS,
              "corner_mounts": B.CORNER_MOUNTS, "mid_mount": B.MID_MOUNT,
              "mount_hole": B.MOUNT_HOLE, "key_pad_dx": B.KEY_DX, "key_pad_dy": B.KEY_DY, "trace_w": B.TRACE_W,
              # the pads of the through-hole parts, as they show on the top side: x, y, size along x and y
              "pads": [[p.x, p.y, p.w, p.h] for p in pads if p.drill and "F" in p.mask],
              "boot_pads": [[p.x, p.y, p.w, p.h] for p in pads if p.name.startswith("JP_BOOT")]},
    "body": {"clear": MM.CLEAR, "overhang": S.OVH, "z_bot": MM.Z_BOT,
             "z_floor": MM.Z_FLOOR_TOP, "wall_gap": S.WALL_GAP, "tilt_deg": S.BODY_TILT, "boss_r": MM.BOSS_R,
             "boss_hole_r": MM.SCREW_CLEAR, "supports": MM.SUPPORTS, "support_r": MM.SUPPORT_R,
             "z_floor_bot": MM.Z_FLOOR_BOT, "hollow_front": MM.hollow_front(), "ribs_x": MM.RIBS_X,
             "ribs_y": MM.RIBS_Y, "rib_t": MM.RIB_T, "boss_r_low": MM.BOSS_R_LOW, "counterbore_r": MM.HEAD_R,
             "seat_z": S.SEAT_Z, "feet": MM.FEET, "foot_pad": MM.FOOT_PAD,
             "foot_bridges": MM.foot_bridges(), "support_top": MM.SUPPORT_TOP,
             "usb_open": {**{k: MM.USB_OPEN[k] for k in ("w", "h", "z")}, "y": S.USB_OPEN_IN}, "usb_keep": MM.USB_KEEP,
             "boot": B.BOOT, "boot_hole": MM.BOOT_HOLE,
             "mid_bar_w": S.MID_BAR["w"], "join_short": MM.JOIN_SHORT},
    "plate": {"z0": S.PLATE_Z0, "z1": S.PLATE_Z1, "key_hole": S.KEY_HOLE, "shaft_hole": S.SHAFT_HOLE,
              "range_hole": S.RANGE_HOLE, "front_break": S.FRONT_BREAK,
              "tongue": {k: S.USB_TONGUE[k] for k in ("w", "d", "h")}},
    # the plate's artwork: the frame round the keys with its group titles, the legends under the keys and round
    # the knobs, the pan arrows round RANGE
    "plate_art": {"text": S.PLATE_TEXT, "frame": S.key_frame(B.COLS, B.ROWS),
                  "title": {k: S.GROUP_TITLE[k] for k in ("size", "track", "pad")},
                  "shift_legend": S.SHIFT_LEGEND, "knob": S.KNOB_ART, "range": S.RANGE_ART},
    "keys": {"cols": B.COLS, "rows": B.ROWS, "cap": [S.CAP["w"], S.CAP["h"], S.CAP["r"]],
             "cap_height": S.CAP["height"], "cap_chamfer": S.CAP["cham"], "cap_base": S.CAP["base"],
             "plunger_top": S.PLUNGER_TOP, "plunger": S.PLUNGER, "switch_body": S.SWITCH_BODY,
             # stack.CAP_BAR_EDGE for every cap, 0 included: the page fails on a key geometry.js lacks
             "bar": {**{k: S.CAP_BAR[k] for k in ("w", "d", "proud", "inset")},
                     "edge": {label: S.CAP_BAR_EDGE.get(label, 0) for row in S.KEY_LEGENDS for label, _ in row}},
             # em: the one legend size (mm), as make_caps.py sizes it with the font's own metrics
             "legend": {"em": MC.LEGEND_EM, "weight": S.LEGEND_WEIGHT, "grow": S.LEGEND_GROW, "line": S.LEGEND_LINE,
                        "direct_to": S.DIRECT_TO, "flip_polys": S.CAP_FLIP_ICON}},
    "key_legends": S.KEY_LEGENDS,
    "flip_icon": {"w": S.FLIP_W, "gap": S.FLIP_GAP, "polys": S.FLIP_ICON},
    "knobs": {name: {"x": x, "y": y, "flutes": S.OUTER_FLUTES.get(name), "legend_tilt": S.KNOB_LEGEND_TILT[name],
                     "legend": S.KNOB_LEGENDS[name][0], "legend_shift": S.KNOB_LEGENDS[name][1]}
              for name, (x, y) in (("ALTHDG", B.ALTHDG), ("FREQ", B.FREQ), ("FMS", B.FMS), ("RANGE", B.RANGE))},
    "outer_knob": S.OUTER_KNOB, "inner_knob": {k: S.INNER_KNOB[k] for k in ("d", "z0", "z1")},
    "range_knob": S.RANGE_KNOB, "flutes": S.FLUTES,
    "encoder": {"size": S.EC11_SIZE, "body": S.EC11_BODY, "sleeve_top": S.SLEEVE_TOP, "outer_top": S.OUTER_TOP,
                "inner_top": S.INNER_TOP, "sleeve_d": S.SLEEVE_D, "outer_d": S.OUTER_D, "inner_d": S.INNER_D},
    "rkjxt": {"across": S.RKJXT_ACROSS, "flats": S.RKJXT_FLATS, "body": S.RKJXT_BODY, "hub_top": S.RKJXT_HUB_TOP,
              "hub_d": S.RKJXT_HUB[0], "lever_z1": S.LEVER_Z1, "lever_d": S.LEVER_D},
    "lights": {name: {"x": x, "y": y, "d": S.LIGHT_HOLE} for name, ((x, y), _gp, _c) in B.LEDS.items()},
    "led": {"cutout": B.LED_CUTOUT, "lens": {k: S.LED_LENS[k] for k in ("l", "w", "h")}}, "amber": S.AMBER["hex"],
    "pipe": {k: S.PIPE[k] for k in ("z0", "len", "clear", "base_d", "base_len")},
    "screw": {"head_z": S.SCREW_HEAD_Z, "length": S.SCREW_L, "d": S.SCREW_D, "head_d": S.SCREW["head_d"],
              "head_k": S.SCREW["head_k"], "flange_d": S.SCREW["flange_d"], "flange_c": S.SCREW["flange_c"],
              "hex": S.SCREW["hex"]},
    "boss": {"d": S.BOSS["d"], "tap_d": S.TAP["drill"]},
    "parts": {"usb_x": B.USB_X, "bodies": bodies},
}
out = Path(__file__).resolve().parent.parent / "viewer" / "geometry.js"
out.write_text("// Generated by mech/make_viewer_data.py from board.py and stack.py: do not edit.\n"
               "window.GEOMETRY = " + dump(rounded(geometry)) + ";\n")
print(f"viewer geometry: {len(geometry)} groups -> {out.relative_to(out.parent.parent)}")
