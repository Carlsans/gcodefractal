"""gcodefractal GUI. Run from the repository root:  python -m gui.app"""
import sys
import threading
import traceback
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QPlainTextEdit, QPushButton, QSlider, QSpinBox, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)

from gui import bridge  # noqa: E402


_JOBS = []


class Job(QThread):
    log = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        _JOBS.append(self)
        self.fn, self._stop = fn, threading.Event()

    def should_stop(self):
        return self._stop.is_set()

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            self.finished_ok.emit(self.fn(self))
        except Exception:
            self.failed.emit(traceback.format_exc())


def to_pixmap(rgb, width=None):
    rgb = np.ascontiguousarray(rgb)
    h, w, _ = rgb.shape
    pix = QPixmap.fromImage(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy())
    return pix.scaledToWidth(width, Qt.SmoothTransformation) if width else pix


class ImageView(QLabel):
    def __init__(self, size=420):
        super().__init__("no image")
        self.setMinimumSize(size, size // 2)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background:#111;color:#888")
        self.rgb = None

    def show_rgb(self, rgb):
        self.rgb = rgb
        self.setPixmap(to_pixmap(rgb, max(min(self.width(), 1000) - 4, 100)))


class LogBox(QPlainTextEdit):
    def __init__(self, height=100):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(400)
        self.setMaximumHeight(height)

    def add(self, text):
        self.appendPlainText(text)


class Runner:
    def __init__(self, log, buttons=()):
        self.log, self.buttons, self.job = log, buttons, None

    def start(self, fn, on_done=None):
        if self.job is not None and self.job.isRunning():
            return
        self.job = Job(fn)
        self.job.log.connect(self.log.add)
        self.job.failed.connect(lambda tb: self.log.add(tb.strip().splitlines()[-1]))
        if on_done:
            self.job.finished_ok.connect(on_done)
        self.job.finished.connect(lambda: [b.setEnabled(True) for b in self.buttons])
        for b in self.buttons:
            b.setEnabled(False)
        self.job.start()

    def stop(self):
        if self.job is not None:
            self.job.stop()


def spin(lo, hi, value, step=1, decimals=None):
    w = QDoubleSpinBox() if decimals is not None else QSpinBox()
    if decimals is not None:
        w.setDecimals(decimals)
    w.setRange(lo, hi); w.setSingleStep(step); w.setValue(value)
    return w


class State:
    """Shared between tabs: engine configuration, the source image and the current pen channels."""
    def __init__(self):
        self.conf = bridge.new_conf(0.25)
        self.image_path, self.image, self.tensor, self.seed = None, None, None, -1


class ImageTab(QWidget):
    channels_ready = Signal()

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.path = QLineEdit(); self.path.setReadOnly(True)
        b_open = QPushButton("Open fractal image..."); b_open.clicked.connect(self.open_image)
        self.scale = spin(2, 100, 25); self.scale.setSuffix(" % of 894 x 865 px")
        self.seed = spin(-1, 100000, -1); self.seed.setToolTip("-1 keeps the configured distribution factors")
        self.mixseed = QCheckBox("Also rotate the colour order with the seed (generatemultiplerandompreviewsandmixcolors)")
        self.mixseed.setChecked(True)
        self.nseeds = spin(1, 500, 12)
        self.pens = QTableWidget(0, 4); self.pens.setHorizontalHeaderLabels(["pen", "RGB", "max pens mixed with it", "distribution factor"])
        self.pens.horizontalHeader().setStretchLastSection(True)
        self.incompatible = QLineEdit(); self.incompatible.setToolTip("pairs that must not be mixed, e.g. green+pink; green+red")
        self.view = ImageView(); self.cover = QLabel("")
        self.grid = QListWidget(); self.grid.setViewMode(QListWidget.IconMode); self.grid.setIconSize(QPixmap(120, 120).size())
        self.grid.setResizeMode(QListWidget.Adjust); self.grid.setMaximumHeight(170)
        self.grid.itemClicked.connect(lambda i: (self.seed.setValue(i.data(Qt.UserRole)), self.apply()))
        self.log = LogBox(70)
        self.b_apply = QPushButton("Preview with this seed"); self.b_apply.clicked.connect(self.apply)
        self.b_seeds = QPushButton("Preview several seeds"); self.b_seeds.clicked.connect(self.many)
        self.runner = Runner(self.log, (self.b_apply, self.b_seeds))

        form = QFormLayout()
        form.addRow(b_open, self.path); form.addRow("Canvas resolution", self.scale)
        form.addRow("Seed", self.seed); form.addRow(self.mixseed); form.addRow("Seeds to compare", self.nseeds)
        form.addRow("Incompatible pen pairs", self.incompatible)
        left = QVBoxLayout(); left.addLayout(form)
        left.addWidget(QLabel("Pens (printed in this order)")); left.addWidget(self.pens)
        row = QHBoxLayout(); row.addWidget(self.b_apply); row.addWidget(self.b_seeds); left.addLayout(row)
        right = QVBoxLayout(); right.addWidget(self.view, 1); right.addWidget(self.cover)
        right.addWidget(QLabel("Seed previews (click one to select it)")); right.addWidget(self.grid)
        top = QHBoxLayout(); top.addLayout(left, 1); top.addLayout(right, 2)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.log)
        self.fill_pens()

    def fill_pens(self):
        conf = self.state.conf
        self.pens.setRowCount(len(conf.pencolorlist))
        for r, (name, rgb, sat, fac) in enumerate(bridge.pen_table(conf)):
            for c, val in enumerate((name, str(rgb), str(sat), f"{fac:.4f}")):
                it = QTableWidgetItem(val)
                if c < 2:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.pens.setItem(r, c, it)
        self.incompatible.setText("; ".join("+".join(p) for p in conf.noncompatiblepencolor))

    def read_pens(self):
        conf = self.state.conf
        for r, pen in enumerate(conf.pencolorlist):
            pen.saturationconstraint = int(self.pens.item(r, 2).text())
            pen.distributionfactor = float(self.pens.item(r, 3).text())
        conf.noncompatiblepencolor = [p.strip().split("+") for p in self.incompatible.text().split(";") if "+" in p]
        bridge.set_resolution(conf, self.scale.value() / 100)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Fractal image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            self.state.image_path = path
            self.path.setText(path)
            self.apply()

    def prepare(self):
        self.read_pens()
        if self.state.image_path is None:
            raise RuntimeError("open an image first")
        return bridge.load_image(self.state.conf, self.state.image_path)

    def apply(self):
        try:
            image = self.prepare()
        except Exception as exc:
            self.log.add(str(exc)); return
        seed = self.seed.value()
        mix = self.mixseed.isChecked()
        conf = self.state.conf

        def work(job):
            if seed >= 0:
                bridge.apply_seed(conf, seed)
            tensor, _ = bridge.image_to_channels(conf, image, seed if (seed >= 0 and mix) else None)
            return bridge.preview(conf, tensor), tensor

        def done(result):
            rgb, tensor = result
            self.state.image, self.state.tensor, self.state.seed = image, tensor, seed
            self.view.show_rgb(rgb)
            cov = bridge.channel_coverage(tensor, conf)
            self.cover.setText("coverage: " + "  ".join(f"{k} {v * 100:.0f}%" for k, v in cov.items()))
            self.fill_pens()
            self.channels_ready.emit()
        self.runner.start(work, done)

    def many(self):
        try:
            image = self.prepare()
        except Exception as exc:
            self.log.add(str(exc)); return
        n, mix, conf = self.nseeds.value(), self.mixseed.isChecked(), self.state.conf

        def work(job):
            out = []
            for s in range(n):
                if job.should_stop():
                    break
                rgb, _ = bridge.seed_preview(conf, image, s, mix)
                out.append((s, rgb))
                job.log.emit(f"seed {s} done")
            return out

        def done(items):
            self.grid.clear()
            for s, rgb in items:
                it = QListWidgetItem(QIcon(to_pixmap(rgb).scaled(120, 120, Qt.KeepAspectRatio)), f"seed {s}")
                it.setData(Qt.UserRole, s)
                self.grid.addItem(it)
        self.runner.start(work, done)


