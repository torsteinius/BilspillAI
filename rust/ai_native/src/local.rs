use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
#[pyclass]
pub struct LocalNetwork { sizes: Vec<usize>, links: Vec<Vec<Vec<usize>>>, count: usize }
impl LocalNetwork {
    fn check(&self,x:&[f64],w:&[f64])->PyResult<()> {
        if x.len()!=self.sizes[0] || w.len()!=self.count { return Err(PyValueError::new_err("Local network shape mismatch")); } Ok(())
    }
    fn acts(&self,x:&[f64],w:&[f64])->Vec<Vec<f64>> {
        let mut acts=vec![x.to_vec()];let mut offset=0;
        for (l,layer) in self.links.iter().enumerate() {
            let input=acts.last().unwrap();let mut out=Vec::new();
            for links in layer {
                let mut v=w[offset+links.len()];
                for (k,i) in links.iter().enumerate(){v+=w[offset+k]*input[*i];}
                out.push(if l+1==self.links.len(){v}else{v.tanh()});offset+=links.len()+1;
            } acts.push(out);
        } acts
    }
}
#[pymethods]
impl LocalNetwork {
    #[new]
    fn new(sizes:Vec<usize>,links:Vec<Vec<Vec<usize>>>)->PyResult<Self>{
        if sizes.len()<2 || sizes.contains(&0) || links.len()+1!=sizes.len(){return Err(PyValueError::new_err("Invalid local topology"));}
        let mut count=0;
        for (l,layer) in links.iter().enumerate(){
            if layer.len()!=sizes[l+1] {return Err(PyValueError::new_err("Invalid layer"));}
            for row in layer {if row.iter().any(|i|*i>=sizes[l]){return Err(PyValueError::new_err("Invalid connection"));} count+=row.len()+1;}
        } Ok(Self{sizes,links,count})
    }
    fn latent(&self,inputs:Vec<f64>,weights:Vec<f64>)->PyResult<Vec<f64>>{self.check(&inputs,&weights)?;Ok(self.acts(&inputs,&weights).pop().unwrap())}
    fn forward(&self,inputs:Vec<f64>,weights:Vec<f64>,_normalized:bool)->PyResult<Vec<f64>>{Ok(self.latent(inputs,weights)?.iter().map(|v|v.tanh()).collect())}
    fn gradient(&self,inputs:Vec<f64>,weights:Vec<f64>,output_index:usize)->PyResult<(f64,Vec<f64>)>{
        self.check(&inputs,&weights)?;
        if output_index>=*self.sizes.last().unwrap(){return Err(PyValueError::new_err("Invalid output"));}
        let a=self.acts(&inputs,&weights);let mut offsets=vec![0];
        for layer in &self.links {offsets.push(offsets.last().unwrap()+layer.iter().map(|r|r.len()+1).sum::<usize>());}
        let mut g=vec![0.;self.count];let mut delta=vec![0.;*self.sizes.last().unwrap()];delta[output_index]=1.;
        for l in (0..self.links.len()).rev(){
            let mut prev=vec![0.;self.sizes[l]];let mut off=offsets[l];
            for (n,links) in self.links[l].iter().enumerate(){
                for (k,i) in links.iter().enumerate(){g[off+k]=delta[n]*a[l][*i];prev[*i]+=weights[off+k]*delta[n];}
                g[off+links.len()]=delta[n];off+=links.len()+1;
            }
            if l>0{for (i,v) in prev.iter_mut().enumerate(){*v*=1.-a[l][i]*a[l][i];}}
            delta=prev;
        } Ok((a.last().unwrap()[output_index],g))
    }
}
