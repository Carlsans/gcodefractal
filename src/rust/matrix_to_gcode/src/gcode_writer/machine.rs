#[derive(Debug)]
pub struct Machine {
    
    pub current_position_index : [i32;2],
    pub is_up : bool,
    resolution : [u32;2],
    size : [f64;2],
    pixel_size : [f64;2],

}

impl Machine{
    pub fn new(resolution: [u32; 2],size: [f64; 2]) -> Self {
        Self { current_position_index:[0,0], is_up: true,resolution,size,pixel_size:[size[0]/(resolution[0] as f64),size[1]/(resolution[1] as f64)] }
    }
    pub fn get_pixel_size(&self)->[f64;2]{
        self.pixel_size
    }
    pub fn set_position_index(&mut self, index: [i32;2]){
        self.current_position_index = index;
    }
    pub fn get_center_index(&self) -> [i32;2] {
        [self.resolution[0] as i32/2,self.resolution[1] as i32/2]
    }
    pub fn get_size(&self) -> [f64; 2] {
        self.size
    }
    pub fn get_current_position(&self) -> [f64;2] {
        self.get_position(self.current_position_index)
        //[self.current_position_index[0] as f64 * self.pixel_size[0],self.current_position_index[1] as f64 * self.pixel_size[1]]
    }
    pub fn get_position(&self,position:[i32;2]) ->[f64;2] {
        [position[0] as f64 * self.pixel_size[0],position[1] as f64 * self.pixel_size[1]]
    }
}
