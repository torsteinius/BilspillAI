mod car;
mod batch;
mod evaluation;
mod local;
mod sectors;
mod laser;
mod track;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use rand_distr::{Distribution, StandardNormal};

fn invalid(message: &str) -> PyErr {
    PyValueError::new_err(message.to_owned())
}

#[pyclass]
struct DenseNetwork {
    sizes: Vec<usize>,
    weight_count: usize,
}

impl DenseNetwork {
    fn calculate(&self, inputs: &[f64], weights: &[f64], normalized: bool) -> Vec<f64> {
        let mut values = inputs.to_vec();
        let mut offset = 0;
        for (index, pair) in self.sizes.windows(2).enumerate() {
            let (a, b) = (pair[0], pair[1]);
            let mut next = Vec::with_capacity(b);
            for neuron in 0..b {
                let row = offset + neuron * (a + 1);
                let mut total = 0.0;
                for (i, value) in values.iter().enumerate() {
                    if *value != 0.0 {
                        total += weights[row + i] * value;
                    }
                }
                next.push(total + weights[row + a]);
            }
            if normalized && index < self.sizes.len() - 2 {
                let mean = next.iter().sum::<f64>() / b as f64;
                let variance = next.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / b as f64;
                let scale = (variance + 1e-5).sqrt();
                for v in &mut next {
                    *v = (*v - mean) / scale;
                }
            }
            for v in &mut next {
                *v = v.tanh();
            }
            values = next;
            offset += (a + 1) * b;
        }
        values
    }

    fn activations(&self, inputs: &[f64], weights: &[f64]) -> Vec<Vec<f64>> {
        let mut result = vec![inputs.to_vec()];
        let mut offset = 0;
        for (layer, pair) in self.sizes.windows(2).enumerate() {
            let (a, b) = (pair[0], pair[1]);
            let values = result.last().unwrap();
            let next = (0..b)
                .map(|n| {
                    let row = offset + n * (a + 1);
                    let total = values
                        .iter()
                        .enumerate()
                        .map(|(i, v)| weights[row + i] * v)
                        .sum::<f64>()
                        + weights[row + a];
                    if layer == self.sizes.len() - 2 {
                        total
                    } else {
                        total.tanh()
                    }
                })
                .collect();
            result.push(next);
            offset += (a + 1) * b;
        }
        result
    }

    fn validate(&self, inputs: &[f64], weights: &[f64]) -> PyResult<()> {
        if inputs.len() != self.sizes[0] || weights.len() != self.weight_count {
            return Err(invalid("Inputs and weights must match the architecture"));
        }
        Ok(())
    }
}

#[pymethods]
impl DenseNetwork {
    #[new]
    fn new(sizes: Vec<usize>) -> PyResult<Self> {
        if sizes.len() < 2 || sizes.contains(&0) {
            return Err(invalid(
                "Architecture needs at least two positive layer sizes",
            ));
        }
        let mut weight_count = 0usize;
        for pair in sizes.windows(2) {
            weight_count = pair[0]
                .checked_add(1)
                .and_then(|a| a.checked_mul(pair[1]))
                .and_then(|n| weight_count.checked_add(n))
                .ok_or_else(|| invalid("Architecture is too large"))?;
        }
        Ok(Self {
            sizes,
            weight_count,
        })
    }

    fn forward(&self, inputs: Vec<f64>, weights: Vec<f64>, normalized: bool) -> PyResult<Vec<f64>> {
        self.validate(&inputs, &weights)?;
        Ok(self.calculate(&inputs, &weights, normalized))
    }

    /// Hidden tanh layers and a linear output: exploration happens before tanh.
    fn latent(&self, inputs: Vec<f64>, weights: Vec<f64>) -> PyResult<Vec<f64>> {
        self.validate(&inputs, &weights)?;
        Ok(self.activations(&inputs, &weights).pop().unwrap())
    }

