use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use std::f64::consts::PI;
fn cross(a:(f64,f64),b:(f64,f64))->f64 {a.0*b.1-a.1*b.0}
fn dot(a:(f64,f64),b:(f64,f64))->f64 {a.0*b.0+a.1*b.1}
fn clipped_nearest(a:(f64,f64),b:(f64,f64),lo:(f64,f64),hi:(f64,f64))->Option<(f64,f64)>{
    let mut t0:f64=0.;let mut t1:f64=1.;
    for (u,v) in [(cross(lo,a),cross(lo,b)),(cross(a,hi),cross(b,hi))]{
        if u<0. && v<0. {return None;}
        if u<0.{t0=t0.max(u/(u-v));}else if v<0.{t1=t1.min(u/(u-v));}
    }
    if t0>t1{return None;}
    let d=(b.0-a.0,b.1-a.1);let sq=dot(d,d);
    let t=if sq>1e-12{(-dot(a,d)/sq).clamp(t0,t1)}else{t0};Some((a.0+t*d.0,a.1+t*d.1))
}
#[pyclass]
pub struct SectorRadar { walls:Vec<(f64,f64,f64,f64,f64)>, edges:Vec<f64> }
#[pymethods]
impl SectorRadar {
    #[new]
    #[pyo3(signature = (walls, edges=None))]
    fn new(walls:Vec<(f64,f64,f64,f64,f64)>,edges:Option<Vec<f64>>)->PyResult<Self>{
        let edges=edges.unwrap_or_else(||(0..=15).map(|i|-PI/2.+i as f64*PI/15.).collect());
        if edges.len()<2 || edges.iter().any(|v|!v.is_finite()) || edges.windows(2).any(|w|w[1]<=w[0]) || edges[0]< -PI || edges[edges.len()-1]>PI || edges.windows(2).any(|w|w[1]-w[0]>=PI) {
            return Err(PyValueError::new_err("Sector edges must increase within -pi to pi, with widths below pi"));
        }
        Ok(Self{walls,edges})
    }
    // Obstacles: x,y,z,radius,vx,vy,kind (1 cone, 2 car). Wall kind is zero.
    fn scan(&self,x:f64,y:f64,z:f64,heading:f64,speed:f64,range:f64,objects:Vec<(f64,f64,f64,f64,f64,f64,i32)>)->PyResult<Vec<(f64,f64,f64,f64,i32,i32)>>{
        if !range.is_finite() || range<=0.{return Err(PyValueError::new_err("Invalid radar range"));}
        let cs=heading.cos();let sn=heading.sin();let local=|px:f64,py:f64|((px-x)*cs+(py-y)*sn,-(px-x)*sn+(py-y)*cs);
        let walls:Vec<_>=self.walls.iter().enumerate().filter(|(_,w)|(w.4-z).abs()<14.).map(|(i,w)|(i,local(w.0,w.1),local(w.2,w.3))).filter(|(_,a,b)|{
            let minx=a.0.min(b.0);let maxx=a.0.max(b.0);let miny=a.1.min(b.1);let maxy=a.1.max(b.1);
            maxx>=-range && minx<=range && miny<=range && maxy>=-range
        }).collect();
        let mut result=Vec::new();
        for edge in self.edges.windows(2) {
            let low=edge[0];let high=edge[1];let lo=(low.cos(),low.sin());let hi=(high.cos(),high.sin());
            let mid=(low+high)/2.;let mut best=(range,0.,range*mid.cos(),range*mid.sin(),-1,-1);
            let mut consider=|p:(f64,f64),vx:f64,vy:f64,kind:i32,index:i32|{
                let d=dot(p,p).sqrt();if d<best.0 {
                    let closing=if d>1e-8{-dot((vx-speed,vy),p)/d}else{0.};best=(d,closing,p.0,p.1,kind,index);
                }
            };
            for (i,a,b) in &walls {if let Some(p)=clipped_nearest(*a,*b,lo,hi){consider(p,0.,0.,0,*i as i32);}}
            for (i,o) in objects.iter().enumerate(){
                if (o.2-z).abs()>=14.{continue;}
                let c=local(o.0,o.1);let norm=dot(c,c).sqrt();let r=o.3;
                if norm-r>range{continue;}
                let vx=o.4*cs+o.5*sn;let vy=-o.4*sn+o.5*cs;
                if norm<=r {consider((0.,0.),vx,vy,o.6,i as i32);continue;}
                if cross(lo,c)>=-1e-10 && cross(c,hi)>=-1e-10{let f=1.-r/norm;consider((c.0*f,c.1*f),vx,vy,o.6,i as i32);}
                for ray in [lo,hi]{
                    let proj=dot(c,ray);let disc=r*r-dot(c,c)+proj*proj;
                    if disc>=-1e-10 && proj>=0.{let t=(proj-disc.max(0.).sqrt()).max(0.);consider((ray.0*t,ray.1*t),vx,vy,o.6,i as i32);}
                }
            }
            result.push(best);
        }Ok(result)
    }
}
