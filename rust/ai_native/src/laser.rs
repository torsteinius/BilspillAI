//! Straight rays, two physical heights, sloped curb faces and elevated car bodies.
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
type Wall=(f64,f64,f64,f64,f64,f64);
type Object=(f64,f64,f64,f64,f64,f64,i32);
type Hit=(f64,f64,f64,f64,i32,i32,f64);
#[pyclass]
pub struct LaserRadar {walls:Vec<Wall>,angles:Vec<f64>}
#[pymethods]
impl LaserRadar {
 #[new]
 pub(crate) fn new(walls:Vec<Wall>,angles:Vec<f64>)->PyResult<Self>{
  if angles.is_empty()||angles.iter().any(|a|!a.is_finite())||walls.iter().any(|w|![w.0,w.1,w.2,w.3,w.4,w.5].iter().all(|v|v.is_finite())) {return Err(PyValueError::new_err("Invalid laser geometry"));}
  Ok(Self{walls,angles})
 }
 // pitch is the local road slope in the ego forward direction. Rays stay straight.
 pub(crate) fn scan(&self,x:f64,y:f64,z:f64,heading:f64,pitch:f64,speed:f64,range:f64,objects:Vec<Object>)->PyResult<Vec<Hit>>{
  if !range.is_finite()||range<=0.||![x,y,z,heading,pitch,speed].iter().all(|v|v.is_finite()){return Err(PyValueError::new_err("Invalid laser pose/range"));}
  let mut result=Vec::with_capacity(2*self.angles.len());
  for height in [0.5,3.] {for &angle in &self.angles {
   let (ca,sa)=(angle.cos(),angle.sin());let (ch,sh)=(heading.cos(),heading.sin());
   let (cp,sp)=(pitch.cos(),pitch.sin());
   let dx=ca*cp*ch-sa*sh;let dy=ca*cp*sh+sa*ch;let dz=ca*sp;
   let origin=z+height;let mut best:Hit=(range,0.,range*ca*cp,range*sa,-1,-1,0.);
   for (i,w) in self.walls.iter().enumerate(){
    let (ex,ey)=(w.3-w.0,w.4-w.1);let den=dx*ey-dy*ex;if den.abs()<1e-12{continue;}
    let (ax,ay)=(w.0-x,w.1-y);let t=(ax*ey-ay*ex)/den;let u=(ax*dy-ay*dx)/den;
    if t<0.||t>=best.0||u<0.||u>1.{continue;}
    let base=w.2+u*(w.5-w.2);let hit_z=origin+t*dz;
    if hit_z<base-1e-8||hit_z>base+2.+1e-8{continue;}
    let norm=(ex*ex+ey*ey).sqrt();let echo=if norm>1e-12{(dx*ey-dy*ex).abs()/norm}else{0.};
    best=(t,speed*ca,t*ca*cp,t*sa,0,i as i32,echo.clamp(0.,1.));
   }
   for (i,o) in objects.iter().enumerate(){
    let (ax,ay)=(x-o.0,y-o.1);let a=dx*dx+dy*dy;let b=ax*dx+ay*dy;let c=ax*ax+ay*ay-o.3*o.3;
    let disc=b*b-a*c;if disc<0.||a<1e-12{continue;}
    let mut lo=((-b-disc.sqrt())/a).max(0.);let mut hi=(-b+disc.sqrt())/a;
    let bottom=o.2+if o.6==2{1.}else{0.};let top=o.2+if o.6==2{5.}else{3.};
    if dz.abs()<1e-12 {if origin<bottom||origin>top{continue;}}
    else {let t0=(bottom-origin)/dz;let t1=(top-origin)/dz;lo=lo.max(t0.min(t1));hi=hi.min(t0.max(t1));}
    if lo>hi||lo>=best.0{continue;}
    let hz=origin+lo*dz;let echo=if (hz-bottom).abs()<1e-7||(hz-top).abs()<1e-7 {dz.abs()}else{((ax+lo*dx)*dx+(ay+lo*dy)*dy).abs()/o.3};
    let closing=speed*ca-(o.4*dx+o.5*dy);
    best=(lo,closing,lo*ca*cp,lo*sa,o.6,i as i32,echo.clamp(0.,1.));
   }
   result.push(best);
  }}Ok(result)
 }
}
