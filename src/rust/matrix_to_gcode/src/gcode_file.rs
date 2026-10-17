use std::fs::File;
use std::io::prelude::*;
use std::path::Path;
use std::path::Display;

pub struct GcodeFile {
    path: String,
    file: File,
    }

impl GcodeFile {
pub fn new(mut basepath :String,filename :&str) -> Self{
    basepath.push_str(&filename);
    let path = Path::new(&basepath);
    let display = path.display();
    // Open a file in write-only mode, returns `io::Result<File>`
    let file = match File::create(&path) {
        Err(why) => panic!("couldn't create {}: {}", display, why),
        Ok(file) => file,
    };
        
    Self{
        path : String::from(filename),
        file,
    }
    }
pub fn write(&mut self,string : String){
     
    match self.file.write_all(string.as_bytes()) {
        Err(why) => panic!("couldn't write because: {}",  why),
        Ok(_) => println!("successfully wrote"),
    }

    }
}