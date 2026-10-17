use ndarray::Array2;
use ndarray_npy::read_npy;
use ndarray::prelude::*;
pub struct NumpyImporter{
    pub nparray : Array2<bool>,
}
impl NumpyImporter{
    pub fn new(mut basepath: String) -> Self {
        basepath.push_str("array.npy");
         // Load the NumPy array
         let array: Array2<bool> = read_npy(basepath).expect("Could not load numpy array");
         //let array: Array2<bool> = array![[true,false,true],[true,true,true],[true,false,true]];
         println!("Loaded array of shape: {:?}", array.shape());
        Self{
           nparray : array,
        }

    }

}