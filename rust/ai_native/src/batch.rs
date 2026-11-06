use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use crate::local::LocalNetwork;
#[pyfunction]
pub fn policy_batch(actor:PyRef<LocalNetwork>,baseline:PyRef<LocalNetwork>,aw:Vec<f64>,bw:Vec<f64>,rows:Vec<(Vec<f64>,Vec<f64>,Vec<f64>,f64,bool)>)->PyResult<(Vec<f64>,Vec<f64>)>{
 if rows.is_empty(){return Err(PyValueError::new_err("Empty batch"));}
 let mut ag=vec![0.;aw.len()];let mut bg=vec![0.;bw.len()];let n=rows.len() as f64;let sigma=0.15_f64;
 for (x,samples,behavior,reward,incremental) in rows {
  if samples.len()!=behavior.len(){return Err(PyValueError::new_err("Action mismatch"));}
  let mut outputs=Vec::new();
  for i in 0..samples.len(){outputs.push(actor.gradient(x.clone(),aw.clone(),i)?);}
  let log_ratio=samples.iter().zip(&behavior).zip(&outputs).map(|((z,old),(mean,_))|(z-old).powi(2)-(z-mean).powi(2)).sum::<f64>()/(2.*sigma*sigma);
  let ratio=log_ratio.clamp(-20.,2_f64.ln()).exp();
  let (base,gradient)=baseline.gradient(x,bw.clone(),0)?;
  let advantage=reward/50.-if incremental{0.}else{base};
  for (z,(mean,g)) in samples.iter().zip(outputs){for (a,v) in ag.iter_mut().zip(g){*a+=ratio*advantage*(z-mean)/(sigma*sigma)*v;}}
  for (b,v) in bg.iter_mut().zip(gradient){*b+=advantage*v;}
 }
 for v in ag.iter_mut().chain(bg.iter_mut()){*v/=n;}Ok((ag,bg))
}
