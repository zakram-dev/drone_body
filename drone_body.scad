/*
 * ============================================================
 *  Compact Quadcopter Drone Body — Parametric OpenSCAD Model
 *  Version: 1.0  |  Units: mm  |  Generated: 2026-10-08
 * ============================================================
 *
 *  DESIGN SUMMARY
 *  ──────────────
 *  • Overall footprint  : ≤ 100 × 100 mm
 *  • Configuration      : X-quad (arms at 45 / 135 / 225 / 315 °)
 *  • Body shape         : Rounded-corner square frame
 *  • Arms               : 4 × tapered rectangular prisms with fillet reinforcement
 *  • Motor mounts       : 4 × circular platforms with M3 bolt holes + shaft bore
 *  • Electronics bay    : Open-top tray with floor, walls, and FC screw bosses
 *  • Battery holes      : 4 × M3 strap holes through base
 *  • Print-ready        : No floating geometry, ≤ 45 ° overhangs, flat base
 *
 *  HOW TO USE
 *  ──────────
 *  1. Open in OpenSCAD  (openscad.org — free & open source)
 *  2. Press F6 to render the full solid
 *  3. File → Export → STL  for 3-D printing
 *  4. File → Export → STEP requires OpenSCAD ≥ 2024 or use FreeCAD import
 *
 *  PARAMETERS FLAGGED FOR USER CONFIRMATION are marked  ← CONFIRM
 * ============================================================
 */

// ──────────────────────────────────────────────
//  GLOBAL QUALITY
// ──────────────────────────────────────────────
$fn = 48;   // Circle smoothness (increase for final render, lower for preview)

// ──────────────────────────────────────────────
//  FRAME PARAMETERS
// ──────────────────────────────────────────────
footprint           = 100;    // Maximum X/Y extent of entire frame (mm)
body_size           = 42;     // Center square side length (mm)
body_thickness      = 4;      // Frame plate thickness (mm)  [3–5 range]
body_corner_r       = 6;      // Rounded corner radius (mm)

// ──────────────────────────────────────────────
//  ARM PARAMETERS
// ──────────────────────────────────────────────
arm_width           = 10;     // Arm cross-section width (mm)
arm_taper_ratio     = 0.75;   // Width ratio at tip vs root (0.5–1.0)
arm_root_fillet_r   = 3;      // Fillet radius at arm-body junction (mm)

// Derived arm geometry
motor_platform_dia  = 16;     // Motor mount disc outer diameter (mm)
arm_reach           = footprint/2 - motor_platform_dia/2;
arm_root_x          = body_size/2 * cos(45);  // Root point along 45° diagonal

// ──────────────────────────────────────────────
//  MOTOR MOUNT PARAMETERS
// ──────────────────────────────────────────────
motor_platform_thick = 3;     // Platform thickness (mm)
motor_hole_dia       = 3.2;   // M3 clearance hole diameter (mm)
motor_hole_pcd       = 9;     // Bolt-circle diameter for motor holes (mm)   ← CONFIRM
motor_hole_count     = 4;     // Holes per mount (4 for standard 1104–2306)
motor_shaft_bore     = 5;     // Center shaft bore diameter (mm)             ← CONFIRM
prop_clearance_dia   = 14;    // Prop-clearance boss inner bore (mm)         ← CONFIRM
prop_clearance_h     = 1.5;   // Height of the clearance boss rim (mm)

// ──────────────────────────────────────────────
//  ELECTRONICS BAY PARAMETERS
// ──────────────────────────────────────────────
bay_x               = 30;     // Bay inner length X (mm)   ← CONFIRM (FC footprint)
bay_y               = 30;     // Bay inner width  Y (mm)   ← CONFIRM (FC footprint)
bay_wall            = 1.5;    // Wall thickness (mm)
bay_floor           = 1.2;    // Floor thickness (mm)
bay_depth           = body_thickness - bay_floor;  // Pocket depth

