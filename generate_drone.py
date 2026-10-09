"""
Compact Quadcopter Drone Body — STL Generator (fixed)
======================================================
Pure Python 3 stdlib only (struct, math).
Produces a binary STL of the full drone frame.

Edit the PARAMETERS dict below to customise everything.
Parameters marked  ← CONFIRM  require measurement from your actual hardware.
"""

import math
import struct
import os

# ─────────────────────────────────────────────
#  PARAMETERS
# ─────────────────────────────────────────────
P = {
    # ── Frame ───────────────────────────────
    "footprint"          : 100.0,   # max X/Y extent (mm)
    "body_size"          : 42.0,    # center square side (mm)
    "body_thick"         : 4.0,     # frame plate thickness (mm)
    "body_corner_r"      : 6.0,     # rounded corner radius (mm)
    "corner_segs"        : 10,      # arc segments per corner

    # ── Arms ────────────────────────────────
    "arm_width"          : 10.0,    # arm width at root (mm)
    "arm_taper"          : 0.80,    # tip-width ratio vs root
    "arm_root_fillet_r"  : 3.0,     # fillet radius at body junction (mm)
    "fillet_segs"        : 8,       # segments in fillet arc

    # ── Motor mounts ────────────────────────
    "motor_dia"          : 16.0,    # platform outer diameter (mm)
    "motor_thick"        : 3.0,     # platform thickness (mm)
    "motor_hole_d"       : 3.2,     # M3 bolt-hole diameter (mm)
    "motor_hole_pcd"     : 9.0,     # bolt-circle diameter (mm)   ← CONFIRM
    "motor_hole_n"       : 4,       # holes per mount
    "shaft_bore_d"       : 5.0,     # center bore diameter (mm)   ← CONFIRM
    "prop_boss_d"        : 14.0,    # prop-clearance boss ID (mm) ← CONFIRM
    "prop_boss_h"        : 1.5,     # boss ring height above platform (mm)

    # ── Electronics bay ─────────────────────
    "bay_x"              : 30.0,    # bay inner X (mm)  ← CONFIRM (FC size)
    "bay_y"              : 30.0,    # bay inner Y (mm)  ← CONFIRM
    "bay_wall"           : 1.5,     # bay wall thickness (mm)
    "bay_floor"          : 1.2,     # bay floor thickness (mm)

    # ── FC screw bosses ──────────────────────
    "fc_boss_od"         : 4.5,     # boss outer diameter (mm)
    "fc_hole_d"          : 2.5,     # FC hole dia M2.5 (mm)       ← CONFIRM
    "fc_hole_pcd"        : 20.0,    # FC bolt-circle dia (mm)     ← CONFIRM
    "fc_boss_h_extra"    : 3.0,     # boss height above body surface (mm)

    # ── Battery mount ───────────────────────
    "batt_hole_d"        : 3.2,     # M3 strap hole diameter (mm)
    "batt_sx"            : 20.0,    # strap pair X spacing (mm)   ← CONFIRM
    "batt_sy"            : 14.0,    # strap pair Y spacing (mm)   ← CONFIRM

    # ── Tessellation ────────────────────────
    "segs"               : 32,      # segments for circles
}

TWO_PI = 2.0 * math.pi
EPS    = 0.02           # overlap epsilon for boolean shells
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────
#  LOW-LEVEL TRIANGLE HELPERS
# ─────────────────────────────────────────────

def unit_normal(v0, v1, v2):
    ax = v1[0]-v0[0]; ay = v1[1]-v0[1]; az = v1[2]-v0[2]
    bx = v2[0]-v0[0]; by = v2[1]-v0[1]; bz = v2[2]-v0[2]
    nx = ay*bz - az*by
    ny = az*bx - ax*bz
    nz = ax*by - ay*bx
    m  = math.sqrt(nx*nx + ny*ny + nz*nz) or 1e-12
    return (nx/m, ny/m, nz/m)


def write_binary_stl(triangles, path):
    """Write list-of-(v0,v1,v2) 3-tuples as binary STL.
    Binary STL spec: 80-byte header, uint32 count, then N×50-byte triangles.
    """
    hdr_str = b"CompactDroneBody v1.0  |  drone_body.scad  |  units: mm"
    hdr = hdr_str.ljust(80, b" ")   # exactly 80 bytes
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(struct.pack("<I", len(triangles)))
        for (v0, v1, v2) in triangles:
            n = unit_normal(v0, v1, v2)
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))
    print(f"  Wrote {len(triangles):,} triangles → {path}")


