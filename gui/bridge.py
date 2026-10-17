"""Glue between the PySide6 GUI and the gcodefractal engine.

``src/matrixtogcode/MatrixtoGcode.py`` runs the whole job as soon as it is imported and asks questions on stdin, so the GUI
cannot use it. The colour handling (``Configuration``, ``ColorInterpreter``) is imported from the engine; the
steps that were tied to ``input()`` and to files (preview, seed selection, the random-lines solver that lives in Rust, the
G-code writer) are re-implemented here with the same logic. The Rust solver is used when it has been built.
"""
import contextlib
import io
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from PIL.Image import Resampling

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.matrixtogcode.ColorInterpreter import ColorInterpreter  # noqa: E402
from src.matrixtogcode.Configuration import Configuration  # noqa: E402
from src.matrixtogcode.LineTravelOptimizer import LineTravelOptimizer  # noqa: E402

RUST_BIN = REPO / "src" / "rust" / "matrix_to_gcode" / "target" / "release" / "matrix_to_gcode"
RUST_DIR = REPO / "src" / "rust" / "matrix_to_gcode"
METHODS = [("random_lines", "Random lines (active method)"),
           ("splittedlines", "Scan lines, row by row (legacy: LineTravelOptimizer)"),
           ("hilbert", "Hilbert curve walk (legacy: Hilbert.py, regenerated instead of loaded from a 67 MB file)")]


@contextlib.contextmanager
def quiet():
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def new_conf(canvas_scale=1.0):
    """Engine Configuration without its file side effects, at canvas_scale * (894 x 865) pixels."""
    Configuration.generateRustConfigFile = lambda self: None
    with quiet():
        conf = Configuration()
    set_resolution(conf, canvas_scale)
    return conf


def set_resolution(conf, canvas_scale):
    conf.canvasresolution = (max(8, int(round(conf.canvasmax[0] * canvas_scale))),
                             max(8, int(round(conf.canvasmax[1] * canvas_scale))))
    conf.xyresolution = (conf.canvasmax[0] / (conf.canvasresolution[0] + 1),
                         conf.canvasmax[1] / (conf.canvasresolution[1] + 1))
    conf.channelnumber = len(conf.pencolorlist)


def set_resolution_exact(conf, width, height):
    conf.canvasresolution = (width, height)
    conf.xyresolution = (conf.canvasmax[0] / (width + 1), conf.canvasmax[1] / (height + 1))


def pen_table(conf):
    return [(p.colorname, tuple(p.rgb), p.saturationconstraint, float(p.distributionfactor)) for p in conf.pencolorlist]


def apply_seed(conf, seed):
    """Per-pen distribution factors drawn from the seed, as Configuration.setcolorlist does (without rebuilding the pens)."""
    torch.manual_seed(seed)
    factors = torch.rand(len(conf.pencolorlist))
    for pen, f in zip(conf.pencolorlist, factors):
        pen.distributionfactor = f


# ---------------------------------------------------------------- image -> pen channels
def load_image(conf, path):
    image = Image.open(path).resize(conf.canvasresolution, resample=Resampling.NEAREST).convert("RGB")
    return image


def image_to_channels(conf, image, shuffle_seed=None):
    """MatrixtoGcode.importimage: (pens, width, height) float tensor of 0/1, plus the interpreter."""
    colors = ColorInterpreter(conf, shuffle_seed)
    with quiet():
        colors.getColorslistfromimage(image)
    arr = np.asarray(image, dtype=np.uint8).transpose(2, 0, 1)
    tensor = torch.from_numpy(arr.copy()).transpose(1, 2)
    with quiet():
        tensor = colors.splitbypencolors(tensor)
    if torch.max(tensor) > 1:
        tensor = tensor.float() / 255
    tensor = torch.where(tensor < conf.donotdrawbelow, torch.tensor(0.0), tensor)
    return tensor, colors


def channel_masks(tensor):
    return [(tensor[i] >= 0.5).numpy() for i in range(tensor.shape[0])]


