import adsk.core, adsk.fusion, adsk.cam, traceback

def run(context):
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = app.activeProduct

        rootComp = design.rootComponent

        # Create a new sketch on the XY plane
        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        sketch = sketches.add(xyPlane)

        # Draw an arc (shin curvature)
        arcs = sketch.sketchCurves.sketchArcs
        center = adsk.core.Point3D.create(0, 0, 0)
        start = adsk.core.Point3D.create(-2, 0, 0)
        end = adsk.core.Point3D.create(2, 0, 0)
        arc = arcs.addByThreePoints(start, center, end)

        # Draw vertical lines to create profile
        lines = sketch.sketchCurves.sketchLines
        leftLine = lines.addByTwoPoints(start, adsk.core.Point3D.create(-2, 8, 0))
        rightLine = lines.addByTwoPoints(end, adsk.core.Point3D.create(2, 8, 0))
        topLine = lines.addByTwoPoints(leftLine.endSketchPoint, rightLine.endSketchPoint)

        # Create profile
        prof = sketch.profiles.item(0)

        # Extrude the profile (thin shell)
        extrudes = rootComp.features.extrudeFeatures
        extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

        distance = adsk.core.ValueInput.createByReal(0.3)
        extInput.setDistanceExtent(False, distance)

        extrude = extrudes.add(extInput)

        # Shell the body to make it lightweight
        shellFeats = rootComp.features.shellFeatures
        faces = adsk.core.ObjectCollection.create()
        faces.add(extrude.endFaces[0])

        shellInput = shellFeats.createInput(faces, False)
        shellInput.insideThickness = adsk.core.ValueInput.createByReal(0.1)
        shellFeats.add(shellInput)

        # Create holes for straps
        holeSketch = sketches.add(xyPlane)
        circles = holeSketch.sketchCurves.sketchCircles

        circles.addByCenterRadius(adsk.core.Point3D.create(-1.5, 4, 0), 0.2)
        circles.addByCenterRadius(adsk.core.Point3D.create(1.5, 4, 0), 0.2)

        holeProf = holeSketch.profiles

        for i in range(holeProf.count):
            holeExtInput = extrudes.createInput(holeProf.item(i),
                adsk.fusion.FeatureOperations.CutFeatureOperation)
            holeExtInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(1))
            extrudes.add(holeExtInput)

        ui.messageBox('Shin Guard Model Created!')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))