use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct RoadGeometry {
    segments: Vec<Vec<f64>>,
    half_width: f64,
    lipschitz: f64,
    cache: HashMap<(i64, i64, i64), Vec<usize>>,
}
fn project(x: f64, y: f64, s: &[f64]) -> (f64, f64) {
    let t = (((x - s[0]) * s[2] + (y - s[1]) * s[3]) / s[4]).clamp(0., 1.);
    (
        (x - s[0] - t * s[2]).powi(2) + (y - s[1] - t * s[3]).powi(2),
        t,
    )
}
impl RoadGeometry {
    fn hit(&mut self, x: f64, y: f64, z: f64) -> (f64, f64, f64, usize) {
        let key = (
            (x / 32.).floor() as i64,
            (y / 32.).floor() as i64,
            (z / 32.).floor() as i64,
        );
        if !self.cache.contains_key(&key) {
            let q = [
                key.0 as f64 * 32. + 16.,
                key.1 as f64 * 32. + 16.,
                key.2 as f64 * 32. + 16.,
            ];
            let mut upper = f64::INFINITY;
            for s in &self.segments {
                let (square, t) = project(q[0], q[1], s);
                upper = upper.min((square + (q[2] - s[6] - t * s[7]).powi(2)).sqrt());
            }
            let limit = upper + (1. + self.lipschitz) * 3_f64.sqrt() * 16.;
            let mut candidates = Vec::new();
            for (i, s) in self.segments.iter().enumerate() {
                let a = [s[0], s[1], s[6]];
                let b = [s[0] + s[2], s[1] + s[3], s[6] + s[7]];
                let lower = (0..3)
                    .map(|j| {
                        (a[j].min(b[j]) - q[j])
                            .max(0.)
                            .max(q[j] - a[j].max(b[j]))
                            .powi(2)
                    })
                    .sum::<f64>()
                    .sqrt();
                if lower <= limit {
                    candidates.push(i);
                }
            }
            if self.cache.len() >= 8192 {
                self.cache.clear();
            }
            self.cache.insert(key, candidates);
        }
        let mut best = f64::INFINITY;
        let mut hit = (0., 0., 0., 0);
        for &i in &self.cache[&key] {
            let s = &self.segments[i];
            let (square, t) = project(x, y, s);
            let height = s[6] + t * s[7];
            let score = square + (z - height).powi(2);
            if score < best {
                best = score;
                hit = (square.sqrt(), s[5] + t * s[8], height, i);
            }
        }
        hit
    }
}
#[pymethods]
impl RoadGeometry {
    #[new]
    pub(crate) fn new(segments: Vec<Vec<f64>>, half_width: f64) -> PyResult<Self> {
        if segments.is_empty()
            || !half_width.is_finite()
            || half_width <= 0.
            || segments
                .iter()
                .any(|s| s.len() != 9 || s.iter().any(|v| !v.is_finite()) || s[4] <= 0.)
        {
            return Err(PyValueError::new_err("Invalid road geometry"));
        }
        let lipschitz = (1.
            + segments
                .iter()
                .map(|s| s[7].powi(2) / s[4])
                .fold(0., f64::max))
        .sqrt();
        Ok(Self {
            segments,
            half_width,
            lipschitz,
            cache: HashMap::new(),
        })
    }
    pub(crate) fn locate(&mut self, x: f64, y: f64, z: f64) -> (f64, f64, f64, usize) {
        self.hit(x, y, z)
    }
    pub(crate) fn clearance(&mut self, x: f64, y: f64, z: f64) -> f64 {
        self.half_width - self.hit(x, y, z).0
    }
    pub(crate) fn progress(&mut self, x: f64, y: f64, z: f64) -> f64 {
        self.hit(x, y, z).1
    }
    pub(crate) fn pitch(&mut self,x:f64,y:f64,z:f64,heading:f64)->f64 {
        let i=self.hit(x,y,z).3;let s=&self.segments[i];
        (s[7]*(s[2]*heading.cos()+s[3]*heading.sin())/s[4]).atan()
    }
    fn sensors(
        &mut self,
        x: f64,
        y: f64,
        z: f64,
        heading: f64,
        angles: Vec<f64>,
        obstacles: Vec<(f64, f64, f64)>,
    ) -> Vec<f64> {
        angles
            .iter()
            .map(|angle| {
                let dx = (heading + angle).cos();
                let dy = (heading + angle).sin();
                let mut distance: f64 = 0.;
                for _ in 0..55 {
                    let gap = self.clearance(x + distance * dx, y + distance * dy, z);
                    if gap < 0.15 || distance >= 180. {
                        break;
                    }
                    distance = 180_f64.min(distance + 0.1_f64.max(gap * 0.95));
                }
                for &(ox, oy, radius) in &obstacles {
                    let ox = ox - x;
                    let oy = oy - y;
                    let projection = ox * dx + oy * dy;
                    let discriminant =
                        radius * radius - (ox * ox + oy * oy - projection * projection);
                    if discriminant >= 0. {
                        let near = projection - discriminant.sqrt();
                        let far = projection + discriminant.sqrt();
                        if far >= 0. {
                            distance = distance.min(near.max(0.));
                        }
                    }
                }
                distance
            })
            .collect()
    }
}
