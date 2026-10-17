# Features that exist in the code but are not part of the final workflow

| # | Feature | Where in the code | Why unused | In the GUI |
|---|---|---|---|---|
| 1 | Hilbert-curve fill | `hilbertcurve/Hilbert.py`, `resolutionmethod = "hilbert"` | Needs a 67 MB cache and offsets; replaced by random lines | Plot > Method "Hilbert curve walk". The curve is regenerated (vectorised) instead of loaded; neighbours that continue in one direction share a stroke |
| 2 | Scan-line fill | `LineTravelOptimizer`, `resolutionmethod = "splittedlines"` | Slow, long travels | Plot > Method "Scan lines" (uses the original `LineTravelOptimizer`) |
| 3 | Grid of optimised cuts | `ImageTravelOptimizer.py` | Its configuration was removed from `Configuration` | Plot > "Legacy: optimised grid of cells" runs the original optimiser on the largest channel and draws each cell separately |
| 4 | Pen colour chart | `PenColorChartTest.py` | Used once to calibrate | Tools > "Pen colour chart"; the chart is sent to the Plot tab |
| 5 | Fuse with progress and pen change | `gcode/fusegcode.py` | Windows paths, `input()` | Tools > Fuse (options for the halfway refill) |
| 6 | Simple fuse | `simplefuse/simplefuse.py` | Same | Tools > Simple fuse |
| 7 | Lift-up optimiser | `gcode/optimizegcode.py` | Superseded by the Z tiers in the writer | Tools > Optimise lift-ups |
| 8 | G-code bounds | `rust/gcode_bounds` | Safety check, called manually | Tools > Bounding box (pure Python) |
| 9 | SVG splitting | `splitsvg.py` | Windows paths, `input()` | Tools > Split SVG (three modes) |
| 10 | Seed-colour mixing | `generatemultiplerandompreviewsandmixcolors` | A flag | Image tab checkbox |
| 11 | Grey-level pen pressure | `GcodeInterpreter.extrapolatez`, `cubicregression` | Commented out | Not integrated: the cubic fit has no calibration data in the repository and the plot method that used it (`drawpixel`) is gone |
| 12 | Per-channel XY offsets | `MatriceEscalier`, `xchanneladjustment` | Only Hilbert and early methods used them | Not integrated: random lines draw every pen on the same grid |
| 13 | Pen-wiping routine | `GcodeInterpreter.wipe` | Needs a wiper at the machine edge | Not integrated: it only applies to the scan-line writer of the original, and the machine-specific coordinates are hard-coded |
| 14 | Deduplicate scripts | `deduplicate/` | Inkscape batch helpers with no Python | Not integrated |