// FC screw boss parameters
fc_boss_od          = 4.5;    // FC mounting boss outer diameter (mm)
fc_boss_id          = 2.5;    // FC mounting hole (M2.5) (mm)               ← CONFIRM
fc_hole_pcd         = 20;     // FC bolt-circle diameter (mm)                ← CONFIRM
fc_boss_height      = body_thickness + 3; // Bosses stand above body surface

// ──────────────────────────────────────────────
//  BATTERY MOUNT PARAMETERS
// ──────────────────────────────────────────────
batt_hole_dia       = 3.2;    // M3 battery-strap hole diameter (mm)
batt_strap_spacing_x = 20;    // Between strap hole pairs, X axis (mm)       ← CONFIRM
batt_strap_spacing_y = 14;    // Between strap hole pairs, Y axis (mm)       ← CONFIRM

// ──────────────────────────────────────────────
//  DERIVED HELPERS
// ──────────────────────────────────────────────
eps = 0.01;  // Small epsilon to avoid z-fighting in boolean previews

// ──────────────────────────────────────────────
//  MODULES
// ──────────────────────────────────────────────

// Rounded-corner square (2-D hull trick)
module rounded_square_2d(size, r) {
    offset(r=r, $fn=$fn) square(size - 2*r, center=true);
}

// ── CENTER BODY ──────────────────────────────
module center_body() {
    difference() {
        // Main frame plate
        linear_extrude(height=body_thickness)
            rounded_square_2d(body_size, body_corner_r);

        // Electronics bay pocket (open top, closed floor)
        translate([0, 0, bay_floor])
            cube([bay_x, bay_y, body_thickness + eps], center=true);

        // Battery strap holes (4 × M3)
        battery_holes();
    }
}

// ── ARM (one, along +X axis; rotate to get others) ──
module single_arm() {
    root_w = arm_width;
    tip_w  = arm_width * arm_taper_ratio;
    root_x = arm_root_x;
    tip_x  = arm_reach;
    
    // Tapered arm polygon extruded upward
    linear_extrude(height=body_thickness)
        polygon(points=[
            [root_x,  root_w/2],
            [root_x, -root_w/2],
            [tip_x,  -tip_w/2],
            [tip_x,   tip_w/2]
        ]);

    // Reinforcement fillet at arm root (cylindrical quarter-round)
    translate([root_x, 0, 0])
        cylinder(r=arm_root_fillet_r, h=body_thickness, $fn=$fn);
}

// ── ALL 4 ARMS ───────────────────────────────
module all_arms() {
    for (ang = [45, 135, 225, 315])
        rotate([0, 0, ang]) single_arm();
}

// ── MOTOR MOUNT PLATFORM ─────────────────────
module motor_platform_solid() {
    // Solid disc
    cylinder(d=motor_platform_dia, h=motor_platform_thick, $fn=$fn);
}

module motor_platform_holes() {
    // Center shaft bore
    translate([0, 0, -eps])
        cylinder(d=motor_shaft_bore, h=motor_platform_thick + 2*eps, $fn=$fn);

    // 4 × motor mounting holes on bolt circle
    for (i = [0:motor_hole_count-1]) {
        ang = i * 360/motor_hole_count + 45;
        translate([cos(ang)*motor_hole_pcd/2,
                   sin(ang)*motor_hole_pcd/2, -eps])
            cylinder(d=motor_hole_dia, h=motor_platform_thick + 2*eps, $fn=16);
    }
}

// Prop-clearance raised annular boss on top of platform
module prop_clearance_boss() {
    z = motor_platform_thick;
    difference() {
        cylinder(d=motor_platform_dia, h=prop_clearance_h, $fn=$fn);
        translate([0, 0, -eps])
            cylinder(d=prop_clearance_dia, h=prop_clearance_h + 2*eps, $fn=$fn);
    }
    translate([0, 0, z]) prop_clearance_boss_ring();
}

module prop_clearance_boss_ring() {
    // Thin annular ring atop the platform edge
    difference() {
        cylinder(d=motor_platform_dia,     h=prop_clearance_h, $fn=$fn);
        translate([0, 0, -eps])
            cylinder(d=prop_clearance_dia, h=prop_clearance_h + 2*eps, $fn=$fn);
    }
}

