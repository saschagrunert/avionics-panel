"""R12 DXF of closed polylines for the CNC and laser-cutting services (make_plate_art.py, make_mech.py)."""
from pathlib import Path

# A minimal HEADER: $INSUNITS 4 = millimetres (CAM reads it as the drawing unit; R12 readers that do not know
# it skip it), $MEASUREMENT 1 = metric.
HEADER = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "9", "$MEASUREMENT", "70", "1", "0", "ENDSEC"]


def write_dxf(path, layers):
    """layers: {layer name: [polygon, ...]}, each polygon a list of (x, y) in mm, DXF frame (y up). Each
    polygon becomes one closed POLYLINE on its layer, coordinates to 0.1 um."""
    out = HEADER + ["0", "SECTION", "2", "ENTITIES"]
    for layer, polys in layers.items():
        for poly in polys:
            out += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
            for x, y in poly:
                out += ["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{y:.4f}"]
            out += ["0", "SEQEND", "8", layer]
    out += ["0", "ENDSEC", "0", "EOF"]
    Path(path).write_text("\n".join(out) + "\n")
