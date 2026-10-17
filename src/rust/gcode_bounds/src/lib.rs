//! Scans a G-code file for X/Y words and reports their min/max extents.
//!
//! Only literal `X`/`Y` values written in the file are considered — there is
//! no modal-state machine (no G91 relative tracking, no arc interpolation).
//! That is intentionally out of scope: the goal is a fast bounding-box scan,
//! not a G-code interpreter.

use std::ffi::{c_char, CStr};
use std::fs::File;
use std::io::{self, BufRead, BufReader};
use std::panic;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Bounds {
    pub min_x: f64,
    pub max_x: f64,
    pub min_y: f64,
    pub max_y: f64,
    pub found_x: bool,
    pub found_y: bool,
}

impl Bounds {
    fn new() -> Self {
        Self {
            min_x: f64::INFINITY,
            max_x: f64::NEG_INFINITY,
            min_y: f64::INFINITY,
            max_y: f64::NEG_INFINITY,
            found_x: false,
            found_y: false,
        }
    }

    fn update_x(&mut self, v: f64) {
        self.found_x = true;
        if v < self.min_x {
            self.min_x = v;
        }
        if v > self.max_x {
            self.max_x = v;
        }
    }

    fn update_y(&mut self, v: f64) {
        self.found_y = true;
        if v < self.min_y {
            self.min_y = v;
        }
        if v > self.max_y {
            self.max_y = v;
        }
    }
}

/// Strips `;` line comments and `(...)` inline comments, then walks the
/// remaining whitespace-separated words looking for `X`/`Y` values.
fn scan_line(line: &[u8], bounds: &mut Bounds) {
    // Cut everything from the first ';' onward.
    let end = line.iter().position(|&b| b == b';').unwrap_or(line.len());
    let line = &line[..end];

    let mut i = 0;
    while i < line.len() {
        // Skip whitespace.
        while i < line.len() && line[i].is_ascii_whitespace() {
            i += 1;
        }
        if i >= line.len() {
            break;
        }

        // Skip parenthesised comments as a single "word".
        if line[i] == b'(' {
            i += 1;
            while i < line.len() && line[i] != b')' {
                i += 1;
            }
            i += 1; // consume ')' (or run off the end, harmless)
            continue;
        }

        // Start of a word: letter + number.
        let letter = line[i];
        let word_start = i;
        i += 1;
        while i < line.len() && !line[i].is_ascii_whitespace() {
            i += 1;
        }
        let word = &line[word_start..i];

        if (letter == b'X' || letter == b'x' || letter == b'Y' || letter == b'y')
            && word.len() > 1
            && let Ok(text) = std::str::from_utf8(&word[1..])
            && let Ok(value) = text.parse::<f64>()
        {
            if letter.eq_ignore_ascii_case(&b'X') {
                bounds.update_x(value);
            } else {
                bounds.update_y(value);
            }
        }
    }
}

/// Streams `path` line by line (low, constant memory) and returns the
/// bounding box of every `X`/`Y` word found.
pub fn compute_bounds<P: AsRef<Path>>(path: P) -> io::Result<Bounds> {
    let file = File::open(path)?;
    let mut reader = BufReader::with_capacity(1 << 20, file);
    let mut bounds = Bounds::new();
    let mut line = Vec::with_capacity(256);

    loop {
        line.clear();
        let bytes_read = reader.read_until(b'\n', &mut line)?;
        if bytes_read == 0 {
            break;
        }
        scan_line(&line, &mut bounds);
    }

    Ok(bounds)
}

// ---------------------------------------------------------------------
// C ABI, for calling from Python (or anything else) via ctypes/cffi/FFI.
// ---------------------------------------------------------------------

#[repr(C)]
pub struct CGcodeBounds {
    pub min_x: f64,
    pub max_x: f64,
    pub min_y: f64,
    pub max_y: f64,
    pub found_x: bool,
    pub found_y: bool,
    /// 0 = ok, 1 = path was not valid UTF-8, 2 = the file could not be
    /// opened/read, 3 = an internal panic was caught.
    pub status: i32,
}

impl CGcodeBounds {
    fn error(status: i32) -> Self {
        Self {
            min_x: f64::NAN,
            max_x: f64::NAN,
            min_y: f64::NAN,
            max_y: f64::NAN,
            found_x: false,
            found_y: false,
            status,
        }
    }
}

/// Computes the X/Y bounding box of the G-code file at `path` (a
/// null-terminated, UTF-8 C string). Never panics or unwinds across the FFI
/// boundary; check `status` before trusting the numeric fields.
///
/// # Safety
/// `path` must be a valid pointer to a null-terminated C string that stays
/// alive for the duration of this call.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn gcode_bounds(path: *const c_char) -> CGcodeBounds {
    let result = panic::catch_unwind(|| {
        if path.is_null() {
            return CGcodeBounds::error(1);
        }
        let path_str = match unsafe { CStr::from_ptr(path) }.to_str() {
            Ok(s) => s,
            Err(_) => return CGcodeBounds::error(1),
        };
        match compute_bounds(path_str) {
            Ok(b) => CGcodeBounds {
                min_x: b.min_x,
                max_x: b.max_x,
                min_y: b.min_y,
                max_y: b.max_y,
                found_x: b.found_x,
                found_y: b.found_y,
                status: 0,
            },
            Err(_) => CGcodeBounds::error(2),
        }
    });

    result.unwrap_or_else(|_| CGcodeBounds::error(3))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_basic_moves() {
        let mut b = Bounds::new();
        scan_line(b"G1 X10.5 Y-3.2 F1500", &mut b);
        scan_line(b"G1 X-2 Y7.25", &mut b);
        assert_eq!(b.min_x, -2.0);
        assert_eq!(b.max_x, 10.5);
        assert_eq!(b.min_y, -3.2);
        assert_eq!(b.max_y, 7.25);
    }

    #[test]
    fn ignores_comments() {
        let mut b = Bounds::new();
        scan_line(b"G1 X10 Y10 ; X99 Y99 should be ignored", &mut b);
        scan_line(b"G1 (skip X50 Y50) X1 Y1", &mut b);
        assert_eq!(b.max_x, 10.0);
        assert_eq!(b.max_y, 10.0);
        assert_eq!(b.min_x, 1.0);
        assert_eq!(b.min_y, 1.0);
    }

    #[test]
    fn no_coordinates_found() {
        let mut b = Bounds::new();
        scan_line(b"G28 ; home", &mut b);
        assert!(!b.found_x);
        assert!(!b.found_y);
    }
}