def preview(conf, tensor):
    """MatrixtoGcode.generatepreview: composite of the measured colour of every pen combination."""
    mask = tensor.to(torch.bool)
    height, width = mask.shape[1], mask.shape[2]
    out = torch.zeros((3, height, width))
    for mix in conf.colorlistmix:
        binary = mix.binary.reshape(-1, 1, 1).expand(-1, height, width)
        selected = (torch.bitwise_xor(mask, binary).sum(dim=0) == 0).unsqueeze(0).expand(3, -1, -1)
        out += selected * torch.tensor(mix.rgb, dtype=torch.float32).reshape(3, 1, 1)
    arr = (out / 255).clamp(0, 1).permute(1, 2, 0).numpy()
    img = Image.fromarray((arr * 255).astype(np.uint8)).transpose(Image.Transpose.ROTATE_180)
    return np.asarray(img)


def seed_preview(conf, image, seed, mix_colors=True):
    apply_seed(conf, seed)
    tensor, colors = image_to_channels(conf, image, seed if mix_colors else None)
    return preview(conf, tensor), tensor


def channel_coverage(tensor, conf):
    return {conf.pencolorlist[i].colorname: float(tensor[i].mean()) for i in range(tensor.shape[0])}


# ---------------------------------------------------------------- random-lines solver (port of rnd_lines_algo.rs)
DIRECTIONS = [(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0), (-1, -1), (0, -1), (1, -1)]


class RandomLines:
    def __init__(self, mask, length_min, length_max, rng=random):
        self.w, self.h = mask.shape
        self.cells = bytearray(np.ascontiguousarray(mask, dtype=np.uint8).tobytes())
        self.rng = rng
        self.min, self.max = length_min, length_max
        self.pos = (rng.randrange(self.w), rng.randrange(self.h))
        self.left = int(mask.sum())

    def inbound(self, i, j):
        return 0 <= i < self.w and 0 <= j < self.h

    def ring(self, n, centre):
        if n == 0:
            return [centre]
        cells, (pi, pj) = [], (-n, -n)
        for di, dj in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            for _ in range(2 * n):
                pi += di; pj += dj
                i, j = pi + centre[0], pj + centre[1]
                if 0 <= i < self.w and 0 <= j < self.h:
                    cells.append((i, j))
        return cells

    def trace(self, d, start, limit):
        i, j = start
        value = self.cells[i * self.h + j]
        count_i = count_j = 0
        while value:
            i += d[0]; j += d[1]
            count_i += abs(d[0]); count_j += abs(d[1])
            if 0 <= i < self.w and 0 <= j < self.h:
                value = self.cells[i * self.h + j]
            else:
                value = 0
                i -= d[0]; j -= d[1]
            if count_i > limit[0] or count_j > limit[1]:
                value = 0
        return start, (i, j), math.hypot(start[0] - i, start[1] - j)

    def step(self):
        d = self.rng.choice(DIRECTIONS)
        limit = (self.rng.randint(self.min[0], self.max[0]), self.rng.randint(self.min[1], self.max[1]))
        best, best_cost, n = ((-1, -1), (-1, -1)), -1e18, 0
        while True:
            cells = self.ring(n, self.pos)
            if not cells and n > max(self.w, self.h):
                return best
            for cell in cells:
                a, b, length = self.trace(d, cell, limit)
                if length > best_cost:
                    best_cost, best = length, (a, b)
            if best_cost > 0:
                return best
            n += 1
            if n > max(self.w, self.h):
                return best

    def remove(self, ray):
        (i0, j0), (i1, j1) = ray
        di = (i1 > i0) - (i1 < i0)
        dj = (j1 > j0) - (j1 < j0)
        i, j = i0, j0
        if self.cells[i * self.h + j]:
            self.cells[i * self.h + j] = 0
            self.left -= 1
        while not (i == i1 and j == j1):
            if self.cells[i * self.h + j]:
                self.cells[i * self.h + j] = 0
                self.left -= 1
            i += di; j += dj