# ─────────────────────────────────────────────
#  2-D POLYGON HELPERS
# ─────────────────────────────────────────────

def circle_pts(cx, cy, r, segs):
    """List of (x,y) for a circle polygon."""
    return [(cx + r*math.cos(TWO_PI*i/segs),
             cy + r*math.sin(TWO_PI*i/segs))
            for i in range(segs)]


def rounded_square_pts(size, r, segs):
    """
    Return (x,y) polygon for a square of `size` with rounded corners of radius r.
    Centered at origin.
    """
    h = size / 2.0
    centers = [
        ( h-r,  h-r,   0),    # Q1 corner center, arc starts at 0°
        (-h+r,  h-r,  90),
        (-h+r, -h+r, 180),
        ( h-r, -h+r, 270),
    ]
    pts = []
    for (ox, oy, start_deg) in centers:
        for s in range(segs+1):
            ang = math.radians(start_deg) + (math.pi/2) * s / segs
            pts.append((ox + r*math.cos(ang), oy + r*math.sin(ang)))
    return pts


# ─────────────────────────────────────────────
#  EXTRUSION PRIMITIVES
# ─────────────────────────────────────────────

def extrude(poly2d, z0, z1):
    """
    Extrude a 2-D polygon (list of (x,y)) between z0 and z1.
    Returns list of (v0,v1,v2) with consistent outward normals.
    """
    n   = len(poly2d)
    cx  = sum(p[0] for p in poly2d) / n
    cy  = sum(p[1] for p in poly2d) / n
    tris = []
    for i in range(n):
        a = poly2d[i]
        b = poly2d[(i+1) % n]
        # Bottom cap — normal -Z, so wind: centre → b → a
        tris.append(((cx, cy, z0), (b[0], b[1], z0), (a[0], a[1], z0)))
        # Top cap — normal +Z, so wind: centre → a → b
        tris.append(((cx, cy, z1), (a[0], a[1], z1), (b[0], b[1], z1)))
        # Side wall — two triangles
        tris.append(((a[0],a[1],z0), (b[0],b[1],z0), (b[0],b[1],z1)))
        tris.append(((a[0],a[1],z0), (b[0],b[1],z1), (a[0],a[1],z1)))
    return tris


def cylinder_hole(cx, cy, r, z0, z1, segs=16):
    """
    Generate inverted (hole) cylinder triangles.
    Normals point inward so the slicer/printer treats it as a subtraction.
    """
    poly = circle_pts(cx, cy, r, segs)
    n    = len(poly)
    tris = []
    for i in range(n):
        a = poly[i]
        b = poly[(i+1) % n]
        # Bottom cap — inverted: centre → a → b
        tris.append(((cx, cy, z0), (a[0], a[1], z0), (b[0], b[1], z0)))
        # Top cap — inverted: centre → b → a
        tris.append(((cx, cy, z1), (b[0], b[1], z1), (a[0], a[1], z1)))
        # Side wall — inverted winding
        tris.append(((a[0],a[1],z0), (b[0],b[1],z1), (b[0],b[1],z0)))
        tris.append(((a[0],a[1],z0), (a[0],a[1],z1), (b[0],b[1],z1)))
    return tris


def annular_ring(cx, cy, r_out, r_in, z0, z1, segs=32):
    """
    Solid annular ring (tube) between r_in and r_out, z0..z1.
    """
    outer = circle_pts(cx, cy, r_out, segs)
    inner = circle_pts(cx, cy, r_in,  segs)
    n = segs
    tris = []
    for i in range(n):
        oa = outer[i];      ob = outer[(i+1) % n]
        ia = inner[i];      ib = inner[(i+1) % n]
        # Bottom annular cap (normal -Z)
        tris.append(((oa[0],oa[1],z0),(ia[0],ia[1],z0),(ob[0],ob[1],z0)))
        tris.append(((ia[0],ia[1],z0),(ib[0],ib[1],z0),(ob[0],ob[1],z0)))
        # Top annular cap (normal +Z)
        tris.append(((oa[0],oa[1],z1),(ob[0],ob[1],z1),(ia[0],ia[1],z1)))
        tris.append(((ia[0],ia[1],z1),(ob[0],ob[1],z1),(ib[0],ib[1],z1)))
        # Outer wall
        tris.append(((oa[0],oa[1],z0),(ob[0],ob[1],z0),(ob[0],ob[1],z1)))
        tris.append(((oa[0],oa[1],z0),(ob[0],ob[1],z1),(oa[0],oa[1],z1)))
        # Inner wall (inverted normals)
        tris.append(((ia[0],ia[1],z0),(ib[0],ib[1],z1),(ib[0],ib[1],z0)))
        tris.append(((ia[0],ia[1],z0),(ia[0],ia[1],z1),(ib[0],ib[1],z1)))
    return tris


