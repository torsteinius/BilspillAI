//! Straight rays, two physical heights, sloped curb faces and elevated car bodies.
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
type Wall=(f64,f64,f64,f64,f64,f64);
type Object=(f64,f64,f64,f64,f64,f64,i32);
type Hit=(f64,f64,f64,f64,i32,i32,f64);
type Point=(f64,f64,f64);
type Face=(Point,Point,Point);
struct Ground { a:[f64;3], e1:[f64;3], e2:[f64;3], low:[f64;3], high:[f64;3] }
fn cross(a:[f64;3],b:[f64;3])->[f64;3]{[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}
fn dot(a:[f64;3],b:[f64;3])->f64{a.iter().zip(b).map(|(x,y)|x*y).sum()}
#[pyclass]
pub struct LaserRadar {walls:Vec<Wall>,wall_bounds:Vec<[f64;4]>,angles:Vec<f64>,ground:Vec<Ground>,ground_bounds:Vec<([f64;3],[f64;3])>}
impl LaserRadar {
 fn ground_hit(&self,origin:[f64;3],end:[f64;3])->Option<(f64,f64)>{
  let d=[end[0]-origin[0],end[1]-origin[1],end[2]-origin[2]];
  let length=dot(d,d).sqrt();let mut nearest=1.;let mut echo=0.;
  for (faces,(low,high)) in self.ground.chunks(32).zip(&self.ground_bounds) {
   if (0..3).any(|i|origin[i].min(end[i])>high[i]+1e-8||origin[i].max(end[i])<low[i]-1e-8){continue;}
   for face in faces {
   if (0..3).any(|i|origin[i].min(end[i])>face.high[i]+1e-8||origin[i].max(end[i])<face.low[i]-1e-8){continue;}
   let h=cross(d,face.e2);let determinant=dot(face.e1,h);
   if determinant.abs()<1e-12{continue;}
   let s=[origin[0]-face.a[0],origin[1]-face.a[1],origin[2]-face.a[2]];
   let u=dot(s,h)/determinant;if !(-1e-8..=1.+1e-8).contains(&u){continue;}
   let q=cross(s,face.e1);let v=dot(d,q)/determinant;
   if v< -1e-8||u+v>1.+1e-8{continue;}
   let t=dot(face.e2,q)/determinant;
   if t>1e-8&&t<nearest-1e-8 {
    nearest=t;let normal=cross(face.e1,face.e2);
    echo=(dot(d,normal).abs()/(length*dot(normal,normal).sqrt())).clamp(0.,1.);
   }
   }
  }
  if nearest<1.{Some((nearest,echo))}else{None}
 }
}
#[pymethods]
impl LaserRadar {
 #[new]
 pub(crate) fn new(walls:Vec<Wall>,angles:Vec<f64>)->PyResult<Self>{
  if angles.is_empty()||angles.iter().any(|a|!a.is_finite())||walls.iter().any(|w|![w.0,w.1,w.2,w.3,w.4,w.5].iter().all(|v|v.is_finite())) {return Err(PyValueError::new_err("Invalid laser geometry"));}
  let wall_bounds=walls.chunks(32).map(|chunk|[chunk.iter().map(|w|w.0.min(w.3)).fold(f64::INFINITY,f64::min),chunk.iter().map(|w|w.1.min(w.4)).fold(f64::INFINITY,f64::min),chunk.iter().map(|w|w.0.max(w.3)).fold(f64::NEG_INFINITY,f64::max),chunk.iter().map(|w|w.1.max(w.4)).fold(f64::NEG_INFINITY,f64::max)]).collect();
  Ok(Self{walls,wall_bounds,angles,ground:vec![],ground_bounds:vec![]})
 }
 pub(crate) fn set_ground(&mut self,faces:Vec<Face>)->PyResult<()> {
  let mut ground=vec![];
  for (a,b,c) in faces {
   let a=[a.0,a.1,a.2];let b=[b.0,b.1,b.2];let c=[c.0,c.1,c.2];
   if a.iter().chain(b.iter()).chain(c.iter()).any(|v|!v.is_finite()){return Err(PyValueError::new_err("Invalid road surface"));}
   let e1=[b[0]-a[0],b[1]-a[1],b[2]-a[2]];let e2=[c[0]-a[0],c[1]-a[1],c[2]-a[2]];
   if dot(cross(e1,e2),cross(e1,e2))<1e-20{return Err(PyValueError::new_err("Degenerate road surface"));}
   ground.push(Ground{a,e1,e2,low:std::array::from_fn(|i|a[i].min(b[i]).min(c[i])),high:std::array::from_fn(|i|a[i].max(b[i]).max(c[i]))});
  }
  self.ground_bounds=ground.chunks(32).map(|faces|(
   std::array::from_fn(|i|faces.iter().map(|f|f.low[i]).fold(f64::INFINITY,f64::min)),
   std::array::from_fn(|i|faces.iter().map(|f|f.high[i]).fold(f64::NEG_INFINITY,f64::max)))).collect();
  self.ground=ground;Ok(())
 }
 // Lower sensor sweeps a vertical fan; upper sensor remains a single straight ray.
 // Each candidate is a straight line and is occluded by the opaque road surface.
 pub(crate) fn scan_fan(&self,x:f64,y:f64,z:f64,heading:f64,pitch:f64,speed:f64,range:f64,objects:Vec<Object>,vertical_half_angle:f64)->PyResult<Vec<Hit>> {
  if !vertical_half_angle.is_finite()||vertical_half_angle<=0.||vertical_half_angle>0.35||self.ground.is_empty(){return Err(PyValueError::new_err("Vertical fan requires road geometry and an angle in (0, 0.35] radians"));}
  let mut result=self.scan(x,y,z,heading,pitch,speed,range,objects)?;
  let (ch,sh)=(heading.cos(),heading.sin());let (cp,sp)=(pitch.cos(),pitch.sin());
  for (index,best) in result.iter_mut().enumerate(){
   let angle=self.angles[index%self.angles.len()];let (ca,sa)=(angle.cos(),angle.sin());
   let dx=ca*cp*ch-sa*sh;let dy=ca*cp*sh+sa*ch;let dz=ca*sp;
   let horizontal=dx.hypot(dy);let ux=dx/horizontal;let uy=dy/horizontal;
   let elevation=dz.atan2(horizontal);let height=if index<self.angles.len(){0.5}else{3.};let origin=[x,y,z+height];
   let end=[x+dx*best.0,y+dy*best.0,origin[2]+dz*best.0];
   let ground=self.ground_hit(origin,end);
   if ground.is_some(){*best=(range,0.,range*ca*cp,range*sa,-1,-1,0.);}
   if index<self.angles.len()&&best.4!=0 {
    for (wall_index,w) in self.walls.iter().enumerate(){
     let (ex,ey)=(w.3-w.0,w.4-w.1);let den=ux*ey-uy*ex;if den.abs()<1e-12{continue;}
     let (ax,ay)=(w.0-x,w.1-y);let distance=(ax*ey-ay*ex)/den;let u=(ax*uy-ay*ux)/den;
     if distance<=1e-8||distance>=best.0||!(0. ..=1.).contains(&u){continue;}
     let base=w.2+u*(w.5-w.2);
     let low=((base-origin[2])/distance).atan().max(elevation-vertical_half_angle);
     let high=((base+2.-origin[2])/distance).atan().min(elevation+vertical_half_angle);
     if low>high{continue;}
     // Try the nominal direction, then the highest visible point of the curb.
     for aim in [elevation.clamp(low,high),high] {
      let target_z=origin[2]+distance*aim.tan();let length=distance.hypot(target_z-origin[2]);
      if length>=best.0{continue;}
      if self.ground_hit(origin,[x+ux*distance,y+uy*distance,target_z]).is_some(){continue;}
      let echo=((ux*ey-uy*ex).abs()*aim.cos()/ex.hypot(ey)).clamp(0.,1.);
      *best=(length,speed*ca,distance*(ux*ch+uy*sh),distance*(-ux*sh+uy*ch),0,wall_index as i32,echo);
     }
    }
   }
   // A beam ending in asphalt must never be reported as clear space.
   if best.4<0 {if let Some((fraction,echo))=ground {
    let length=dot([end[0]-x,end[1]-y,end[2]-origin[2]],[end[0]-x,end[1]-y,end[2]-origin[2]]).sqrt()*fraction;
    *best=(length,speed*ca,length*ca*cp,length*sa,3,-1,echo);
   }}
  }
  Ok(result)
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
   for (chunk_index,(chunk,bounds)) in self.walls.chunks(32).zip(&self.wall_bounds).enumerate(){
    // Conservative ray/box slab test: it can only discard impossible hits.
    let mut near=0.0_f64;let mut far=best.0;
    for (origin,direction,low,high) in [(x,dx,bounds[0],bounds[2]),(y,dy,bounds[1],bounds[3])] {
     if direction.abs()<1e-15 {if origin<low-1e-8||origin>high+1e-8{far=-1.;break;}}
     else {let a=(low-1e-8-origin)/direction;let b=(high+1e-8-origin)/direction;near=near.max(a.min(b));far=far.min(a.max(b));}
    }
    if near>far{continue;}
    for (local_index,w) in chunk.iter().enumerate(){
    let i=chunk_index*32+local_index;
    let (ex,ey)=(w.3-w.0,w.4-w.1);let den=dx*ey-dy*ex;if den.abs()<1e-12{continue;}
    let (ax,ay)=(w.0-x,w.1-y);let t=(ax*ey-ay*ex)/den;let u=(ax*dy-ay*dx)/den;
    if t<0.||t>=best.0||u<0.||u>1.{continue;}
    let base=w.2+u*(w.5-w.2);let hit_z=origin+t*dz;
    if hit_z<base-1e-8||hit_z>base+2.+1e-8{continue;}
    let norm=(ex*ex+ey*ey).sqrt();let echo=if norm>1e-12{(dx*ey-dy*ex).abs()/norm}else{0.};
    best=(t,speed*ca,t*ca*cp,t*sa,0,i as i32,echo.clamp(0.,1.));
   }
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
