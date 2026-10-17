use std::fs::File;
use std::io::BufReader;
use std::collections::HashMap;
use serde::Deserialize;
use serde_json::Value;
use rand::{distr, Rng};
mod machine;
use crate::gcode_writer::machine::Machine;
#[derive(Debug)]
pub struct GcodeWriter {
machine : Machine,
pub resolution : [u32;2],
size : [f64;2],
xyspeed : f64,
travelspeed : f64,
safez : f64,
shorttravelz : f64,
shorttravelmaxdistance : f64,
zspeed : f64,
pub max_line_length_min : f64,
pub max_line_length_max : f64,
change_pen_ratio : f64,
change_pen_height: f64,
}
impl GcodeWriter {
    pub fn draw_line(&mut self,line: [[i32; 2]; 2]) -> String {
        let mut direction = self.get_line_direction(line);
        // In case we got a single pixel, give it a random orientation so it's not a single dot but a line
        if direction == [0.,0.] {
            direction = self.get_random_direction();
            
        }
        //println!("direction{:?}",direction);
        let pixel_size = self.machine.get_pixel_size();
        let start_x_square_correction = (-pixel_size[0]*direction[0])/2.;
        let stop_x_square_correction = (pixel_size[0]*direction[0])/2.;
        let start_y_square_correction = (-pixel_size[1]*direction[1])/2.;
        let stop_y_square_correction = (pixel_size[1]*direction[1])/2.;
        //println!("start_x_square_correction{start_x_square_correction}");
        //println!("stop_x_square_correction{stop_x_square_correction}");
        //println!("start_y_square_correction{start_y_square_correction}");
        //println!("stop_y_square_correction{stop_y_square_correction}");
        let start_pos = [ self.machine.get_position(line[0])[0] + start_x_square_correction,
                                    self.machine.get_position(line[0])[1] + start_y_square_correction];
        //println!("start_pos{:?}",start_pos);
        //println!("self.machine.get_position(line[0])[1] {}",self.machine.get_position(line[0])[1]);
       //println!("self.machine.get_position(line[1])[1] {}",self.machine.get_position(line[1])[1]);
        let end_pos =   [ self.machine.get_position(line[1])[0] + stop_x_square_correction,
                                    self.machine.get_position(line[1])[1] + stop_y_square_correction];
        
        let travel_move = self.travel_move(self.machine.current_position_index,line[0]);
        
        self.machine.current_position_index = line[1];
        //println!("end_pos{:?}",end_pos);
        //let start_pos: (f64,f64) = (origin.0 as f64 / self.resolution.0 as f64, origin.1 as f64  / self.resolution.1 as f64 ) ;
        //let end_pos: (f64,f64) = (self.size.0*destination.0 as f64 / self.resolution.0 as f64,self.size.1*destination.1 as f64 / self.resolution.1 as f64) ;
        //println!("Start position : {},{}, End position : {},{}",start_pos.0,start_pos.1,end_pos.0,end_pos.1);
        //format!("G1 X{} Y{} \nG1 X{} Y{} \n",
        //self.pos_to_str(start_pos.0),self.pos_to_str(start_pos.1),
        //self.pos_to_str(end_pos.0),self.pos_to_str(end_pos.1))
        //return ("G1 X".to_owned() + &self.pos_to_str(start_pos.0)).to_string();
        /*        /*
        xyspeed : f64,
travelspeed : f64,
*/  */
        let mut return_string = String::new();
        return_string.push_str(&format!("{}G1 X{} Y{} F{}\n",travel_move,self.pos_to_str(start_pos[0]),self.pos_to_str(start_pos[1]),self.pos_to_str(self.travelspeed)));
        return_string.push_str(&format!("G1 Z0 {}\n",self.pos_to_str(self.zspeed)));
        return_string.push_str(&format!("G1 X{} Y{} F{}\n",self.pos_to_str(end_pos[0]),self.pos_to_str(end_pos[1]),self.pos_to_str(self.xyspeed)));
        return_string
    }
    pub fn get_indexes_length_from_max_line_length(&self) ->([i32;2],[i32;2]){
        ([(self.max_line_length_min  / self.machine.get_pixel_size()[0]) as i32 ,(self.max_line_length_min / self.machine.get_pixel_size()[1]) as i32],        
         [(self.max_line_length_max  / self.machine.get_pixel_size()[0]) as i32 ,(self.max_line_length_max / self.machine.get_pixel_size()[1]) as i32])
    }
    fn travel_move(&self,current_position: [i32;2],destination: [i32;2]) -> String {
        let current_position = self.machine.get_position(current_position);
        let destination = self.machine.get_position(destination);
        //let current_position = current_position.map(f64::from);
        //let destination = destination.map(f64::from);
        let distance = ((current_position[0]-destination[0])*(current_position[0]-destination[0]) + (current_position[1]-destination[1])*(current_position[1]-destination[1])).sqrt();
        if distance <= (self.machine.get_pixel_size()[0].powf(2.0)+self.machine.get_pixel_size()[1].powf(2.0)).sqrt()+0.01{
            return String::new();
        }
        if distance < self.shorttravelmaxdistance {
            return format!("G1 Z{} {}\n",self.pos_to_str(self.shorttravelz),self.pos_to_str(self.zspeed));
        }else {
            return format!("G1 Z{} {}\n",self.pos_to_str(self.safez),self.pos_to_str(self.zspeed));
        }
    }
    pub fn change_pen(&mut self) -> String {
        let mut returnstring = String::new();
        returnstring.push_str(&format!("G1 Z{}\n",self.pos_to_str(self.change_pen_height)));
        self.machine.is_up = true;
        let size = self.machine.get_size();
        returnstring.push_str(&format!("G1 X{} Y{}\n",size[0]/2.,size[1]/2.));
        self.machine.set_position_index(self.machine.get_center_index());
        returnstring.push_str("M226 P121\n");
        returnstring
        /*self.file.write("G1 Z25\n")
        self.machine.setZ(32)
        self.machine.setY(self.conf.canvasmax[0] / 2)
        self.machine.setX(self.conf.canvasmax[1] / 2)
        self.file.write("G1 X"+ self.formatcoordinate(self.machine.x) + " Y" + self.formatcoordinate(self.machine.y) + "\n")
        self.file.write("M226 P121\n") */

    }
    fn get_random_direction(&self) -> [f64; 2]{
        let mut rng = rand::thread_rng();
        let mut randomdirection = [0.,0.];
        loop {
            randomdirection[0] = rng.gen_range(-1..2) as f64;
            randomdirection[1] = rng.gen_range(-1..2) as f64;
            if randomdirection != [0.,0.] {break;}
        }
        
        return randomdirection;

    }
    fn get_line_direction(&self,line: [[i32; 2]; 2]) -> [f64; 2]{
        let mut directionx: f64 = 0.;
        if line[0][0] > line[1][0] {
            directionx = -1.
        }else if line[0][0] < line[1][0]{
            directionx = 1.
        }
        let mut directiony: f64 = 0.;
        if line[0][1] > line[1][1] {
            directiony = -1.
        }else if line[0][1] < line[1][1]{
            directiony = 1.
        }
        //println!("directionx{directionx},directiony{directiony}");
        [directionx,directiony]
    }
    fn pos_to_str(&self,position:f64) -> String{
        let strpos = format!("{:.2}", position);
        let strpos = String::from(strpos.trim_end_matches('0'));
        let strpos = String::from(strpos.trim_end_matches('.'));

        strpos

    }
    pub fn print_config(&self){
        println!("{:?}",self)
    }
    pub fn get_change_pen_ratio(&self) -> f64{
        self.change_pen_ratio
    }
    pub fn new(mut basepath: String) -> Self {
         // Load JSON config
        basepath.push_str("config.json");

        let config_file = File::open(basepath).expect("Failed to open config.json");
        let reader = BufReader::new(config_file);

        // Automatically parses the config as a key-value map
        let config: HashMap<String, Value> = serde_json::from_reader(reader).expect("Failed to convert to hashmap");

        for (key, value) in &config {
            println!("{}: {}", key, value);
        }
   
        let resolutionx = config["resolutionX"]
            .as_u64()
            .expect("resolutionX should be a u64") as u32;
        let resolutiony = config["resolutionY"]
            .as_u64()
            .expect("resolutionY should be a u64") as u32;
        let sizex = config["sizeX"]
            .as_f64()
            .expect("sizeX should be a f64");
        let sizey = config["sizeY"]
            .as_f64()
            .expect("sizeY should be a f64");
        let xyspeed = config["xyspeed"]
            .as_f64()
            .expect("xyspeed should be a f64");
        let travelspeed = config["travelspeed"]
            .as_f64()
            .expect("travelspeed should be a f64");
        let safez = config["safez"]
            .as_f64()
            .expect("safez should be a f64");
        let shorttravelz = config["shorttravelz"]
        .as_f64()
        .expect("shorttravelz should be a f64");
        let shorttravelmaxdistance = config["shorttravelmaxdistance"]
            .as_f64()
            .expect("shorttravelmaxdistance should be a f64");
        let zspeed = config["zspeed"]
            .as_f64()
            .expect("zspeed should be a f64");
        let max_line_length_min: f64 = config["max_line_length_min"]
            .as_f64()
            .expect("max_line_length_min should be a f64");
        let max_line_length_max: f64 = config["max_line_length_max"]
            .as_f64()
            .expect("max_line_length_max should be a f64");
        let change_pen_ratio = config["change_pen_ratio"]
            .as_f64()
            .expect("change_pen_ratio should be a f64");
        let change_pen_height = config["change_pen_height"]
        .as_f64()
        .expect("change_pen_height should be a f64");
    //pub max_line_index_lenght_perpendicular : u32,
   // pub max_line_index_lenght_diagonal : u32,
        Self {
            machine : Machine::new([resolutionx,resolutiony],[sizex,sizey]),
            resolution : [resolutionx,resolutiony],
            size : [sizex,sizey],
            xyspeed,
            travelspeed,
            safez,
            shorttravelz,
            shorttravelmaxdistance,
            zspeed,
            max_line_length_min,
            max_line_length_max,
            change_pen_ratio,
            change_pen_height,

        }
    }
}