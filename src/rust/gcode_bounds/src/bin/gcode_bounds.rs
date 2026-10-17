use std::env;
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut args = env::args();
    let program = args.next().unwrap_or_else(|| "gcode_bounds".to_string());
    let Some(path) = args.next() else {
        eprintln!("usage: {program} <file.gcode>");
        return ExitCode::FAILURE;
    };

    match gcode_bounds::compute_bounds(&path) {
        Ok(b) if b.found_x || b.found_y => {
            println!("min_x = {}", b.min_x);
            println!("max_x = {}", b.max_x);
            println!("min_y = {}", b.min_y);
            println!("max_y = {}", b.max_y);
            ExitCode::SUCCESS
        }
        Ok(_) => {
            eprintln!("no X or Y coordinates found in {path}");
            ExitCode::FAILURE
        }
        Err(e) => {
            eprintln!("failed to read {path}: {e}");
            ExitCode::FAILURE
        }
    }
}
