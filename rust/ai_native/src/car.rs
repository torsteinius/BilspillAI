//! Batched numeric kernels; Python retains object IDs and event ordering.
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
type Point = (f64, f64, f64);
type Target = (f64, f64, f64, f64, f64, bool);

#[pyfunction]
pub fn cone_targets(
    ego: (f64, f64, f64, f64, bool),
    targets: Vec<Target>,
    range: f64,
    half_angle: f64,
) -> Vec<(usize, f64, f64, f64, f64, f64, f64)> {
    let (x, y, heading, ego_speed, crashed) = ego;
    if crashed {
        return vec![];
    }
    let (sin, cos) = heading.sin_cos();
    targets
        .iter()
        .enumerate()
        .filter_map(|(i, &(tx, ty, th, speed, radius, dead))| {
            let (dx, dy) = (tx - x, ty - y);
            let distance = dx.hypot(dy);
            let forward = dx * cos + dy * sin;
            let lateral = -dx * sin + dy * cos;
            if dead
                || distance >= range
                || forward < 0.
                || lateral.atan2(forward).abs() > half_angle
            {
                return None;
            }
            let vx = speed * th.cos() - ego_speed * cos;
            let vy = speed * th.sin() - ego_speed * sin;
            let closing = if distance != 0. {
                -(vx * dx + vy * dy) / distance
            } else {
                0.
            };
            Some((
                i,
                (distance - radius).max(0.),
                forward,
                lateral,
                speed,
                closing,
                vx * cos + vy * sin,
            ))
        })
        .collect()
}

pub(crate) fn swept(a: Point, b: Point, next_a: Point, next_b: Point) -> f64 {
    let r = [a.0 - b.0, a.1 - b.1, a.2 - b.2];
    let v = [
        next_a.0 - next_b.0 - r[0],
        next_a.1 - next_b.1 - r[1],
        next_a.2 - next_b.2 - r[2],
    ];
    let square = v.iter().map(|v| v * v).sum::<f64>();
    let t = if square != 0. {
        (-r.iter().zip(v).map(|(r, v)| r * v).sum::<f64>() / square).clamp(0., 1.)
    } else {
        0.
    };
    r.iter()
        .zip(v)
        .map(|(r, v)| (r + t * v).powi(2))
        .sum::<f64>()
        .sqrt()
}

#[pyfunction]
pub fn separations(
    old: Vec<Point>,
    positions: Vec<Point>,
    cones: Vec<(f64, f64, f64, f64)>,
    radius: f64,
) -> PyResult<(Vec<Vec<f64>>, Vec<Vec<f64>>)> {
    if old.len() != positions.len() {
        return Err(PyValueError::new_err("Position counts must match"));
    }
    let cone_gaps = positions
        .iter()
        .enumerate()
        .map(|(i, &p)| {
            cones
                .iter()
                .map(|&(x, y, z, r)| swept(old[i], (x, y, z), p, (x, y, z)) - radius - r)
                .collect()
        })
        .collect();
    let car_gaps = positions
        .iter()
        .enumerate()
        .map(|(i, &p)| {
            positions
                .iter()
                .enumerate()
                .map(|(j, &q)| swept(old[i], old[j], p, q) - 2. * radius)
                .collect()
        })
        .collect();
    Ok((cone_gaps, car_gaps))
}