class Writer:
    """gcode_writer.rs: converts index rays to G-code lines, with the same heights and speeds."""

    def __init__(self, conf):
        self.conf = conf
        self.ps = (conf.canvasmax[0] / conf.canvasresolution[0], conf.canvasmax[1] / conf.canvasresolution[1])
        self.cur = (0, 0)
        self.strokes = []

    @staticmethod
    def fmt(v):
        s = f"{v:.2f}".rstrip("0").rstrip(".")
        return s if s else "0"

    def position(self, idx):
        return idx[0] * self.ps[0], idx[1] * self.ps[1]

    def travel(self, a, b):
        pa, pb = self.position(a), self.position(b)
        dist = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
        if dist <= math.hypot(self.ps[0], self.ps[1]) + 0.01:
            return ""
        z = self.conf.shorttravelz if dist < self.conf.shorttravelmaxdistance else self.conf.safez
        return f"G1 Z{self.fmt(z)} {self.fmt(self.conf.zspeed)}\n"

    def draw(self, ray, pen=0, rng=random):
        a, b = ray
        d = ((b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1]))
        if d == (0, 0):
            while d == (0, 0):
                d = (rng.randint(-1, 1), rng.randint(-1, 1))
        pa, pb = self.position(a), self.position(b)
        start = (pa[0] - self.ps[0] * d[0] / 2, pa[1] - self.ps[1] * d[1] / 2)
        end = (pb[0] + self.ps[0] * d[0] / 2, pb[1] + self.ps[1] * d[1] / 2)
        out = self.travel(self.cur, a)
        self.cur = b
        out += f"G1 X{self.fmt(start[0])} Y{self.fmt(start[1])} F{self.fmt(self.conf.travelspeed)}\n"
        out += f"G1 Z0 {self.fmt(self.conf.zspeed)}\n"
        out += f"G1 X{self.fmt(end[0])} Y{self.fmt(end[1])} F{self.fmt(self.conf.xyspeed)}\n"
        self.strokes.append((start[0], start[1], end[0], end[1], pen))
        return out

    def change_pen(self):
        c = self.conf
        self.cur = (c.canvasresolution[0] // 2, c.canvasresolution[1] // 2)
        return (f"G1 Z{self.fmt(c.change_pen_height)}\nG1 X{c.canvasmax[0] / 2} Y{c.canvasmax[1] / 2}\nM226 P121\n")


def header(conf):
    return f"G1 Z15\nM851 Z{Writer.fmt(conf.zoffset)}\n"


def tool_change(conf, name, coverage):
    return (f"; Processing {name}\nM117 {name} M={int(coverage * 100)}%\nG1 Z35\n"
            f"G1 X{Writer.fmt(conf.canvasmax[1] / 2)} Y{Writer.fmt(conf.canvasmax[0] / 2)}\nM226 P121\n")


def plot_random_lines(conf, mask, writer, pen, job=None, log=print, use_rust=False):
    """One pen channel -> G-code string, using the Python port or the compiled Rust solver."""
    if use_rust and RUST_BIN.exists():
        return plot_rust(conf, mask, writer, pen, log)
    lmin = [max(1, int(conf.max_line_length_range[0] / writer.ps[0])), max(1, int(conf.max_line_length_range[0] / writer.ps[1]))]
    lmax = [max(lmin[0], int(conf.max_line_length_range[1] / writer.ps[0])), max(lmin[1], int(conf.max_line_length_range[1] / writer.ps[1]))]
    algo = RandomLines(mask, lmin, lmax)
    total = max(algo.left, 1)
    change_every = int(conf.change_pen_ratio * mask.size)
    next_change, steps, out, failures = change_every, 0, [], 0
    while algo.left > 0:
        if job is not None and job.should_stop():
            break
        if steps % 200 == 0:
            out.append(f";num_steps {steps} pixel left : {algo.left}\nM117 Progress {(total - algo.left) * 100 / total:.2f}%\n")
            if change_every and (total - algo.left) > next_change:
                out.append("M117 Changing pen\n" + writer.change_pen())
                next_change += change_every
            if steps % 5000 == 0:
                log(f"  pen {pen}: {algo.left} pixels left")
        ray = algo.step()
        if ray == ((-1, -1), (-1, -1)):
            failures += 1
            if failures > 50:
                break
            continue
        out.append(writer.draw(ray, pen))
        algo.remove(ray)
        algo.pos = ray[1]
        steps += 1
    return "".join(out)


def plot_rust(conf, mask, writer, pen, log):
    with tempfile.TemporaryDirectory() as tmp:
        np.save(os.path.join(tmp, "array.npy"), mask.astype(bool))
        import json
        json.dump({"resolutionX": conf.canvasresolution[0], "resolutionY": conf.canvasresolution[1],
                   "sizeX": conf.canvasmax[0], "sizeY": conf.canvasmax[1], "xyspeed": conf.xyspeed,
                   "travelspeed": conf.travelspeed, "safez": conf.safez, "shorttravelz": conf.shorttravelz,
                   "shorttravelmaxdistance": conf.shorttravelmaxdistance, "zspeed": conf.zspeed,
                   "max_line_length_min": conf.max_line_length_range[0], "max_line_length_max": conf.max_line_length_range[1],
                   "change_pen_ratio": conf.change_pen_ratio, "change_pen_height": conf.change_pen_height},
                  open(os.path.join(tmp, "config.json"), "w"))
        result = subprocess.run([str(RUST_BIN), tmp], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("Rust solver failed: " + result.stderr[-300:])
        text = open(os.path.join(tmp, "topython.gcode")).read()
    writer.strokes.extend(parse_strokes(text, pen))
    return text


def parse_strokes(text, pen=0):
    """Pen-down XY moves of a G-code text -> (x0, y0, x1, y1, pen)."""
    strokes, x = [], None
    down, last = False, None
    for line in text.splitlines():
        line = line.split(";")[0].strip()
        if not line.startswith("G1"):
            continue
        z = re.search(r"Z(-?[\d.]+)", line)
        if z:
            down = float(z.group(1)) <= 0.5
        mx, my = re.search(r"X(-?[\d.]+)", line), re.search(r"Y(-?[\d.]+)", line)
        if mx or my:
            nx = float(mx.group(1)) if mx else (last[0] if last else 0)
            ny = float(my.group(1)) if my else (last[1] if last else 0)
            if down and last is not None:
                strokes.append((last[0], last[1], nx, ny, pen))
            last = (nx, ny)
    return strokes


def plot_scanlines(conf, mask, writer, pen, job=None, log=print):
    """Legacy method: LineTravelOptimizer extracts horizontal runs, drawn row by row."""
    with quiet():
        lines = LineTravelOptimizer(conf).optimizetensor(torch.from_numpy(mask.astype(np.uint8)))
    out = []
    pos = None
    for k in range(lines.shape[0]):
        if job is not None and job.should_stop():
            break
        x0, x1, row = int(lines[k, 0]), int(lines[k, 1]), int(lines[k, 2])
        y = row * writer.ps[1]
        xa, xb = x0 * writer.ps[0], x1 * writer.ps[0]
        short = pos is not None and (pos[0] - xa) ** 2 + (pos[1] - y) ** 2 < conf.shorttravelmaxdistance ** 2
        adjacent = pos is not None and abs(pos[0] - xa) <= writer.ps[0] and abs(pos[1] - y) <= writer.ps[1]
        if adjacent:
            lift = ""
        else:
            lift = f"G1 Z{Writer.fmt(conf.shorttravelz if short else conf.safez)} F{conf.zspeed}\n"
        out.append(f"{lift}G1 X{Writer.fmt(xa)} Y{Writer.fmt(y)} F{Writer.fmt(conf.xyspeed)}\nG1 Z0 F{conf.zspeed}\n"
                   f"G1 X{Writer.fmt(xb)} F{Writer.fmt(conf.xyspeed)}\n")
        writer.strokes.append((xa, y, xb, y, pen))
        pos = (xb, y)
    return "".join(out)


# ---------------------------------------------------------------- Hilbert walk
def hilbert_order(order):
    """Hilbert index of every cell of a 2**order grid (vectorised xy2d)."""
    n = 1 << order
    x, y = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    d = np.zeros_like(x)
    s = n // 2
    while s > 0:
        rx = ((x & s) > 0).astype(np.int64)
        ry = ((y & s) > 0).astype(np.int64)
        d += s * s * ((3 * rx) ^ ry)
        mirror = (ry == 0) & (rx == 1)
        x = np.where(mirror, n - 1 - x, x)
        y = np.where(mirror, n - 1 - y, y)
        swap = ry == 0
        x, y = np.where(swap, y, x), np.where(swap, x, y)
        s //= 2
    return d


def plot_hilbert(conf, mask, writer, pen, job=None, log=print):
    """Legacy method: visit the selected pixels in Hilbert-curve order; neighbours that continue in one direction share a stroke."""
    w, h = mask.shape
    order = max(1, math.ceil(math.log2(max(w, h))))
    index = hilbert_order(order)[:w, :h]
    ii, jj = np.nonzero(mask)
    sel = np.argsort(index[ii, jj], kind="stable")
    ii, jj = ii[sel].tolist(), jj[sel].tolist()
    out, k = [], 0
    while k < len(ii):
        if job is not None and job.should_stop():
            break
        start, direction = k, None
        while k + 1 < len(ii) and k - start < 40:
            step = (ii[k + 1] - ii[k], jj[k + 1] - jj[k])
            if max(abs(step[0]), abs(step[1])) != 1 or (direction is not None and step != direction):
                break
            direction = step
            k += 1
        out.append(writer.draw(((ii[start], jj[start]), (ii[k], jj[k])), pen))
        k += 1
    return "".join(out)


# ---------------------------------------------------------------- cut-grid optimisation (ImageTravelOptimizer)
class _Stats:
    def printandsave(self, *args):
        pass


def optimise_cuts(conf, mask, cuts=4, epochs=40):
    """Legacy ImageTravelOptimizer: gradient descent on a grid of cuts that lowers the estimated travel."""
    from src.matrixtogcode.ImageTravelOptimizer import ImageTravelOptimizer
    conf.traveloptimizationcutscount = cuts
    conf.traveloptimizationmax_epoch = epochs
    opt = ImageTravelOptimizer(conf, _Stats())
    opt.currentcolor = "gui"
    tensor = torch.from_numpy(mask.astype(np.float32))
    with quiet():
        opt.optimizecuts(tensor)
    cut_idx = opt.cutstensortoindex(opt.cutstensor)
    xs = [0] + sorted(set(int(v) for v in cut_idx[:, 0])) + [mask.shape[0]]
    ys = [0] + sorted(set(int(v) for v in cut_idx[:, 1])) + [mask.shape[1]]
    return xs, ys


# ---------------------------------------------------------------- whole job
def run_plot(conf, masks, names, method="random_lines", cut_grid=None, use_rust=False, job=None, log=print):
    writer = Writer(conf)
    parts = [header(conf)]
    per_pen = {}
    for pen, (mask, name) in enumerate(zip(masks, names)):
        if job is not None and job.should_stop():
            break
        if not mask.any():
            log(f"{name}: empty, skipped")
            continue
        log(f"{name}: {int(mask.sum())} pixels")
        parts.append(tool_change(conf, name, float(mask.mean())))
        text = ""
        regions = [(0, mask.shape[0], 0, mask.shape[1])]
        if cut_grid:
            xs, ys = cut_grid
            regions = [(xs[a], xs[a + 1], ys[b], ys[b + 1]) for a in range(len(xs) - 1) for b in range(len(ys) - 1)]
        for (x0, x1, y0, y1) in regions:
            sub = np.zeros_like(mask)
            sub[x0:x1, y0:y1] = mask[x0:x1, y0:y1]
            if not sub.any():
                continue
            if method == "random_lines":
                text += plot_random_lines(conf, sub, writer, pen, job, log, use_rust)
            elif method == "splittedlines":
                text += plot_scanlines(conf, sub, writer, pen, job, log)
            elif method == "hilbert":
                text += plot_hilbert(conf, sub, writer, pen, job, log)
            else:
                raise ValueError(method)
        per_pen[name] = text
        parts.append("G1 Z15\n" + text + "G1 Z15\n")
    parts.append("G1 Z15\n")
    return "".join(parts), writer.strokes, per_pen


def render_strokes(strokes, conf, pen_rgb, width=900, upto=None):
    scale = width / conf.canvasmax[0]
    height = int(conf.canvasmax[1] * scale)
    img = Image.new("RGB", (width, height), (245, 242, 235))
    draw = ImageDraw.Draw(img)
    for (x0, y0, x1, y1, pen) in strokes[:upto]:
        draw.line([(x0 * scale, y0 * scale), (x1 * scale, y1 * scale)], fill=tuple(pen_rgb[pen % len(pen_rgb)]), width=1)
    return np.asarray(img)


def build_rust(log=print):
    """cargo build --release for the random-lines solver."""
    result = subprocess.run(["cargo", "build", "--release"], cwd=RUST_DIR, capture_output=True, text=True)
    log(result.stdout[-400:] + result.stderr[-600:])
    return RUST_BIN.exists()


# ---------------------------------------------------------------- tools (fusegcode, optimizegcode, splitsvg, bounds, chart)
def add_progress(text):
    lines = text.splitlines()
    total, out, shown = max(len(lines), 1), [], 1
    for i, line in enumerate(lines):
        out.append(line)
        pct = math.floor(i / total * 100)
        if pct > shown:
            shown = pct
            out.append(f"\nM117 Progress: {pct}% \n")
    return "\n".join(out) + "\n"


def fuse_gcode(files, output, split=False, pen_change_each=True):
    """gcode/fusegcode.py: concatenate files with a pen-change routine and a progress display."""
    up = "G1 Z15 F30000; S0"
    data = ""
    for n, file in enumerate(files):
        size = os.path.getsize(file)
        part = f"\n;File number = {n}\n\nM300 S880 P5000\nM117 Sz:{round(size / 1024)}Kb F:{n + 1}/{len(files)}\n"
        if pen_change_each:
            part += "\nG1 Z25\nG1 X450 Y430\nG1 Z60\nM226 P121\nG1 Z20\nM226 P121\n "
        content = open(file).read()
        if split:
            lines, out, mid, seen, find = content.splitlines(), "", len(content.splitlines()) // 2, 0, False
            for line in lines:
                seen += 1
                out += line + "\n"
                if seen == mid:
                    find = True
                if find and line == up:
                    find = False
                    out += "\nG1 Z25\nG1 X480 Y430\nG1 Z20\nM226 P121\n "
            content = out
        part += content + "\n"
        data += add_progress(part)
    with open(output, "w") as handle:
        handle.write(data)
    return len(data)


def simple_fuse(files, output):
    """simplefuse/simplefuse.py: concatenate with a lift between files."""
    data = ""
    for n, file in enumerate(files):
        data += f"\n;File sub number = {n}\nG1 Z15 F30000; S0\n" + open(file).read() + "\n"
    open(output, "w").write(data)


def optimize_gcode(path, output, skip_first=100, threshold=10.0):
    """gcode/optimizegcode.py: replace full lift-ups before short travels with a low lift."""
    lines = open(path).read().splitlines()
    out, x, y, replaced = [], 0.0, 0.0, 0

    def next_xy(start):
        nx = ny = None
        for line in lines[start:]:
            mx, my = re.search(r"X(-?[\d.]+)", line), re.search(r"Y(-?[\d.]+)", line)
            nx = float(mx.group(1)) if mx and nx is None else nx
            ny = float(my.group(1)) if my and ny is None else ny
            if nx is not None and ny is not None:
                return nx, ny
        return 1e9, 1e9

    for idx, line in enumerate(lines):
        if idx < skip_first:
            out.append(line)
            continue
        if "G1 Z15" in line:
            nx, ny = next_xy(idx)
            dist = math.hypot(x - nx, y - ny)
            if dist < threshold:
                out.append(f"G1 Z3 F30000 ; travel={dist:.3f}")
                replaced += 1
            else:
                out.append(f"{line} ; travel={dist:.3f}")
            continue
        out.append(line)
        mx, my = re.search(r"X(-?[\d.]+)", line), re.search(r"Y(-?[\d.]+)", line)
        x = float(mx.group(1)) if mx else x
        y = float(my.group(1)) if my else y
    out.append("G1 Z15 F30000; S0 \nG1 F3000\n;File optimized low Z travel\n")
    open(output, "w").write("\n".join(out))
    return replaced


def gcode_bounds(path):
    """Bounding box of X/Y words (what rust/gcode_bounds does)."""
    xs, ys = [], []
    for line in open(path):
        line = line.split(";")[0]
        for m in re.finditer(r"X(-?[\d.]+)", line):
            xs.append(float(m.group(1)))
        for m in re.finditer(r"Y(-?[\d.]+)", line):
            ys.append(float(m.group(1)))
    if not xs or not ys:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def split_svg(svg_path, out_dir, mode="bymaximumsize", count=8, max_kb=512, width_mm=900, height_mm=865):
    """splitsvg.py: split an Inkscape SVG's paths (sorted by colour brightness) into several files."""
    from xml.dom import minidom
    doc = minidom.parse(str(svg_path))
    paths = [[p.getAttribute('d'), p.getAttribute('style'), p.getAttribute('id'),
              p.getAttribute('inkscape:connector-curvature')] for p in doc.getElementsByTagName('path')]
    doc.unlink()

    def brightness(p):
        hexs = p[1][6:12] or "000000"
        try:
            return sum(int(hexs[i:i + 1], 16) for i in (0, 2, 4)) / 3
        except ValueError:
            return 0
    paths.sort(key=brightness)
    if mode == "mixedfiles":
        batches = [sorted(paths[n::count], key=lambda p: int(re.sub(r"\D", "", p[2]) or 0), reverse=True) for n in range(count)]
    elif mode == "similartogether":
        step = max(len(paths) // count, 1)
        batches = [paths[n * step:(n + 1) * step if n < count - 1 else len(paths)] for n in range(count)]
    else:
        batches, cur, size = [], [], 0
        for p in paths:
            cur.append(p); size += len(p[0])
            if size > max_kb * 1024:
                batches.append(cur); cur, size = [], 0
        if cur:
            batches.append(cur)
    os.makedirs(out_dir, exist_ok=True)
    head = f'<svg width="{width_mm}mm" height="{height_mm}mm" viewBox="0 0 {width_mm} {height_mm}">'
    written = []
    for n, batch in enumerate(batches):
        target = Path(out_dir) / f"result{n}.svg"
        with open(target, "w") as f:
            f.write(head)
            for p in batch:
                f.write(f'\n<path style="{p[1]}" d="{p[0]}" id="{p[2]}" inkscape:connector-curvature="{p[3]}" />')
            f.write("</svg>")
        written.append(str(target))
    return written


def color_chart(conf):
    """PenColorChartTest: a calibration sheet with all pen combinations; returns the pen tensor."""
    from src.matrixtogcode.PenColorChartTest import PenColorChartTest

    class _Conf:
        pass
    chart = PenColorChartTest.__new__(PenColorChartTest)
    chart.conf = new_conf(1.0)  # cells are sized in millimetres, so the chart needs ~1 mm pixels
    conf = chart.conf
    chart.pencolorlist = [p.colorname for p in conf.pencolorlist]
    with quiet():
        return chart.generateAllmixtensor().to(torch.float32)
