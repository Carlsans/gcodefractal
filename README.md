# gcodefractal

Turn a coloured fractal image into G-code for a six-pen plotter. Colours come from **overlaying pens**: the 63 combinations of six pens
reproduce a palette; each pen's pixels are covered with short random strokes found by a solver (Python, or Rust for large plots).

- How it works, what worked and what did not: [docs/PROJECT.md](docs/PROJECT.md)
- Features that were tried and dropped: [docs/UNUSED_FEATURES.md](docs/UNUSED_FEATURES.md)

## GUI

```
pip install -r requirements-gui.txt
python -m gui.app
```

1. **Image and pens**: open an image, choose the canvas resolution, edit the pens, preview a seed or compare several.
2. **Plot (G-code)**: choose the stroke method, set speeds and heights, generate, scrub through the strokes, save the G-code.
3. **Tools (legacy scripts)**: fuse and optimise G-code, split an SVG, build a pen colour chart.

The default canvas is 25 % of full size (a 224 x 216 pixel grid at 4 mm) so that previews are quick; a full-size plot uses 100 % and the Rust solver:
`cd src/rust/matrix_to_gcode && cargo build --release` (or the *Build Rust solver* button).

The G-code uses `M226 P121` (pause for a pen change) and `M117` (LCD message), Marlin commands. Check heights, speeds and the Z offset against your machine before running.

## Original script

`src/matrixtogcode/MatrixtoGcode.py` (it runs the whole job when started and asks questions on the terminal).

## License

[PolyForm Noncommercial 1.0.0](LICENSE). Personal, research and hobby use are allowed; commercial use is not.

## Launch the GUI

Linux: `./run.sh`  
Windows: `run_win.bat`

The first run creates a `.venv` and installs `requirements-gui.txt`; later runs start immediately.
