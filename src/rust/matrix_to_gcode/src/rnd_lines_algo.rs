use std::collections::btree_map::Range;

use ndarray::Array2;
use ndarray::prelude::*;
use rand::{Rng, thread_rng};
use rand::seq::IndexedRandom;
use std::process::exit;
pub struct RandomLinesAlgo {
    pub nparray: Array2<bool>,
    pub actual_pos: [i32; 2],
    pub current_n: u32,
    pub max_line_length_min: [i32; 2],
    pub max_line_length_max: [i32; 2],
    pub current_max_line_length: [i32; 2],
}

impl RandomLinesAlgo {
    pub fn new(nparray: Array2<bool>,max_line_length_min: [i32; 2],max_line_length_max: [i32; 2]) -> Self{
        let shape = nparray.shape();
        assert!(shape.len() == 2, "Expected 2D array");
        let mut rng = thread_rng();
        let mut actual_pos = [
            rng.random_range(0..shape[0]) as i32,
            rng.random_range(0..shape[1]) as i32,
        ];
        Self { nparray,
            actual_pos,
            current_n : 0,
            max_line_length_min,
            max_line_length_max,
            current_max_line_length: [0,0],
         }

    }
    fn reset_max_line_length(&mut self){
        self.current_max_line_length = [rand::thread_rng().gen_range(self.max_line_length_min[0]..self.max_line_length_max[0]+1),
        rand::thread_rng().gen_range(self.max_line_length_min[1]..self.max_line_length_max[1]+1)];
    }
    fn is_inbound(&self,array: [i32;2]) -> bool{
        let maxpos = self.nparray.shape();
        let maxpos = [maxpos[0] as i32,maxpos[1] as i32];
        array[0]<maxpos[0] && array[1]<
        maxpos[1] && array[0]>= 0 && array[1]>= 0
    }
    fn get_distance(&self,start: [i32;2],end: [i32;2]) -> f64{
        let distance = ((start[0]-end[0])*(start[0]-end[0]) + (start[1]-end[1])*(start[1]-end[1])) as f64;
        distance.sqrt()

    }
    pub fn get_next_try(&self) -> Vec<[i32; 2]>{
        
        let n = self.current_n;
        if n == 0 {
            return vec![[self.actual_pos[0],self.actual_pos[1]]];
        }
        let sens = [[1,0],[0,1],[-1,0],[0,-1]];
        let mut p:[i32; 2] = [- (n as i32),- (n as i32)];
        let c = 2*n;
        let mut vec: Vec<[i32; 2]> = Vec::new();
        for direction in sens{
            for i in 0..c{
                p[0] = p[0] + direction[0];
                p[1] = p[1] + direction[1];
                let position = [p[0]+self.actual_pos[0],p[1]+self.actual_pos[1]];
                //println!("position{:?}",position);
                if self.is_inbound(position) {
                    vec.push(position);
                    //println!("vecpush{:?}",position);
                }
                
                //println!("p={:?}",p);
            }
        }
        //for x in &vec {
            //println!("vec{:?}",x);
        //}
        vec
    }
    fn trace_ray(&self,direction:[i32; 2],position: [i32; 2]) -> ([i32; 2],[i32; 2],f64) {
        let mut current_index = position.clone();
        let mut current_value: ArrayBase<ndarray::ViewRepr<&bool>, Dim<[usize; 0]>> = self.nparray.slice(s![current_index[0] as usize ,current_index[1] as usize]);
        let mut current_value = *current_value.into_scalar();
        let mut max_distance_counter: [i32; 2] = [0,0];
        //println!("max_rnd_distance{:?}",max_rnd_distance);
        //let mut distance = 0;
        //println!("*current_value.into_scalar(){}",current_value);
        while current_value{
            //distance += 1;
            current_index[0] += direction[0];
            current_index[1] += direction[1];
            max_distance_counter[0] += direction[0].abs();
            max_distance_counter[1] += direction[1].abs();
            //println!("current_index{:?}",current_index);
            if self.is_inbound(current_index){
                current_value = *self.nparray.slice(s![current_index[0] as usize ,current_index[1] as usize]).into_scalar();

            }else{
                current_value = false;
                current_index[0] -= direction[0];
                current_index[1] -= direction[1];
            }
            // TODO A VERIFIER
            // Si la distance parcourue depasse la limite max_line_length (en index) on sort de la boucle
            if max_distance_counter[0] > self.current_max_line_length[0] || max_distance_counter[1] > self.current_max_line_length[1]{
                current_value = false;
                //println!("called {:?} {:?} ",position,current_index);
                
            }
            
        }
        let linelength = self.get_distance(position, current_index);
        // start,end,distance
        
        (position,current_index,linelength)
    }
    pub fn remove_ray(&mut self,ray:[[i32; 2]; 2]){
        let mut directionx = 0;
        if ray[0][0] > ray[1][0] {
            directionx = -1
        }else if ray[0][0] < ray[1][0]{
            directionx = 1
        }
        let mut directiony = 0;
        if ray[0][1] > ray[1][1] {
            directiony = -1
        }else if ray[0][1] < ray[1][1]{
            directiony = 1
        }
        //println!("directionx {:?} directiony {:?}",directionx,directiony);
        let mut index_position = ray[0];
        // Remove the first ray pixel
        let row = index_position[0] as usize;
        let column = index_position[1] as usize;
        self.nparray[[row,column]] = false;
        //println!("{} {}",row,column);
        // Remove the rest
        while !(index_position[0] == ray[1][0] && index_position[1] == ray[1][1]){
            let row = index_position[0] as usize;
            let column = index_position[1] as usize;
            self.nparray[[row,column]] = false;
            index_position[0] += directionx;
            index_position[1] += directiony;

        }
        

    } 
    fn get_random_direction(&self) -> [i32; 2] {
        let directions = 
        [[-1,1], [0,1], [1,1],
         [-1,0],        [1,0],
         [-1,-1],[0,-1],[1,-1]];
         
        let direction: &[i32; 2] = directions.choose(&mut rand::rng()).expect("random failed");
        //print!("{:?}",*direction);
        *direction
        
    }
    pub fn step(&mut self)->[[i32; 2]; 2]{
        let current_direction = self.get_random_direction();
        self.reset_max_line_length();
        let mut current_length = 1000;
        let mut bestcost = -1000000000.0;
        let mut bestray: [[i32; 2]; 2]= [[-1,-1],[-1,-1]];
        while current_length > 0 {
            let current_try = self.get_next_try();
            //println!("current_try all{:?}",current_try);
            for i in &current_try {
                //println!("current_try i{:?}",i);
                let (ray_start,ray_end,ray_length) = self.trace_ray(current_direction,*i);
                let ray_distance_from_actual_pos = self.get_distance(self.actual_pos, ray_start);
                let cost =  ray_length ;//- (ray_distance_from_actual_pos/2.0); // Goal is to Maximize
                //println!("{:?}  {:?}",cost,bestcost);
                if cost > bestcost {
                    //println!("ray_start{:?},ray_end{:?},ray_length{:?}",ray_start,ray_end,ray_length);
                    //println!("current_direction{:?}",current_direction);
                    //println!("ray_distance_from_actual_pos{:?}",ray_distance_from_actual_pos);
                    //println!("cost{:?}",cost);
                    bestcost = cost;
                    bestray = [ray_start,ray_end];
                                }
            }
            current_length = current_try.len();
            //println!("current try lenght {}",current_length);
            // Prend la case la plus proche ayant la meilleure note qui possede une certain longueur
            if bestcost > 0.0 {
                //println!("bestray={:?}",bestray);
                return bestray;
            }
            
            self.current_n += 1;
            //println!("n={}",self.current_n);
        }
        bestray
    }
}