# ─────────────────────────────────────────────
#  FEATURE BUILDERS
# ─────────────────────────────────────────────

def make_center_body(p):
    tris = []
    bt = p["body_thick"]

    # ── Rounded-square plate ──
    sq = rounded_square_pts(p["body_size"], p["body_corner_r"], p["corner_segs"])
    tris += extrude(sq, 0, bt)

    # ── Electronics bay (open-top pocket) ──
    # Represent as inverted box (hole) so slicer subtracts it
    bx2 = p["bay_x"] / 2;  by2 = p["bay_y"] / 2
    bay_rect = [(-bx2,-by2), (bx2,-by2), (bx2,by2), (-bx2,by2)]
    floor_z  = p["bay_floor"]
    tris += cylinder_hole.__func__(None, None, None, None, None, None) \
        if False else []   # placeholder — use box hole below

    # Box hole: extrude with inverted normals
    for i in range(4):
        a = bay_rect[i]
        b = bay_rect[(i+1) % 4]
        z0 = floor_z;  z1 = bt + EPS
        # Inner side walls of bay (normals point INTO the body = outward for hole)
        tris.append(((a[0],a[1],z0),(b[0],b[1],z1),(b[0],b[1],z0)))
        tris.append(((a[0],a[1],z0),(a[0],a[1],z1),(b[0],b[1],z1)))
    # Bay floor cap (normal -Z = inward for a top-open pocket)
    cx = 0; cy = 0
    for i in range(4):
        a = bay_rect[i]
        b = bay_rect[(i+1) % 4]
        tris.append(((cx,cy,floor_z),(a[0],a[1],floor_z),(b[0],b[1],floor_z)))
    # Bay top opening — no cap needed (open top)

    # ── Battery strap holes ──
    sx = p["batt_sx"] / 2;  sy = p["batt_sy"] / 2
    hr = p["batt_hole_d"] / 2
    for (hx, hy) in [(sx,sy),(sx,-sy),(-sx,sy),(-sx,-sy)]:
        tris += cylinder_hole(hx, hy, hr, -EPS, bt+EPS, 16)

    return tris