class PlotTab(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state, self.strokes, self.gcode, self.per_pen = state, [], "", {}
        c = state.conf
        self.method = QComboBox()
        for key, label in bridge.METHODS:
            self.method.addItem(label, key)
        self.rust = QCheckBox("Use the compiled Rust solver (faster)"); self.rust.setEnabled(bridge.RUST_BIN.exists())
        self.rust.setChecked(bridge.RUST_BIN.exists())
        b_build = QPushButton("Build Rust solver"); b_build.clicked.connect(self.build_rust)
        self.l1 = spin(0.5, 50, c.max_line_length_range[0], .5, 1); self.l2 = spin(0.5, 50, c.max_line_length_range[1], .5, 1)
        self.xy = spin(100, 20000, c.xyspeed, 100); self.tr = spin(100, 30000, c.travelspeed, 100)
        self.safez = spin(1, 60, c.safez, .5, 1); self.shz = spin(0.5, 30, c.shorttravelz, .5, 1)
        self.shd = spin(0, 100, c.shorttravelmaxdistance, 1, 1)
        self.zoff = spin(-10, 10, c.zoffset, .1, 2)
        self.pen_ratio = spin(0.01, 1, c.change_pen_ratio, .05, 2)
        legacy = QGroupBox("Legacy / experimental: split the image into an optimised grid of cells (ImageTravelOptimizer)")
        legacy.setCheckable(True); legacy.setChecked(False); self.cutbox = legacy
        self.cuts = spin(1, 20, 3); self.epochs = spin(5, 500, 40)
        lf = QFormLayout(legacy); lf.addRow("Cuts per axis", self.cuts); lf.addRow("Epochs", self.epochs)
        lf.addRow(QLabel("Gradient descent moves the cut lines to reduce the estimated pen travel; each cell is then drawn separately."))
        self.b_gen = QPushButton("Generate G-code"); self.b_stop = QPushButton("Stop")
        b_save = QPushButton("Save .gcode"); b_split = QPushButton("Save one file per pen")
        self.b_gen.clicked.connect(self.generate); self.b_stop.clicked.connect(lambda: self.runner.stop())
        b_save.clicked.connect(self.save); b_split.clicked.connect(self.save_split)
        self.slider = QSlider(Qt.Horizontal); self.slider.valueChanged.connect(self.redraw)
        self.view = ImageView(); self.log = LogBox(110); self.info = QLabel("")
        self.runner = Runner(self.log, (self.b_gen,))
        form = QFormLayout()
        form.addRow("Method", self.method); form.addRow(self.rust); form.addRow(b_build)
        form.addRow("Line length (mm), min", self.l1); form.addRow("Line length (mm), max", self.l2)
        form.addRow("Drawing speed (mm/min)", self.xy); form.addRow("Travel speed", self.tr)
        form.addRow("Safe Z / short-travel Z", self._pair(self.safez, self.shz))
        form.addRow("Short travel distance (mm)", self.shd); form.addRow("Z offset (M851)", self.zoff)
        form.addRow("Pen change every (fraction of canvas)", self.pen_ratio)
        left = QVBoxLayout(); left.addLayout(form); left.addWidget(legacy)
        row = QHBoxLayout(); [row.addWidget(w) for w in (self.b_gen, self.b_stop)]; left.addLayout(row)
        row2 = QHBoxLayout(); row2.addWidget(b_save); row2.addWidget(b_split); left.addLayout(row2)
        right = QVBoxLayout(); right.addWidget(self.view, 1); right.addWidget(QLabel("Show the first strokes")); right.addWidget(self.slider)
        right.addWidget(self.info)
        top = QHBoxLayout(); top.addLayout(left, 1); top.addLayout(right, 2)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.log)

    @staticmethod
    def _pair(a, b):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); l.addWidget(a); l.addWidget(b); return w

    def build_rust(self):
        self.runner.start(lambda job: bridge.build_rust(job.log.emit), lambda ok: (self.rust.setEnabled(ok), self.rust.setChecked(ok)))

    def apply_settings(self):
        c = self.state.conf
        c.max_line_length_range = (self.l1.value(), max(self.l1.value(), self.l2.value()))
        c.xyspeed, c.travelspeed, c.safez, c.shorttravelz = self.xy.value(), self.tr.value(), self.safez.value(), self.shz.value()
        c.shorttravelmaxdistance, c.zoffset, c.change_pen_ratio = self.shd.value(), self.zoff.value(), self.pen_ratio.value()

    def generate(self):
        s = self.state
        if s.tensor is None:
            self.log.add("prepare the pen channels in the first tab"); return
        self.apply_settings()
        masks = bridge.channel_masks(s.tensor)
        names = [p.colorname for p in s.conf.pencolorlist]
        method, rust = self.method.currentData(), self.rust.isChecked()
        cuts_on, cuts, epochs = self.cutbox.isChecked(), self.cuts.value(), self.epochs.value()

        def work(job):
            grid = None
            if cuts_on:
                job.log.emit("optimising cuts on the largest channel...")
                biggest = max(range(len(masks)), key=lambda i: masks[i].sum())
                grid = bridge.optimise_cuts(s.conf, masks[biggest], cuts, epochs)
                job.log.emit(f"cuts: x {grid[0]}  y {grid[1]}")
            return bridge.run_plot(s.conf, masks, names, method, grid, rust, job, job.log.emit)

        def done(result):
            self.gcode, self.strokes, self.per_pen = result
            self.slider.setRange(1, max(len(self.strokes), 1)); self.slider.setValue(len(self.strokes))
            lines = self.gcode.count("\n")
            self.info.setText(f"{len(self.strokes)} strokes, {lines} G-code lines, {len(self.gcode) / 1e6:.2f} MB")
            self.redraw()
        self.runner.start(work, done)

    def redraw(self):
        if self.strokes:
            rgb = [p.rgb for p in self.state.conf.pencolorlist]
            self.view.show_rgb(bridge.render_strokes(self.strokes, self.state.conf, rgb, 900, self.slider.value()))

    def save(self):
        if not self.gcode:
            return
        path, _ = QFileDialog.getSaveFileName(self, "G-code", "fractal.gcode", "G-code (*.gcode)")
        if path:
            Path(path).write_text(self.gcode)

    def save_split(self):
        if not self.per_pen:
            return
        folder = QFileDialog.getExistingDirectory(self, "Folder")
        if folder:
            for name, text in self.per_pen.items():
                (Path(folder) / f"{name}.gcode").write_text("G1 Z15\n" + text + "G1 Z15\n")


