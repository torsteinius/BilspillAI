//! Whole deterministic evaluation rollout. No learning, respawns, cones or UI.
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use crate::laser::LaserRadar;
use crate::{track::RoadGeometry, sectors::SectorRadar, local::LocalNetwork, car::swept};
type Pose = (f64,f64,f64,f64,f64,f64,f64,bool,f64);
#[derive(Clone)]
struct Car { x:f64,y:f64,z:f64,h:f64,factor:f64,direction:f64,travel:f64,dead:bool,speed:f64 }
impl Car { fn point(&self)->(f64,f64,f64){(self.x,self.y,self.z)} }
#[derive(Clone,Default)]
struct Pair { armed:bool,done:bool,stable:usize,travel:(f64,f64) }
fn passes(cars:&[Car],road:&mut RoadGeometry,perimeter:f64,range:f64,pairs:&mut [Pair])->Vec<usize>{
 let n=cars.len();let mut result=vec![0;n];
 let positions:Vec<_>=cars.iter().map(|c|road.progress(c.x,c.y,c.z)).collect();
 for i in 0..n {for j in 0..n {
  if i==j {continue;}
  let a=&cars[i];let b=&cars[j];let state=&mut pairs[i*n+j];
  if a.dead||b.dead||a.direction!=b.direction {state.armed=false;state.stable=0;continue;}
  if state.done {continue;}
  let gap=((positions[j]-positions[i]+perimeter/2.).rem_euclid(perimeter)-perimeter/2.)*a.direction;
  let delta=(positions[i]-positions[j]).abs();
  let same=(a.z-b.z).abs()<14. || delta.min(perimeter-delta)<=range*1.5;
  if !same||gap.abs()>180. {state.armed=false;state.stable=0;continue;}
  if gap>=18.&&gap<=120. {state.armed=true;}
  let completed=state.armed&&gap<= -18.&&a.travel>state.travel.0&&b.travel>state.travel.1;
  state.travel=(a.travel,b.travel);
  state.stable=if completed {state.stable+1}else{0};
  if state.stable>=10 {result[i]+=1;state.done=true;}
 }}result
}
#[pyclass]
pub struct SectorEvaluation { road:RoadGeometry,radar:SectorRadar,net:LocalNetwork,weights:Vec<Vec<f64>>,perimeter:f64,range:f64,brake:f64, channels:usize, steering_boost:f64, laser:Option<LaserRadar>, models:Vec<LocalNetwork>, modes:Vec<usize> }
#[pymethods]
impl SectorEvaluation {
 #[new]
 fn new(segments:Vec<Vec<f64>>,half_width:f64,walls:Vec<(f64,f64,f64,f64,f64)>,edges:Vec<f64>,sizes:Vec<usize>,links:Vec<Vec<Vec<usize>>>,weights:Vec<Vec<f64>>,perimeter:f64,range:f64,brake:f64)->PyResult<Self>{
  if sizes.last()!=Some(&2)||!(sizes.first()==Some(&(2*(edges.len().saturating_sub(1))))||sizes.first()==Some(&(3*(edges.len().saturating_sub(1)))))||weights.len()<2||!perimeter.is_finite()||perimeter<=0.||!range.is_finite()||range<=0.||!brake.is_finite()||brake<0.||brake>=1. {return Err(PyValueError::new_err("Invalid sector evaluation configuration"));}
  let net=LocalNetwork::new(sizes.clone(),links)?;
  for w in &weights {net.forward(vec![0.;sizes[0]],w.clone(),false)?;}
  let channels=sizes[0]/(edges.len()-1);
  Ok(Self{road:RoadGeometry::new(segments,half_width)?,radar:SectorRadar::new(walls,Some(edges))?,net,weights,perimeter,range,brake,channels,steering_boost:0.,laser:None,models:vec![],modes:vec![]})
 }
 fn set_laser_models(&mut self,walls:Vec<(f64,f64,f64,f64,f64,f64)>,angles:Vec<f64>,sizes:Vec<Vec<usize>>,links:Vec<Vec<Vec<Vec<usize>>>>,weights:Vec<Vec<f64>>,modes:Vec<usize>)->PyResult<()> {
  if sizes.len()!=weights.len()||links.len()!=weights.len()||modes.len()!=weights.len()||weights.len()<2 {return Err(PyValueError::new_err("Mixed model count mismatch"));}
  let mut models=vec![];
  for i in 0..weights.len(){
   let count=match modes[i]{2=>60,3=>90,6=>366,_=>return Err(PyValueError::new_err("Unknown mixed sensor mode"))};
   if sizes[i].first()!=Some(&count)||sizes[i].last()!=Some(&2){return Err(PyValueError::new_err("Mixed model shape mismatch"));}
   let net=LocalNetwork::new(sizes[i].clone(),links[i].clone())?;net.forward(vec![0.;count],weights[i].clone(),false)?;models.push(net);
  }
  self.laser=Some(LaserRadar::new(walls,angles)?);self.models=models;self.modes=modes;self.weights=weights;Ok(())
 }
 fn set_steering_boost(&mut self,boost:f64)->PyResult<()> {
  if !boost.is_finite()||boost<0. {return Err(PyValueError::new_err("Invalid steering boost"));}
  self.steering_boost=boost;Ok(())
 }
 // Model order: candidate, fixed traffic reference, then background models.
 fn run(&mut self,initial:Vec<Pose>,role:usize,steps:usize,pass_reward:f64,car_penalty:f64)->PyResult<(f64,f64,usize,usize,bool)>{
  let n=initial.len();
  if n<5||n>20||role>=5||steps==0||self.weights.len()!=n-3||!pass_reward.is_finite()||!car_penalty.is_finite(){return Err(PyValueError::new_err("Invalid evaluation rollout"));}
  let mut cars:Vec<_>=initial.into_iter().map(|c|Car{x:c.0,y:c.1,z:c.2,h:c.3,factor:c.4,direction:c.5,travel:c.6,dead:c.7,speed:c.8}).collect();
  let mut pairs=vec![Pair::default();n*n];
  for i in 0..n {for j in 0..n {pairs[i*n+j].travel=(cars[i].travel,cars[j].travel);}}
  passes(&cars,&mut self.road,self.perimeter,self.range,&mut pairs);
  let mut reward=0.;let mut distance=0.;let mut count=0;let mut survived=0;
  for tick in 0..steps {
   let mut controls=vec![(0.,0.,0.);n];
   for i in 0..n {
    let c=&cars[i];if c.dead {continue;}
    let objects=cars.iter().enumerate().filter(|(j,o)|*j!=i&&!o.dead).map(|(_,o)|(o.x,o.y,o.z,7.,o.speed*o.h.cos(),o.speed*o.h.sin(),2)).collect();
    let index=if i>=5 {i-3}else if i==role {0}else{1};
    let mode=if self.models.is_empty(){self.channels}else{self.modes[index]};
    let input=if mode==6 {
        let pitch=self.road.pitch(c.x,c.y,c.z,c.h);
        self.laser.as_ref().unwrap().scan(c.x,c.y,c.z,c.h,pitch,c.speed,self.range,objects)?.iter().flat_map(|r|[r.0/self.range,(r.1/10.8).clamp(-1.,1.),r.6]).collect()
    } else if mode==3 {
        self.radar.scan_echo(c.x,c.y,c.z,c.h,c.speed,self.range,objects)?.iter().flat_map(|r|[r.0/self.range,(r.1/10.8).clamp(-1.,1.),r.6]).collect()
    } else {
        self.radar.scan(c.x,c.y,c.z,c.h,c.speed,self.range,objects)?.iter().flat_map(|r|[r.0/self.range,(r.1/10.8).clamp(-1.,1.)]).collect()
    };
    let net=if self.models.is_empty(){&self.net}else{&self.models[index]};
    let out=net.forward(input,self.weights[index].clone(),false)?;
    controls[i]=(out[0],(-out[1]).max(0.),out[1].max(0.));
   }
   let old:Vec<_>=cars.iter().map(|c|c.point()).collect();let active:Vec<_>=cars.iter().map(|c|!c.dead).collect();
   let before=cars[role].travel;let mut car_hit=vec![false;n];
   for i in 0..n {
    let c=&mut cars[i];if c.dead{continue;}
    let along=self.road.progress(c.x,c.y,c.z);let (steer,brake,throttle)=controls[i];
    c.h+=0.045*(steer+self.steering_boost*steer.powi(3));c.speed=3.*c.factor*(1.-self.brake*brake)*(1.+0.5*throttle);
    c.x+=c.speed*c.h.cos();c.y+=c.speed*c.h.sin();c.z=self.road.locate(c.x,c.y,c.z).2;
    c.travel+=((self.road.progress(c.x,c.y,c.z)-along+self.perimeter/2.).rem_euclid(self.perimeter)-self.perimeter/2.)*c.direction;
    for t in [0.,0.5,1.] {if self.road.clearance(old[i].0+(c.x-old[i].0)*t,old[i].1+(c.y-old[i].1)*t,old[i].2+(c.z-old[i].2)*t)<=7. {c.dead=true;}}
   }
   for i in 0..n {for j in i+1..n {if active[i]&&active[j]&&swept(old[i],old[j],cars[i].point(),cars[j].point())-14.<=0. {cars[i].dead=true;cars[j].dead=true;car_hit[i]=true;car_hit[j]=true;}}}
   let passed=passes(&cars,&mut self.road,self.perimeter,self.range,&mut pairs)[role];count+=passed;reward+=pass_reward*passed as f64;
   distance+=(cars[role].travel-before).max(0.);survived=tick+1;
   if cars[role].dead {reward-=if car_hit[role]{car_penalty}else{50.};break;}
  }
  Ok((reward,distance,count,survived,cars[role].dead))
 }
}
