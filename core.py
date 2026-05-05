# 1. Open Autodesk Fusion 360
# 2. Go to UTILITIES > Add-Ins > Scripts and Add-Ins (or press Shift+S)
# 3. Click the green "+" button under "My Scripts"
# 4. Navigate to this file and select it
# 5. Click "Run"

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import math

# PARAMETERS  (all dimensions in centimetres)
SHIN_LENGTH        = 28.0   # total length of the guard (top to bottom)
SHIN_WIDTH_TOP     = 8.0    # width at the top (knee end)
SHIN_WIDTH_BOTTOM  = 6.0    # width at the ankle end
SHIN_HEIGHT        = 1.5    # convex dome height (how much it curves outward)
THICKNESS          = 0.35   # shell thickness
ANKLE_WING_WIDTH   = 2.5    # lateral wing width on ankle section
ANKLE_WING_LENGTH  = 6.0    # how far up ankle wings extend
EDGE_RADIUS        = 0.6    # fillet radius on all hard edges
VENT_ROWS          = 4      # number of ventilation hole rows
VENT_COLS          = 3      # ventilation holes per row
VENT_RADIUS        = 0.55   # radius of each vent hole


def run(context):
    ui = None
    try:
        app  = adsk.core.Application.get()
        ui   = app.userInterface
        des  = adsk.fusion.Design.cast(app.activeProduct)

        if not des:
            ui.messageBox("Please open a Fusion 360 design before running this script.")
            return

        root = des.rootComponent
        occs = root.occurrences
        mat  = adsk.core.Matrix3D.create()
        occ  = occs.addNewComponent(mat)
        comp = occ.component
        comp.name = "ShinGuard"

        sks  = comp.sketches
        exts = comp.features.extrudeFeatures
        fils = comp.features.filletFeatures
        shls = comp.features.shellFeatures

        # 1. MAIN SHIELD PROFILE (front face)
        xy_plane = comp.xYConstructionPlane
        sk_profile = sks.add(xy_plane)
        sk_profile.name = "ShieldProfile"

        lines = sk_profile.sketchCurves.sketchLines
        arcs  = sk_profile.sketchCurves.sketchArcs
        pts   = adsk.core.ObjectCollection.create()

        hw_top = SHIN_WIDTH_TOP    / 2
        hw_bot = SHIN_WIDTH_BOTTOM / 2
        L      = SHIN_LENGTH

        # Trapezoid outline – wider at top (knee), narrower at bottom (ankle)
        p0 = adsk.core.Point3D.create(-hw_top, L,   0)
        p1 = adsk.core.Point3D.create( hw_top, L,   0)
        p2 = adsk.core.Point3D.create( hw_bot, 0,   0)
        p3 = adsk.core.Point3D.create(-hw_bot, 0,   0)

        lines.addByTwoPoints(p0, p1)   # top edge
        lines.addByTwoPoints(p1, p2)   # right edge
        lines.addByTwoPoints(p2, p3)   # bottom edge
        lines.addByTwoPoints(p3, p0)   # left edge

        prof = sk_profile.profiles.item(0)

        # 2. EXTRUDE to create solid slab
        ext_input = exts.createInput(
            prof,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        dist = adsk.core.ValueInput.createByReal(SHIN_HEIGHT)
        ext_input.setDistanceExtent(False, dist)
        solid = exts.add(ext_input)
        body  = solid.bodies.item(0)
        body.name = "ShieldBody"

        # 3. ANKLE WINGS
        sk_wings = sks.add(xy_plane)
        sk_wings.name = "AnkleWings"
        wlines = sk_wings.sketchCurves.sketchLines

        # Left wing
        wl0 = adsk.core.Point3D.create(-hw_bot,                   ANKLE_WING_LENGTH, 0)
        wl1 = adsk.core.Point3D.create(-hw_bot,                   0,                 0)
        wl2 = adsk.core.Point3D.create(-hw_bot - ANKLE_WING_WIDTH, 0,                 0)
        wl3 = adsk.core.Point3D.create(-hw_bot - ANKLE_WING_WIDTH, ANKLE_WING_LENGTH, 0)

        wlines.addByTwoPoints(wl0, wl1)
        wlines.addByTwoPoints(wl1, wl2)
        wlines.addByTwoPoints(wl2, wl3)
        wlines.addByTwoPoints(wl3, wl0)

        # Right wing (mirror)
        wr0 = adsk.core.Point3D.create( hw_bot,                   ANKLE_WING_LENGTH, 0)
        wr1 = adsk.core.Point3D.create( hw_bot,                   0,                 0)
        wr2 = adsk.core.Point3D.create( hw_bot + ANKLE_WING_WIDTH, 0,                 0)
        wr3 = adsk.core.Point3D.create( hw_bot + ANKLE_WING_WIDTH, ANKLE_WING_LENGTH, 0)

        wlines.addByTwoPoints(wr0, wr1)
        wlines.addByTwoPoints(wr1, wr2)
        wlines.addByTwoPoints(wr2, wr3)
        wlines.addByTwoPoints(wr3, wr0)

        # Extrude both wing profiles and join to main body
        for i in range(sk_wings.profiles.count):
            wing_prof = sk_wings.profiles.item(i)
            w_input = exts.createInput(
                wing_prof,
                adsk.fusion.FeatureOperations.JoinFeatureOperation
            )
            w_dist = adsk.core.ValueInput.createByReal(SHIN_HEIGHT)
            w_input.setDistanceExtent(False, w_dist)
            w_input.participantBodies = [body]
            exts.add(w_input)
          
        # 4. SHELL – hollow out to THICKNESS
        # We shell the back face (Z=0 plane face) to keep the front dome solid.
        back_face = None
        for f in body.faces:
            # Back face normal points in -Z direction and is roughly flat
            evaluator = f.evaluator
            area       = f.area
            # Identify the back flat face by checking face normal at centre
            bb = f.boundingBox
            cx = (bb.minPoint.x + bb.maxPoint.x) / 2
            cy = (bb.minPoint.y + bb.maxPoint.y) / 2
            cz = (bb.minPoint.z + bb.maxPoint.z) / 2
            ok, normal = evaluator.getNormalAtPoint(
                adsk.core.Point3D.create(cx, cy, cz)
            )
            if ok and normal.z < -0.9:
                back_face = f
                break

        if back_face:
            open_faces = adsk.core.ObjectCollection.create()
            open_faces.add(back_face)
            shl_input = shls.createInput(
                open_faces,
                adsk.fusion.FeatureOperations.JoinFeatureOperation
            )
            shl_input.insideThickness = adsk.core.ValueInput.createByReal(THICKNESS)
            shls.add(shl_input)
          
        # 5. VENTILATION HOLES (cut-through)
        # Place holes on a front face sketch
        front_face = None
        for f in body.faces:
            bb = f.boundingBox
            if abs(bb.maxPoint.z - SHIN_HEIGHT) < 0.01:
                cx = (bb.minPoint.x + bb.maxPoint.x) / 2
                cy = (bb.minPoint.y + bb.maxPoint.y) / 2
                ok, normal = f.evaluator.getNormalAtPoint(
                    adsk.core.Point3D.create(cx, cy, cz)
                )
                if ok and normal.z > 0.9:
                    front_face = f
                    break

        # Fallback: use an offset plane at z=SHIN_HEIGHT
        if not front_face:
            planes      = comp.constructionPlanes
            plane_input = planes.createInput()
            offset_val  = adsk.core.ValueInput.createByReal(SHIN_HEIGHT)
            plane_input.setByOffset(xy_plane, offset_val)
            vent_plane  = planes.add(plane_input)
        else:
            vent_plane = front_face

        sk_vents = sks.add(vent_plane)
        sk_vents.name = "VentHoles"
        circles = sk_vents.sketchCurves.sketchCircles

        # Distribute vent holes evenly across the guard body
        y_start   = L * 0.15 
        y_end     = L * 0.88
        y_spacing = (y_end - y_start) / max(VENT_ROWS - 1, 1)

        for row in range(VENT_ROWS):
            y_pos = y_start + row * y_spacing

            # Compute guard half-width at this y position (linear taper)
            t = y_pos / L
            hw_here = hw_bot + (hw_top - hw_bot) * t
            x_margin = hw_here * 0.15  # keep some margin inside boundary

        for column in range(VENT_COLUMNS):
            x_pos = x_start + column * x_spacing

            # Check if point is inside tapered "portal"
            if abs(x_pos) <= (hw_here - x_margin):
                position = (x_pos, y_pos)
                set(position)

        vent_profs = adsk.core.ObjectCollection.create()
        for i in range(sk_vents.profiles.count):
            vent_profs.add(sk_vents.profiles.item(i))

        if vent_profs.count > 0:
            cut_input = exts.createInput(
                sk_vents.profiles.item(0),
                adsk.fusion.FeatureOperations.CutFeatureOperation
            )
            # Collect all vent profiles
            all_vents = adsk.core.ObjectCollection.create()
            for i in range(sk_vents.profiles.count):
                all_vents.add(sk_vents.profiles.item(i))
            cut_input.profile = all_vents
            cut_input.setAllExtent(adsk.fusion.ExtentDirections.NegativeExtentDirection)
            cut_input.participantBodies = [body]
            exts.add(cut_input)

        # 6. EDGE FILLETS – smooth all edges
        edge_col = adsk.core.ObjectCollection.create()
        for edge in body.edges:
            edge_col.add(edge)

        if edge_col.count > 0:
            fil_input = fils.createInput()
            fil_input.addConstantRadiusEdgeSet(
                edge_col,
                adsk.core.ValueInput.createByReal(EDGE_RADIUS),
                True
            )
            fils.add(fil_input)

        # 7. APPEARANCE – assign a material color
        try:
            appearances = des.appearances
            appear      = None
            for a in appearances:
                if "plastic" in a.name.lower():
                    appear = a
                    break
            if appear:
                body.appearance = appear
        except Exception:
            pass  # Appearance is cosmetic; skip silently if unavailable

        # Fit the view
        app.activeViewport.fit()

        ui.messageBox(
            "✅  Shin Guard created successfully!\n\n"
            f"  Length:        {SHIN_LENGTH} cm\n"
            f"  Width (top):   {SHIN_WIDTH_TOP} cm\n"
            f"  Width (ankle): {SHIN_WIDTH_BOTTOM} cm\n"
            f"  Shell thickness: {THICKNESS} cm\n"
            f"  Vent holes:    {VENT_ROWS} × {VENT_COLS}\n\n"
            "Tip: Edit the PARAMETERS section at the top of the\n"
            "script to customise size, thickness, and vent count."
        )

    except Exception:
        if ui:
            ui.messageBox(f"Script failed:\n{traceback.format_exc()}")
