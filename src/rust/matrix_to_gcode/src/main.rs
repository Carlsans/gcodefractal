mod gcode_writer;
mod gcode_file;
mod numpy_importer;
mod rnd_lines_algo;
use crate::gcode_writer::GcodeWriter;
use crate::gcode_file::GcodeFile;
use crate::numpy_importer::NumpyImporter;
use crate::rnd_lines_algo::RandomLinesAlgo;
use std::process::exit;
use std::env;


fn main() {
    // Collect command line arguments
    let args: Vec<String> = env::args().collect();
    let mut basepath = String::from("/home/carl/PycharmProjects/gcodefractal/src/common");
    if args.len() > 1{
        basepath = String::from(&args[1]);
        
    }
    if !basepath.ends_with('/'){
        basepath.push('/');
    }
    println!("basepath{}",basepath);
    
    
    
    let mut gcode = GcodeWriter::new(basepath.clone());    
    let np_importer = NumpyImporter::new(basepath.clone());
    let (max_line_length_min,max_line_length_max) = gcode.get_indexes_length_from_max_line_length();
    let mut algo = RandomLinesAlgo::new(np_importer.nparray,max_line_length_min,max_line_length_max);
    let mut gcodefile = GcodeFile::new(basepath.clone(),"topython.gcode");
    if gcode.resolution[0] != algo.nparray.shape()[0] as u32 
    || gcode.resolution[1] != algo.nparray.shape()[1] as u32 {
        panic!("Python Resolution and Numpy Array shape must be equal")
    }
    gcode.print_config();
    let mut num_steps = 0 ;
    let mut buffer = String::from("");
    let total_ones_pixel_count = algo.nparray.mapv(i32::from).sum() as f64;
    let total_pixel_count = algo.nparray.shape()[0] as f64 *algo.nparray.shape()[1] as f64;
    let change_pen_pixels = (gcode.get_change_pen_ratio()*total_pixel_count) as i32;
    let mut change_pen: i32 = change_pen_pixels;
    loop {
        //println!("{:?}",algo.nparray);
        algo.current_n = 0;
        // Run once every ... to minimize run time
        // Save String buffer
        if num_steps % 100 == 0 {
            let pixel_sum = algo.nparray.mapv(i32::from).sum();
            println!("pixel_sum= {pixel_sum}");
            buffer.push_str(&format!(";num_steps {} pixel left : {}",num_steps,pixel_sum));
            buffer += "\n";
            //buffer.push_str(&format!(";{}  {}",total_ones_pixel_count as i32-pixel_sum,change_pen));
            //buffer += "\n";
            buffer.push_str(&format!("M117 Progress {:.2}%",(total_ones_pixel_count-pixel_sum as f64)*100./total_ones_pixel_count));
            buffer += "\n";

            
                if (total_ones_pixel_count as i32-pixel_sum) > change_pen {
                    buffer.push_str("M117 Changing pen");
                    buffer += "\n"; 
                    buffer += gcode.change_pen().as_str();
                    change_pen += change_pen_pixels;
                }
            

            gcodefile.write(buffer);
            buffer = String::from("");
            if pixel_sum==0 {
                break;
            }
        }

        let result = algo.step();
        //println!("---------");
        //println!("Result : {:?}",result); 
        let line: String = gcode.draw_line(result);
        //println!("Line : {:?}",line); 
        buffer.push_str(&line);
        if result == [[-1,-1],[-1,-1]]{
            
            break;
        } 
        if result[0]==result[1]{
            let pixel_sum = algo.nparray.mapv(i32::from).sum();
            println!("mimimipixel_sum= {pixel_sum}");
            //break;
        } 
        algo.remove_ray(result);
        // Set new position after removing the line. Gcode should be there
        algo.actual_pos = result[1];
        num_steps +=1 
    }
    println!("num_steps={num_steps}");
    // let origin = (5,10);
    // let destination = (20,300);
    // let line = gcode.draw_line(origin,destination);
    // println!("{}",line);
    // let mut gcodefile = GcodeFile::new(String::from("Test.gcode"));
    // gcodefile.write(String::from("Test"));
    // gcodefile.write(String::from(line));
}