module single_motor_mount() {
    difference() {
        union() {
            motor_platform_solid();
            translate([0, 0, motor_platform_thick])
                prop_clearance_boss_ring();
        }
        motor_platform_holes();
    }
}

// ── ALL 4 MOTOR MOUNTS ───────────────────────
module all_motor_mounts() {
    for (ang = [45, 135, 225, 315]) {
        dist = arm_reach;
        translate([cos(ang)*dist, sin(ang)*dist, 0])
            single_motor_mount();
    }
}

// ── FC SCREW BOSSES (inside bay) ─────────────
module fc_bosses() {
    for (i = [0:3]) {
        ang = i * 90 + 45;
        r   = fc_hole_pcd / 2;
        translate([cos(ang)*r, sin(ang)*r, 0])
            difference() {
                cylinder(d=fc_boss_od, h=fc_boss_height, $fn=$fn);
                translate([0, 0, -eps])
                    cylinder(d=fc_boss_id, h=fc_boss_height + 2*eps, $fn=16);
            }
    }
}

// ── BATTERY STRAP HOLES ──────────────────────
module battery_holes() {
    sx = batt_strap_spacing_x / 2;
    sy = batt_strap_spacing_y / 2;
    for (pos = [[sx,sy],[sx,-sy],[-sx,sy],[-sx,-sy]])
        translate([pos[0], pos[1], -eps])
            cylinder(d=batt_hole_dia, h=body_thickness + 2*eps, $fn=16);
}

// ──────────────────────────────────────────────
//  FOOTPRINT VERIFICATION CUBE (comment out for final export)
// ──────────────────────────────────────────────
// Uncomment the next line to show a transparent 100×100 footprint box:
// %translate([0,0,2]) cube([100,100,0.5], center=true);

// ──────────────────────────────────────────────
//  ASSEMBLY — FULL DRONE BODY
// ──────────────────────────────────────────────
module drone_body() {
    union() {
        center_body();
        all_arms();
        all_motor_mounts();
        fc_bosses();
    }
}

// ──────────────────────────────────────────────
//  RENDER
// ──────────────────────────────────────────────
drone_body();


/*
 * ══════════════════════════════════════════════
 *  EXPORT INSTRUCTIONS
 * ══════════════════════════════════════════════
 *
 *  STL (for 3-D printing):
 *    OpenSCAD → File → Export → Export as STL…
 *    Recommended settings: ≥ 48 segments ($fn), 0.01 mm tolerance
 *
 *  STEP (for CAD editing in Fusion 360, SolidWorks, FreeCAD, etc.):
 *    Option A — OpenSCAD ≥ 2024:
 *      File → Export → Export as STEP…
 *    Option B — FreeCAD (any version):
 *      1. Open FreeCAD → File → Open → select this .scad file
 *         (FreeCAD has native OpenSCAD import)
 *      2. File → Export → STEP AP214
 *    Option C — Convert STL to STEP online:
 *      CAD Exchanger, VoloVox, or FreeCAD "Part → Create shape from mesh"
 *
 * ══════════════════════════════════════════════
 *  PARAMETERS REQUIRING USER CONFIRMATION
 * ══════════════════════════════════════════════
 *  motor_hole_pcd      = 9 mm   — set per actual motor spec (1104→9mm, 2204→16mm)
 *  motor_shaft_bore    = 5 mm   — measure motor bell diameter + 0.5 mm clearance
 *  prop_clearance_dia  = 14 mm  — set to motor-bell OD for snug prop collar
 *  bay_x / bay_y       = 30 mm  — match your flight-controller board footprint
 *  fc_boss_id          = 2.5 mm — M2.5 for most FCs; some use M3 → change to 3.2
 *  fc_hole_pcd         = 20 mm  — standard 30×30 FC hole spacing uses ~20 mm PCD
 *  batt_strap_spacing  = 20×14  — measure your battery width and adjust
 * ══════════════════════════════════════════════
 */
