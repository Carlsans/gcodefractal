# gcodefractal: how it works, what worked, what did not

Written from the code and from the output that sits next to it: 339 PNG renders, 44 G-code files (the largest, `anaplexity.gcode`,
is 556 MB and was written in September 2026), 78 statistics files and 15 animated GIFs. Statements marked *(inferred)* are conclusions from
that evidence, not recorded results.

## The idea

Turn a coloured fractal image into a drawing made by a large pen plotter (894 x 865 mm canvas, driven by Marlin-style G-code) that only
has **six felt pens** and a **Z axis that can press harder or lift**. A full-colour picture is reproduced by **overlaying pens**: every
combination of the six pens (2^6 = 63 non-empty mixes) is a distinct colour on paper, so a palette of up to 63 colours plus white can be drawn.

## Pipeline

| Stage | File | Notes |
|---|---|---|
| Palette | `ColorInterpreter.getColorslistfromimage` | Collect the distinct colours of the image, sort them by brightness (sum of R, G, B). |
| Pen mixes | `ColorInterpreter.getPencolorMixlist` | Enumerate all 2^6 subsets. Keep a subset only if its size is within the smallest `saturationconstraint` of its pens (a pale pen may only be mixed with few others) and if it has no forbidden pair (7 pairs such as green+pink, red+purple). |
| Assignment | `associatepenandimagecolors` | Walk the sorted palette and give each stretch of it to the next pen mix. The stretch length is proportional to the average **distribution factor** of the pens in the mix. |
| Channels | `splitbypencolors` | One boolean image per pen: pixel on if its colour is assigned to a mix containing the pen. Pixels below `donotdrawbelow` (0.3) are dropped. |
| Preview | `MatrixtoGcode.generatepreview` | Composite using the **measured** colour of each pen combination (`Configuration.setcolormixlist`, 63 hand-measured RGB values). |
| Seed search | `generatemultiplerandompreviews` | The distribution factors and the palette rotation come from a random seed. The program renders up to 500 previews and the user types the number of the one they like. |
| Strokes | `rust/matrix_to_gcode` (`random_lines`) | See below. |
| G-code | `GcodeInterpreter.py`, `gcode_writer.rs` | Header, one block per pen with a pen-change routine (`M226 P121` pause), progress on the LCD (`M117`), and wiping. |
| Post-processing | `gcode/`, `simplefuse/`, `splitsvg.py` | Fuse files, replace needless full lifts by low lifts, split large SVGs. |

### The random-lines solver

Pixels to draw are `true` in a 2D array. Repeatedly: pick a random direction among 8, pick a maximum length between 3 and 4 mm, then search rings of increasing radius
around the pen for the start cell whose ray in that direction covers the most pixels; draw that stroke, clear the pixels, and continue from its end.
The pen is changed (refilled) after a fixed fraction of the pixels is done. Short travels lift the pen only to 2.5 mm, long ones to 7 mm.
Writing it in Rust (`ndarray`, `ndarray-npy`) brought the run time of full-size plots (3576 x 3460 pixels) to something workable *(inferred: the Python
alternatives remained in the code)*.

## What worked

- **Overlaying pens for colour.** Six pens give 63 colours, enough to render the palette of a fractal rendering.
- **Measured mix colours.** The 63 RGB values in `Configuration` replace a colour model. They make the preview match the paper.
- **Previews over many seeds.** The assignment of palette stretches to mixes is arbitrary, so looking at hundreds of previews and choosing
  one is cheaper than modelling "a good assignment".
- **Short, randomly oriented strokes.** Max line length went from 8-15 mm down to 3-4 mm (a comment in `Configuration` records "etait (8,15)").
  Short random lines hide the stroke direction and pen wear, and they let the solver fill awkward shapes.
- **A Rust solver behind a file interface.** Python writes `array.npy` and `config.json`, Rust writes `topython.gcode`: simple, and the Rust part
  can be run on its own.
- **Z-height tiers for travel.** Skipping the lift between adjacent strokes, a low lift for short moves, a high lift for long ones
  removes most of the pen-up/down time.

## What did not work (or was set aside)

- **Hilbert-curve fill.** Visiting pixels along a Hilbert curve gives one continuous pen path, but it needs a precomputed 4096 x 4096 index (a
  67 MB file) and per-channel offsets from `MatriceEscalier`; the resulting G-code files were 10-60 MB for tests. The call is commented out in
  `MatrixtoGcode` and `resolutionmethod = "random_lines"` replaced it.
- **Scan lines (`splittedlines`).** Row-by-row runs via `LineTravelOptimizer`: predictable but long travels and slow in Python.
- **Travel optimisation by gradient descent** (`ImageTravelOptimizer`): meant to cut the image into a grid whose cuts minimise pen travel. Its configuration
  parameters (`traveloptimizationcutscount`, `traveloptimizationmax_epoch`) were commented out of `Configuration`, so it cannot run from the main script.
- **Machine compensation.** `machinecompensationx/y` hold notes such as `(-.2,.6)` then `(-.6,.7)(trop)` and `(-.5,.5)`: the offsets
  between drawing directions needed hand calibration, and large values were "too much".
- **Pen channel offsets.** Earlier versions drew each pen at a small offset (`xchanneladjustment`) to avoid ink overlap; with random lines this is gone.
- **Grey levels as pressure** (`extrapolatez`, `cubicregression`): force-dependent Z is commented out; only "on/off" survives, with `zmaxforce` unused.
- **Windows-only helper scripts.** `splitsvg`, `simplefuse` and `fusegcode` use `os.getcwd() + "\\"` and `.bat` launchers.
- **Interactive run.** The main script blocks on `input()` ("Continue ? (Y,n)", "Select a seed") and, imported, runs the whole job.
- **Calibration by hand.** The mix colours and the `PenColorChartTest` chart were produced and read manually; there is no automated colour measurement.

## Lessons

1. Break the colour problem into "which palette entry goes to which pen mix" and "what does that mix look like". Measure the second once, search the first by preview.
2. Keep strokes short and randomly oriented when pens are felt tips.
3. Spend the effort on travel: lift heights and ordering decide the plot time more than the line algorithm.
4. Keep an interface file between the exploratory Python and the fast solver, so the solver can be rewritten without touching the rest.
5. Put the job's questions behind a function, not `input()`.

## Running the original code

`src/matrixtogcode/MatrixtoGcode.py` (run from the repository root; modules import `src.X`). Build the solver first:
`cd src/rust/matrix_to_gcode && cargo build --release`. Edit paths and settings in `Configuration.py`; the image path is `images/<name>.png`.
The script writes `<name>.gcode` and `<name>stats.txt` next to the image.