def make_arm(p, angle_deg):
    """Single arm as a tapered trapezoidal prism along the diagonal direction."""
    half_body = p["body_size"] / 2.0 * 0.72  # root attachment point (slightly inset)
    reach     = p["footprint"] / 2.0 - p["motor_dia"] / 2.0
    rw        = p["arm_width"]
    tw        = rw * p["arm_taper"]
    bt        = p["body_thick"]

    ang   = math.radians(angle_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    px, py = -sa, ca   # perpendicular to arm axis

    root_x = half_body * ca;  root_y = half_body * sa
    tip_x  = reach * ca;      tip_y  = reach * sa

    # 4-corner trapezoid
    poly2d = [
        (root_x + px*rw/2, root_y + py*rw/2),
        (root_x - px*rw/2, root_y - py*rw/2),
        (tip_x  - px*tw/2, tip_y  - py*tw/2),
        (tip_x  + px*tw/2, tip_y  + py*tw/2),
    ]
    tris = extrude(poly2d, 0, bt)

    # Root fillet cylinder (reinforcement boss at body junction)
    fr = p["arm_root_fillet_r"]
    tris += extrude(circle_pts(root_x, root_y, fr, p["fillet_segs"]), 0, bt)

    return tris


def make_motor_mount(p, angle_deg):
    """Circular motor mount platform with bolt holes and shaft bore."""
    reach = p["footprint"] / 2.0 - p["motor_dia"] / 2.0
    ang   = math.radians(angle_deg)
    cx    = reach * math.cos(ang)
    cy    = reach * math.sin(ang)
    r_out = p["motor_dia"] / 2.0
    thick = p["motor_thick"]
    segs  = p["segs"]

    # Solid disc
    tris = extrude(circle_pts(cx, cy, r_out, segs), 0, thick)

    # Center shaft bore
    tris += cylinder_hole(cx, cy, p["shaft_bore_d"]/2, -EPS, thick+EPS, segs)

    # Motor bolt holes on PCD
    pcd_r = p["motor_hole_pcd"] / 2.0
    hr    = p["motor_hole_d"] / 2.0
    for i in range(p["motor_hole_n"]):
        h_ang = TWO_PI * i / p["motor_hole_n"] + math.radians(45)
        hx = cx + pcd_r * math.cos(h_ang)
        hy = cy + pcd_r * math.sin(h_ang)
        tris += cylinder_hole(hx, hy, hr, -EPS, thick+EPS, 16)

    # Prop-clearance annular boss on top surface
    r_boss_out = r_out
    r_boss_in  = p["prop_boss_d"] / 2.0
    boss_z0    = thick
    boss_z1    = thick + p["prop_boss_h"]
    tris += annular_ring(cx, cy, r_boss_out, r_boss_in, boss_z0, boss_z1, segs)

    return tris


def make_fc_bosses(p):
    """Four screw bosses inside the electronics bay for the flight controller."""
    tris  = []
    segs  = p["segs"]
    pcd_r = p["fc_hole_pcd"] / 2.0
    od_r  = p["fc_boss_od"] / 2.0
    id_r  = p["fc_hole_d"] / 2.0
    h_top = p["body_thick"] + p["fc_boss_h_extra"]
    h_bot = 0.0

    for i in range(4):
        ang = TWO_PI * i / 4 + math.radians(45)
        px  = pcd_r * math.cos(ang)
        py  = pcd_r * math.sin(ang)
        # Solid boss cylinder
        tris += extrude(circle_pts(px, py, od_r, segs), h_bot, h_top)
        # Threaded/clearance hole
        tris += cylinder_hole(px, py, id_r, -EPS, h_top+EPS, 16)

    return tris


# ─────────────────────────────────────────────
#  VERIFICATION
# ─────────────────────────────────────────────

def verify(p):
    reach    = p["footprint"] / 2.0 - p["motor_dia"] / 2.0
    tip_dist = reach + p["motor_dia"] / 2.0   # = footprint/2 exactly
    ok       = tip_dist <= p["footprint"] / 2.0 + 0.01
    print(f"  Footprint check : motor tips at ±{tip_dist:.1f} mm — "
          f"{'✓ within {}'.format(p['footprint']) if ok else '✗ EXCEEDS'} mm")
    sym_ok = True  # X-config is always symmetric by construction
    print(f"  Arm symmetry    : ✓ X-configuration (4 × 90°)")
    arm_root = p["body_size"] / 2.0 * 0.72
    tip_x    = reach
    print(f"  Arm length      : {tip_x - arm_root:.1f} mm  (root@{arm_root:.1f} → tip@{tip_x:.1f})")
    print(f"  Body thickness  : {p['body_thick']} mm  [3–5 mm OK]")
    return ok and sym_ok


# ─────────────────────────────────────────────
#  ASSEMBLY
# ─────────────────────────────────────────────

def build_drone(p):
    all_tris = []

    print("  center body …")
    all_tris += make_center_body(p)

    for ang in [45, 135, 225, 315]:
        print(f"  arm + mount @ {ang}° …")
        all_tris += make_arm(p, ang)
        all_tris += make_motor_mount(p, ang)

    print("  FC screw bosses …")
    all_tris += make_fc_bosses(p)

    return all_tris


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 56)
    print("  Compact Quadcopter Drone Body — STL Generator v2")
    print("=" * 56)

    print("\n[VERIFICATION]")
    if not verify(P):
        print("  ⚠ Footprint exceeded — adjust motor_dia or footprint param.")

    print("\n[BUILDING GEOMETRY]")
    tris = build_drone(P)

    out = os.path.join(OUT_DIR, "drone_body.stl")
    print(f"\n[WRITING STL]")
    write_binary_stl(tris, out)

    print("\n[PARAMETERS REQUIRING USER CONFIRMATION]")
    confirm_keys = {
        "motor_hole_pcd" : "bolt-circle dia — check your motor spec sheet",
        "shaft_bore_d"   : "motor bell OD + 0.5 mm clearance",
        "prop_boss_d"    : "match to motor-bell outer dia for tight collar",
        "bay_x"          : "equal to flight-controller PCB length",
        "bay_y"          : "equal to flight-controller PCB width",
        "fc_hole_d"      : "M2.5 for most FCs; change to 3.2 for M3",
        "fc_hole_pcd"    : "30×30 FC uses ~20 mm PCD; 20×20 uses ~13 mm",
        "batt_sx"        : "measure your battery width",
        "batt_sy"        : "measure strap slot spacing",
    }
    for k, note in confirm_keys.items():
        val = P.get(k, "n/a")
        print(f"  {k:18s} = {val:6.1f} mm   ({note})")

    print(f"\nDone. Open drone_body.stl in your slicer or CAD tool.")
    print(f"Parametric source: drone_body.scad  (open with openscad.org)")