    fn gradient(
        &self,
        inputs: Vec<f64>,
        weights: Vec<f64>,
        output_index: usize,
    ) -> PyResult<(f64, Vec<f64>)> {
        self.validate(&inputs, &weights)?;
        if output_index >= *self.sizes.last().unwrap() {
            return Err(invalid("Output index out of range"));
        }
        let activations = self.activations(&inputs, &weights);
        let mut offsets = vec![0];
        for pair in self.sizes.windows(2) {
            offsets.push(offsets.last().unwrap() + (pair[0] + 1) * pair[1]);
        }
        let mut gradient = vec![0.; self.weight_count];
        let mut delta = vec![0.; *self.sizes.last().unwrap()];
        delta[output_index] = 1.;
        for layer in (0..self.sizes.len() - 1).rev() {
            let values = &activations[layer];
            let stride = values.len() + 1;
            let offset = offsets[layer];
            for (n, d) in delta.iter().enumerate() {
                for (i, v) in values.iter().enumerate() {
                    gradient[offset + n * stride + i] = d * v;
                }
                gradient[offset + n * stride + stride - 1] = *d;
            }
            if layer > 0 {
                delta = values
                    .iter()
                    .enumerate()
                    .map(|(i, v)| {
                        (1. - v * v)
                            * delta
                                .iter()
                                .enumerate()
                                .map(|(n, d)| weights[offset + n * stride + i] * d)
                                .sum::<f64>()
                    })
                    .collect();
            }
        }
        Ok((activations.last().unwrap()[output_index], gradient))
    }

    fn forward_batch(
        &self,
        observations: Vec<Vec<f64>>,
        weights: Vec<f64>,
        normalized: bool,
    ) -> PyResult<Vec<Vec<f64>>> {
        if weights.len() != self.weight_count {
            return Err(invalid("Weights must match the architecture"));
        }
        for inputs in &observations {
            self.validate(inputs, &weights)?;
        }
        Ok(observations
            .iter()
            .map(|v| self.calculate(v, &weights, normalized))
            .collect())
    }
}

#[pyclass]
struct EvolutionRng {
    rng: ChaCha8Rng,
}

#[pymethods]
impl EvolutionRng {
    #[new]
    fn new(seed: u64) -> Self {
        Self {
            rng: ChaCha8Rng::seed_from_u64(seed),
        }
    }

    /// Return Gaussian perturbations of a parent, optionally freezing weights.
    #[pyo3(signature = (parent, count, sigma, mask=None))]
    fn mutate(
        &mut self,
        parent: Vec<f64>,
        count: usize,
        sigma: f64,
        mask: Option<Vec<bool>>,
    ) -> PyResult<Vec<Vec<f64>>> {
        check_sigma(sigma)?;
        if mask.as_ref().is_some_and(|m| m.len() != parent.len()) {
            return Err(invalid("Mutation mask must contain one boolean per weight"));
        }
        Ok((0..count)
            .map(|_| {
                parent
                    .iter()
                    .enumerate()
                    .map(|(i, v)| {
                        if mask.as_ref().is_some_and(|m| !m[i]) {
                            *v
                        } else {
                            let noise: f64 = StandardNormal.sample(&mut self.rng);
                            v + sigma * noise
                        }
                    })
                    .collect()
            })
            .collect())
    }

    /// Keep elites exactly; choose one parent uniformly for each new candidate.
    fn breed(
        &mut self,
        elites: Vec<Vec<f64>>,
        population_size: usize,
        sigma: f64,
    ) -> PyResult<Vec<Vec<f64>>> {
        check_sigma(sigma)?;
        if elites.is_empty()
            || population_size < elites.len()
            || elites.iter().any(|e| e.len() != elites[0].len())
        {
            return Err(invalid(
                "Expected equally sized elites and population_size >= elite count",
            ));
        }
        let mut population = elites.clone();
        while population.len() < population_size {
            let parent = self.rng.gen_range(0..elites.len());
            population.push(
                elites[parent]
                    .iter()
                    .map(|v| {
                        let noise: f64 = StandardNormal.sample(&mut self.rng);
                        v + sigma * noise
                    })
                    .collect(),
            );
        }
        Ok(population)
    }
}

fn check_sigma(sigma: f64) -> PyResult<()> {
    if !sigma.is_finite() || sigma < 0.0 {
        return Err(invalid("Mutation spread must be finite and nonnegative"));
    }
    Ok(())
}

#[pymodule]
fn bilspill_ai_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(car::cone_targets, m)?)?;
    m.add_function(wrap_pyfunction!(car::separations, m)?)?;
    m.add_class::<track::RoadGeometry>()?;
    m.add_function(wrap_pyfunction!(batch::policy_batch,m)?)?;
    m.add_class::<evaluation::SectorEvaluation>()?;
    m.add_class::<DenseNetwork>()?;
    m.add_class::<local::LocalNetwork>()?;
    m.add_class::<sectors::SectorRadar>()?;
    m.add_class::<laser::LaserRadar>()?;
    m.add_class::<EvolutionRng>()?;
    Ok(())
}