class ToolsTab(QWidget):
    def __init__(self, state, plot):
        super().__init__()
        self.state, self.plot = state, plot
        self.log = LogBox(160); self.view = ImageView(300)
        self.files = QListWidget(); self.files.setMaximumHeight(110)
        b_add = QPushButton("Add G-code files..."); b_add.clicked.connect(self.add_files)
        b_clear = QPushButton("Clear"); b_clear.clicked.connect(self.files.clear)
        self.split = QCheckBox("Insert a pen refill halfway through each file (split)")
        self.pencha = QCheckBox("Pen-change routine before each file"); self.pencha.setChecked(True)
        b_fuse = QPushButton("Fuse with progress display (fusegcode)"); b_fuse.clicked.connect(self.fuse)
        b_simple = QPushButton("Simple fuse (simplefuse)"); b_simple.clicked.connect(self.simple)
        b_opt = QPushButton("Optimise lift-ups of the first file (optimizegcode)"); b_opt.clicked.connect(self.optimise)
        b_bounds = QPushButton("Bounding box of the first file (gcode_bounds)"); b_bounds.clicked.connect(self.bounds)
        g1 = QGroupBox("G-code files")
        l1 = QVBoxLayout(g1)
        row = QHBoxLayout(); row.addWidget(b_add); row.addWidget(b_clear); l1.addLayout(row); l1.addWidget(self.files)
        l1.addWidget(self.split); l1.addWidget(self.pencha)
        for b in (b_fuse, b_simple, b_opt, b_bounds):
            l1.addWidget(b)

        g2 = QGroupBox("Split an Inkscape SVG (splitsvg)")
        self.svg = QLineEdit(); b_svg = QPushButton("SVG..."); b_svg.clicked.connect(lambda: self._pick(self.svg, "SVG (*.svg)"))
        self.mode = QComboBox(); self.mode.addItems(["bymaximumsize", "mixedfiles", "similartogether"])
        self.count = spin(1, 100, 8); self.kb = spin(8, 100000, 512)
        b_split = QPushButton("Split"); b_split.clicked.connect(self.split_svg)
        f2 = QFormLayout(g2); f2.addRow(b_svg, self.svg); f2.addRow("Mode", self.mode); f2.addRow("Files (mixed / similar)", self.count)
        f2.addRow("Max size per file (kB)", self.kb); f2.addRow(b_split)

        g3 = QGroupBox("Pen colour chart (PenColorChartTest): every pen combination, to calibrate the mixes")
        b_chart = QPushButton("Generate chart and send it to the Plot tab"); b_chart.clicked.connect(self.chart)
        QVBoxLayout(g3).addWidget(b_chart)
        left = QVBoxLayout(); left.addWidget(g1); left.addWidget(g2); left.addWidget(g3)
        right = QVBoxLayout(); right.addWidget(self.view, 1)
        top = QHBoxLayout(); top.addLayout(left, 1); top.addLayout(right, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.log)

    def _pick(self, edit, filt):
        path, _ = QFileDialog.getOpenFileName(self, "File", "", filt)
        if path:
            edit.setText(path)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "G-code", "", "G-code (*.gcode)")
        self.files.addItems(sorted(paths))

    def names(self):
        return [self.files.item(i).text() for i in range(self.files.count())]

    def fuse(self):
        if self.names():
            out, _ = QFileDialog.getSaveFileName(self, "Output", "output.gcode", "G-code (*.gcode)")
            if out:
                self.log.add(f"wrote {bridge.fuse_gcode(self.names(), out, self.split.isChecked(), self.pencha.isChecked())} characters")

    def simple(self):
        if self.names():
            out, _ = QFileDialog.getSaveFileName(self, "Output", "output.gcode", "G-code (*.gcode)")
            if out:
                bridge.simple_fuse(self.names(), out); self.log.add("done")

    def optimise(self):
        if self.names():
            out, _ = QFileDialog.getSaveFileName(self, "Output", "finaloutput.gcode", "G-code (*.gcode)")
            if out:
                self.log.add(f"{bridge.optimize_gcode(self.names()[0], out)} lift-ups replaced by a low lift")

    def bounds(self):
        if self.names():
            self.log.add(f"min/max X, min/max Y: {bridge.gcode_bounds(self.names()[0])}")

    def split_svg(self):
        if self.svg.text():
            folder = QFileDialog.getExistingDirectory(self, "Output folder")
            if folder:
                files = bridge.split_svg(self.svg.text(), folder, self.mode.currentText(),
                                         self.count.value(), self.kb.value())
                self.log.add(f"wrote {len(files)} files")

    def chart(self):
        import torch
        tensor = bridge.color_chart(self.state.conf)
        self.state.tensor = tensor
        bridge.set_resolution_exact(self.state.conf, tensor.shape[1], tensor.shape[2])
        self.view.show_rgb(bridge.preview(self.state.conf, tensor))
        self.log.add(f"chart {tuple(tensor.shape)} ready: open the Plot tab and generate")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gcodefractal")
        self.state = State()
        self.image_tab = ImageTab(self.state)
        self.plot_tab = PlotTab(self.state)
        self.tools_tab = ToolsTab(self.state, self.plot_tab)
        tabs = QTabWidget()
        for w, name in ((self.image_tab, "1. Image and pens"), (self.plot_tab, "2. Plot (G-code)"), (self.tools_tab, "3. Tools (legacy scripts)")):
            tabs.addTab(w, name)
        self.setCentralWidget(tabs)
        self.resize(1250, 850)

    def closeEvent(self, event):
        running = [job for job in _JOBS if job.isRunning()]
        for job in running:
            job.stop()
        # a QThread destroyed while running aborts the process, and terminating one inside CUDA does too
        if not all(job.wait(15000) for job in running):
            import os
            os._exit(0)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
