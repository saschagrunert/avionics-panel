"""Small OpenCascade helpers shared by the plate and knob generators."""
import math

from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_Transform
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeRevol
from OCC.Core.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCC.Core.GProp import GProp_GProps
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.Interface import Interface_Static
from OCC.Core.StepBasic import StepBasic_Product
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.TCollection import TCollection_HAsciiString
from OCC.Core.TopTools import TopTools_ListOfShape


def box(x0, y0, z0, x1, y1, z1):
    return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()


def cyl(r, z0, z1, cx=0.0, cy=0.0):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(cx, cy, z0), gp_Dir(0, 0, 1)), r, z1 - z0).Shape()


def revolve(profile):
    """solid of revolution about Z from a closed (r, z) polygon."""
    poly = BRepBuilderAPI_MakePolygon()
    for r, z in profile:
        poly.Add(gp_Pnt(r, 0, z))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakeRevol(face, gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 2 * math.pi).Shape()


def fluted_section(R, flutes, depth, z, per_flute=12):
    """closed polygon of a fluted knob section (12 facets per flute: smooth at print resolution).
    A periodic B-spline through the same points gives a wrong loft, so this stays a polygon."""
    p = BRepBuilderAPI_MakePolygon()
    n = flutes * per_flute
    for i in range(n):
        t = 2 * math.pi * i / n
        r = R - depth * (0.5 - 0.5 * math.cos(flutes * t))
        p.Add(gp_Pnt(r * math.cos(t), r * math.sin(t), z))
    p.Close()
    return p.Wire()


def fluted(R, h, flutes, depth, taper, cham, bottom_cham=0.3, z0=0.0):
    """fluted, slightly tapered knob body from z0 to z0 + h with chamfered top (and bottom) edges."""
    ts = BRepOffsetAPI_ThruSections(True, True)
    ts.AddWire(fluted_section(R, flutes, depth, z0 - 0.01))
    ts.AddWire(fluted_section(R * (1 - taper), flutes, depth, z0 + h + 0.01))
    ts.Build()
    body = ts.Shape()
    Rt = R * (1 - taper)
    m = 1.5
    env = [(0, z0), (R - bottom_cham, z0), (R + m, z0 + bottom_cham + m),
           (Rt + m, z0 + h - cham - m), (Rt - cham, z0 + h), (0, z0 + h)]
    return common(body, revolve(env))


def cut(a, *tools):
    args, tl = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(a)
    for t in tools:
        tl.Append(t)
    op = BRepAlgoAPI_Cut(); op.SetArguments(args); op.SetTools(tl); op.Build()
    assert op.IsDone()
    return op.Shape()


def fuse(a, b):
    op = BRepAlgoAPI_Fuse(a, b); assert op.IsDone(); return op.Shape()


def common(a, b):
    op = BRepAlgoAPI_Common(a, b); assert op.IsDone(); return op.Shape()


def dbore(d, flat, z0, z1):
    """D-shaped bore along Z: dia d, flat `flat` across, flat towards +x."""
    return common(cyl(d / 2, z0, z1), box(-d, -d, z0 - 1, flat - d / 2, d, z1 + 1))


def move(shape, dx=0.0, dy=0.0, dz=0.0):
    t = gp_Trsf(); t.SetTranslation(gp_Vec(dx, dy, dz))
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def volume(shape):
    p = GProp_GProps(); brepgprop.VolumeProperties(shape, p); return p.Mass()


def pin_step_time(path):
    """STEP headers carry the write time: pin it, so a rebuild without changes leaves the file identical."""
    import re
    with open(path) as f:
        s = f.read()
    s = re.sub(r"(FILE_NAME\('[^']*',')[^']*(')", r"\g<1>2026-01-01T00:00:00\g<2>", s, count=1)
    with open(path, "w") as f:
        f.write(s)


def write_step(shape, name):
    """shape -> <name>.step (mm), its product named <name>. OpenCascade's own product name depends on the
    process: write.step.product.name only exists once a STEP writer has been made, and it appends how many
    shapes the process has transferred so far. The name goes onto the product itself instead, so the file is
    the same whichever process writes it, and in whatever order."""
    w = STEPControl_Writer()                                  # first, so the write.step parameters exist
    Interface_Static.SetCVal("write.step.unit", "MM")
    w.Transfer(shape, STEPControl_AsIs)
    model = w.Model()
    for i in range(1, model.NbEntities() + 1):
        entity = model.Value(i)
        if entity.IsKind("StepBasic_Product"):
            product = StepBasic_Product.DownCast(entity)
            product.SetId(TCollection_HAsciiString(name))
            product.SetName(TCollection_HAsciiString(name))
    assert w.Write(name + ".step") == IFSelect_RetDone
    pin_step_time(name + ".step")


def export(shape, name, deflection=0.01):
    assert BRepCheck_Analyzer(shape).IsValid(), f"{name}: invalid solid"
    write_step(shape, name)
    BRepMesh_IncrementalMesh(shape, deflection, False, 0.15, True)
    st = StlAPI_Writer(); st.SetASCIIMode(False); st.Write(shape, name + ".stl")
    print(f"{name}: {volume(shape) / 1000:.2f} cm3")
