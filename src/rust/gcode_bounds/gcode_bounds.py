"""Python handle for the gcode_bounds Rust library.

Loads the compiled shared library (build it first with, from this
directory: `cargo build --release`) and exposes a single function,
`get_bounds`, that returns the X/Y bounding box of a G-code file.

Example
-------
    from gcode_bounds import get_bounds

    bounds = get_bounds("part.gcode")
    print(bounds.min_x, bounds.max_x, bounds.min_y, bounds.max_y)
"""

from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass
from pathlib import Path

_LIB_NAMES = {
    "Linux": "libgcode_bounds.so",
    "Darwin": "libgcode_bounds.dylib",
    "Windows": "gcode_bounds.dll",
}


class _CGcodeBounds(ctypes.Structure):
    _fields_ = [
        ("min_x", ctypes.c_double),
        ("max_x", ctypes.c_double),
        ("min_y", ctypes.c_double),
        ("max_y", ctypes.c_double),
        ("found_x", ctypes.c_bool),
        ("found_y", ctypes.c_bool),
        ("status", ctypes.c_int32),
    ]


_STATUS_MESSAGES = {
    1: "path is not valid UTF-8",
    2: "file could not be opened or read",
    3: "internal error while scanning the file",
}


def _load_library() -> ctypes.CDLL:
    lib_name = _LIB_NAMES.get(platform.system())
    if lib_name is None:
        raise RuntimeError(f"unsupported platform: {platform.system()}")

    lib_path = Path(__file__).with_name("target") / "release" / lib_name
    if not lib_path.exists():
        raise FileNotFoundError(
            f"{lib_path} not found. Build it first with:\n"
            f"    cd {Path(__file__).parent} && cargo build --release"
        )

    lib = ctypes.CDLL(str(lib_path))
    lib.gcode_bounds.argtypes = [ctypes.c_char_p]
    lib.gcode_bounds.restype = _CGcodeBounds
    return lib


_lib = _load_library()


@dataclass(frozen=True)
class GcodeBounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    found_x: bool
    found_y: bool


def get_bounds(path: str | Path) -> GcodeBounds:
    """Scan a G-code file and return the extents of its X/Y coordinates.

    Only literal X/Y words present in the file are considered (no modal
    state, no arc interpolation, no relative-mode tracking). If a file has
    no X (or Y) words at all, the corresponding `found_*` flag is False and
    the min/max fields for that axis are NaN.
    """
    raw_path = str(path).encode("utf-8")
    result = _lib.gcode_bounds(raw_path)

    if result.status != 0:
        message = _STATUS_MESSAGES.get(result.status, "unknown error")
        raise RuntimeError(f"gcode_bounds failed for {path!r}: {message}")

    return GcodeBounds(
        min_x=result.min_x,
        max_x=result.max_x,
        min_y=result.min_y,
        max_y=result.max_y,
        found_x=result.found_x,
        found_y=result.found_y,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"usage: python {sys.argv[0]} <file.gcode>")
        raise SystemExit(1)

    b = get_bounds(sys.argv[1])
    print(f"min_x = {b.min_x}")
    print(f"max_x = {b.max_x}")
    print(f"min_y = {b.min_y}")
    print(f"max_y = {b.max_y}")
