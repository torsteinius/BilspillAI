//! Rust/WebAssembly renderer. Python owns the simulation; wgpu owns all 3D drawing.
use std::sync::{Arc, Mutex};
use wasm_bindgen::prelude::*;
use wgpu::util::DeviceExt;

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct Vertex {
    position: [f32; 3],
    color: [f32; 3],
}

#[derive(Default)]
struct Mesh {
    vertices: Vec<Vertex>,
}
impl Mesh {
    fn quad(&mut self, p: [[f32; 3]; 4], color: [f32; 3]) {
        for i in [0, 1, 2, 0, 2, 3] {
            self.vertices.push(Vertex {
                position: p[i],
                color,
            });
        }
    }
    fn box_mesh(
        &mut self,
        min: [f32; 3],
        max: [f32; 3],
        color: [f32; 3],
        transform: impl Fn([f32; 3]) -> [f32; 3],
    ) {
        let [x, y, z] = min;
        let [a, b, c] = max;
        for (face, shade) in [
            ([[x, y, c], [a, y, c], [a, b, c], [x, b, c]], 1.0),
            ([[x, y, z], [a, y, z], [a, y, c], [x, y, c]], 0.8),
            ([[x, b, z], [a, b, z], [a, b, c], [x, b, c]], 0.8),
            ([[x, y, z], [x, b, z], [x, b, c], [x, y, c]], 0.65),
            ([[a, y, z], [a, b, z], [a, b, c], [a, y, c]], 0.9),
        ] {
            self.quad(face.map(&transform), color.map(|v| v * shade));
        }
    }
}

#[cfg(any(target_arch = "wasm32", test))]
fn road_mesh(points: &[[f32; 3]], half: f32) -> Mesh {
    let mut mesh = Mesh::default();
    let normals: Vec<_> = (0..points.len())
        .map(|i| {
            let a = points[(i + points.len() - 1) % points.len()];
            let b = points[(i + 1) % points.len()];
            let length = (b[0] - a[0]).hypot(b[1] - a[1]);
            [-(b[1] - a[1]) / length, (b[0] - a[0]) / length]
        })
        .collect();
    for i in 0..points.len() {
        let j = (i + 1) % points.len();
        let edge = |idx: usize, d: f32, z: f32| {
            let p = points[idx];
            let n = normals[idx];
            [p[0] + d * n[0], p[1] + d * n[1], p[2] + z]
        };
        mesh.quad(
            [
                edge(i, -half, 0.),
                edge(j, -half, 0.),
                edge(j, half, 0.),
                edge(i, half, 0.),
            ],
            [0.20, 0.25, 0.29],
        );
        if points[i][2].min(points[j][2]) > 12. {
            mesh.quad(
                [
                    edge(i, -half - 3., -10.),
                    edge(j, -half - 3., -10.),
                    edge(j, half + 3., -10.),
                    edge(i, half + 3., -10.),
                ],
                [0.12, 0.16, 0.20],
            );
            for side in [-1., 1.] {
                mesh.quad(
                    [
                        edge(i, side * (half + 3.), -10.),
                        edge(j, side * (half + 3.), -10.),
                        edge(j, side * (half + 3.), 0.),
                        edge(i, side * (half + 3.), 0.),
                    ],
                    [0.35, 0.42, 0.46],
                );
            }
        }
        for side in [-1., 1.] {
            let wall = if i % 6 < 3 {
                [0.65, 0.71, 0.72]
            } else {
                [0.57, 0.64, 0.65]
            };
            mesh.quad(
                [
                    edge(i, side * (half + 1.), 0.),
                    edge(j, side * (half + 1.), 0.),
                    edge(j, side * (half + 1.), 26.),
                    edge(i, side * (half + 1.), 26.),
                ],
                wall,
            );
            mesh.quad(
                [
                    edge(i, side * (half + 1.), 26.),
                    edge(j, side * (half + 1.), 26.),
                    edge(j, side * (half + 3.), 26.),
                    edge(i, side * (half + 3.), 26.),
                ],
                [0.81, 0.86, 0.85],
            );
            // The outer face is needed when the bridge is viewed from outside.
            mesh.quad(
                [
                    edge(i, side * (half + 3.), 0.),
                    edge(j, side * (half + 3.), 0.),
                    edge(j, side * (half + 3.), 26.),
                    edge(i, side * (half + 3.), 26.),
                ],
                wall.map(|v| v * 0.75),
            );
            let curb = if i % 6 < 3 {
                [0.89, 0.91, 0.87]
            } else {
                [0.80, 0.42, 0.32]
            };
            mesh.quad(
                [
                    edge(i, side * (half - 1.), 0.08),
                    edge(j, side * (half - 1.), 0.08),
                    edge(j, side * half, 0.08),
                    edge(i, side * half, 0.08),
                ],
                curb,
            );
        }
        if i % 6 < 3 {
            mesh.quad(
                [
                    edge(i, -0.35, 0.1),
                    edge(j, -0.35, 0.1),
                    edge(j, 0.35, 0.1),
                    edge(i, 0.35, 0.1),
                ],
                [0.80, 0.82, 0.71],
            );
        }
    }
    mesh.quad(
        [
            [-20000., -20000., -12.],
            [20000., -20000., -12.],
            [20000., 20000., -12.],
            [-20000., 20000., -12.],
        ],
        [0.24, 0.38, 0.28],
    );
    mesh
}

#[cfg(any(target_arch = "wasm32", test))]
fn cockpit_mesh() -> Mesh {
    let mut m = Mesh::default();
    // Positions are normalized device coordinates; negative red tags HUD vertices.
    let color = [-1.10, 0.16, 0.20];
    m.quad(
        [
            [-1., -1., 0.],
            [1., -1., 0.],
            [1., -0.55, 0.],
            [-1., -0.55, 0.],
        ],
        color,
    );
    m.quad(
        [[-1., 1., 0.], [1., 1., 0.], [1., 0.92, 0.], [-1., 0.92, 0.]],
        color,
    );
    for side in [-1., 1.] {
        m.quad(
            [
                [side, 1., 0.],
                [side * 0.92, 1., 0.],
                [side * 0.73, -0.6, 0.],
                [side, -0.7, 0.],
            ],
            color,
        );
    }
    // Steering wheel ring, with physical aspect ratio compensated at the fixed canvas size.
    for i in 0..64 {
        let a = i as f32 * std::f32::consts::TAU / 64.;
        let b = (i + 1) as f32 * std::f32::consts::TAU / 64.;
        let point = |t: f32, r: f32| [-0.35 + r * t.cos(), -0.87 + r * 1200. / 650. * t.sin(), 0.];
        m.quad(
            [
                point(a, 0.17),
                point(b, 0.17),
                point(b, 0.14),
                point(a, 0.14),
            ],
            [-1.03, 0.05, 0.06],
        );
    }
    m
}

#[wasm_bindgen]
pub struct Renderer {
    surface: wgpu::Surface<'static>,
    device: wgpu::Device,
    queue: wgpu::Queue,
    config: wgpu::SurfaceConfiguration,
    pipeline: wgpu::RenderPipeline,
    hud_pipeline: wgpu::RenderPipeline,
    camera: wgpu::Buffer,
    bind_group: wgpu::BindGroup,
    depth: wgpu::TextureView,
    road: wgpu::Buffer,
    road_count: u32,
    cones: Option<wgpu::Buffer>,
    cone_count: u32,
    failure: Arc<Mutex<Option<String>>>,
    cars: wgpu::Buffer,
    hud: wgpu::Buffer,
    hud_count: u32,
}
fn error(e: impl std::fmt::Display) -> JsValue {
    JsValue::from_str(&e.to_string())
}
#[cfg(target_arch = "wasm32")]
fn vertex_buffer(device: &wgpu::Device, label: &str, mesh: &Mesh) -> wgpu::Buffer {
    device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some(label),
        contents: bytemuck::cast_slice(&mesh.vertices),
        usage: wgpu::BufferUsages::VERTEX,
    })
}
#[cfg(target_arch = "wasm32")]
fn depth_buffer(device: &wgpu::Device, w: u32, h: u32) -> wgpu::TextureView {
    device
        .create_texture(&wgpu::TextureDescriptor {
            label: Some("depth"),
            size: wgpu::Extent3d {
                width: w,
                height: h,
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: wgpu::TextureFormat::Depth24Plus,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            view_formats: &[],
        })
        .create_view(&Default::default())
}

#[wasm_bindgen]
impl Renderer {
    #[cfg(target_arch = "wasm32")]
    #[wasm_bindgen(js_name = create)]
    pub async fn create(
        canvas: web_sys::HtmlCanvasElement,
        coordinates: Vec<f32>,
        half_width: f32,
    ) -> Result<Renderer, JsValue> {
        console_error_panic_hook::set_once();
        if coordinates.len() < 9
            || coordinates.len() % 3 != 0
            || !half_width.is_finite()
            || half_width <= 0.
            || coordinates.iter().any(|v| !v.is_finite())
        {
            return Err(error("Invalid track geometry"));
        }
        let points: Vec<[f32; 3]> = coordinates
            .chunks_exact(3)
            .map(|p| [p[0], p[1], p[2]])
            .collect();
        for i in 0..points.len() {
            let a = points[i];
            let b = points[(i + 1) % points.len()];
            if (a[0] - b[0]).hypot(a[1] - b[1]) < 0.001 {
                return Err(error("Zero-length road segment"));
            }
        }
        let width = canvas.width().max(1);
        let height = canvas.height().max(1);
        let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
            backends: wgpu::Backends::BROWSER_WEBGPU,
            ..Default::default()
        });
        let surface = instance
            .create_surface(wgpu::SurfaceTarget::Canvas(canvas))
            .map_err(error)?;
        let adapter = instance
            .request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::HighPerformance,
                compatible_surface: Some(&surface),
                force_fallback_adapter: false,
            })
            .await
            .map_err(error)?;
        let (device, queue) = adapter
            .request_device(&wgpu::DeviceDescriptor {
                label: Some("car-renderer"),
                ..Default::default()
            })
            .await
            .map_err(error)?;
        let failure = Arc::new(Mutex::new(None));
        let lost = failure.clone();
        device.set_device_lost_callback(move |reason, message| {
            *lost.lock().unwrap() = Some(format!("GPU device lost: {reason:?}: {message}"));
        });
        let uncaptured = failure.clone();
        device.on_uncaptured_error(Box::new(move |e| {
            *uncaptured.lock().unwrap() = Some(format!("GPU error: {e}"));
        }));
        device.push_error_scope(wgpu::ErrorFilter::Validation);
        let config = surface
            .get_default_config(&adapter, width, height)
            .ok_or_else(|| error("No canvas format"))?;
        surface.configure(&device, &config);
        let camera = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("camera"),
            size: 48,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: None,
            entries: &[wgpu::BindGroupLayoutEntry {
                binding: 0,
                visibility: wgpu::ShaderStages::VERTEX | wgpu::ShaderStages::FRAGMENT,
                ty: wgpu::BindingType::Buffer {
                    ty: wgpu::BufferBindingType::Uniform,
                    has_dynamic_offset: false,
                    min_binding_size: None,
                },
                count: None,
            }],
        });
        let bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: None,
            layout: &layout,
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: camera.as_entire_binding(),
            }],
        });
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: None,
            bind_group_layouts: &[&layout],
            push_constant_ranges: &[],
        });
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("scene"),
            source: wgpu::ShaderSource::Wgsl(include_str!("scene.wgsl").into()),
        });
        let make_pipeline = |hud: bool| {
            device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some(if hud { "cockpit" } else { "scene" }),
                layout: Some(&pipeline_layout),
                vertex: wgpu::VertexState {
                    module: &shader,
                    entry_point: Some("vertex"),
                    compilation_options: Default::default(),
                    buffers: &[wgpu::VertexBufferLayout {
                        array_stride: 24,
                        step_mode: wgpu::VertexStepMode::Vertex,
                        attributes: &wgpu::vertex_attr_array![0=>Float32x3,1=>Float32x3],
                    }],
                },
                fragment: Some(wgpu::FragmentState {
                    module: &shader,
                    entry_point: Some("fragment"),
                    compilation_options: Default::default(),
                    targets: &[Some(wgpu::ColorTargetState {
                        format: config.format,
                        blend: None,
                        write_mask: wgpu::ColorWrites::ALL,
                    })],
                }),
                primitive: wgpu::PrimitiveState {
                    cull_mode: None,
                    ..Default::default()
                },
                depth_stencil: if hud {
                    None
                } else {
                    Some(wgpu::DepthStencilState {
                        format: wgpu::TextureFormat::Depth24Plus,
                        depth_write_enabled: true,
                        depth_compare: wgpu::CompareFunction::Less,
                        stencil: Default::default(),
                        bias: Default::default(),
                    })
                },
                multisample: Default::default(),
                multiview: None,
                cache: None,
            })
        };
        let pipeline = make_pipeline(false);
        let hud_pipeline = make_pipeline(true);
        let mesh = road_mesh(&points, half_width);
        let road_count = mesh.vertices.len() as u32;
        let road = vertex_buffer(&device, "static-road", &mesh);
        let hud_mesh = cockpit_mesh();
        let hud_count = hud_mesh.vertices.len() as u32;
        let hud = vertex_buffer(&device, "cockpit", &hud_mesh);
        let cars = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("cars"),
            size: 24 * 60 * 64,
            usage: wgpu::BufferUsages::VERTEX | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let depth = depth_buffer(&device, width, height);
        if let Some(e) = device.pop_error_scope().await {
            return Err(error(e));
        }
        Ok(Self {
            failure,
            surface,
            device,
            queue,
            config,
            pipeline,
            hud_pipeline,
            camera,
            bind_group,
            depth,
            road,
            road_count,
            cones: None,
            cone_count: 0,
            cars,
            hud,
            hud_count,
        })
    }

    /// Each car: x,y,z,heading,pitch,crashed,r,g,b. Inputs contain no learned state.
    pub fn set_cones(&mut self, cones: Vec<f32>) -> Result<(), JsValue> {
        if cones.len() % 4 != 0 || cones.len() > 40000 || cones.iter().any(|v| !v.is_finite()) {
            return Err(error("Invalid cones"));
        }
        let mut mesh = Mesh::default();
        for c in cones.chunks_exact(4) {
            if c[3] <= 0. {
                return Err(error("Invalid cone radius"));
            }
            for i in 0..12 {
                let a = i as f32 * std::f32::consts::TAU / 12.;
                let b = (i + 1) as f32 * std::f32::consts::TAU / 12.;
                let point = |angle: f32, h: f32| {
                    [
                        c[0] + c[3] * (1. - h / 16.) * angle.cos(),
                        c[1] + c[3] * (1. - h / 16.) * angle.sin(),
                        c[2] + h,
                    ]
                };
                for (lo, hi, color) in [
                    (0., 6., [1., 0.28, 0.04]),
                    (6., 10., [0.95, 0.95, 0.90]),
                    (10., 16., [1., 0.28, 0.04]),
                ] {
                    mesh.quad(
                        [point(a, lo), point(b, lo), point(b, hi), point(a, hi)],
                        color,
                    );
                }
            }
        }
        self.cone_count = mesh.vertices.len() as u32;
        self.cones = if self.cone_count > 0 {
            Some(
                self.device
                    .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                        label: Some("cones"),
                        contents: bytemuck::cast_slice(&mesh.vertices),
                        usage: wgpu::BufferUsages::VERTEX,
                    }),
            )
        } else {
            None
        };
        Ok(())
    }

    pub fn render(&mut self, cars: Vec<f32>, selected: usize, chase: bool) -> Result<(), JsValue> {
        if let Some(message) = self.failure.lock().unwrap().as_ref() {
            return Err(error(message));
        }
        if cars.len() % 9 != 0
            || cars.len() > 9 * 64
            || selected >= cars.len() / 9
            || cars.iter().any(|v| !v.is_finite())
        {
            return Err(error("Invalid car state"));
        }
        let selected_car = &cars[selected * 9..selected * 9 + 9];
        let [x, y, z, heading, pitch] = [
            selected_car[0],
            selected_car[1],
            selected_car[2],
            selected_car[3],
            selected_car[4],
        ];
        let (sin, cos) = heading.sin_cos();
        let (sp, cp) = (pitch + if chase { -0.18 } else { 0. }).sin_cos();
        let back = if chase { 100. } else { 0. };
        let lift = if chase { 55. } else { 9. };
        let uniform = [
            x - back * cos,
            y - back * sin,
            z + lift,
            0.,
            cos,
            sin,
            cp,
            sp,
            1400. / self.config.width as f32,
            1400. / self.config.height as f32,
            1. - 572. / self.config.height as f32,
            0.,
        ];
        self.queue
            .write_buffer(&self.camera, 0, bytemuck::cast_slice(&uniform));
        let mut mesh = Mesh::default();
        for (i, c) in cars.chunks_exact(9).enumerate() {
            if c[5] > 0.5 || (i == selected && !chase) {
                continue;
            }
            let (si, co) = c[3].sin_cos();
            let (ps, pc) = c[4].sin_cos();
            let transform = |p: [f32; 3]| {
                let along = p[0] * pc - p[2] * ps;
                [
                    c[0] + along * co - p[1] * si,
                    c[1] + along * si + p[1] * co,
                    c[2] + p[0] * ps + p[2] * pc,
                ]
            };
            mesh.box_mesh([-6., -4., 1.], [6., 4., 4.], [c[6], c[7], c[8]], transform);
            mesh.box_mesh(
                [-3., -3.4, 4.],
                [3., 3.4, 7.],
                [0.13, 0.22, 0.26],
                transform,
            );
        }
        if !mesh.vertices.is_empty() {
            self.queue
                .write_buffer(&self.cars, 0, bytemuck::cast_slice(&mesh.vertices));
        }
        let frame = match self.surface.get_current_texture() {
            Ok(frame) => frame,
            Err(wgpu::SurfaceError::Lost | wgpu::SurfaceError::Outdated) => {
                self.surface.configure(&self.device, &self.config);
                return Ok(());
            }
            Err(wgpu::SurfaceError::Timeout) => return Ok(()),
            Err(e) => return Err(error(e)),
        };
        let view = frame.texture.create_view(&Default::default());
        let mut encoder = self.device.create_command_encoder(&Default::default());
        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("3D"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    depth_slice: None,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color {
                            r: 0.40,
                            g: 0.59,
                            b: 0.69,
                            a: 1.,
                        }),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: &self.depth,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.),
                        store: wgpu::StoreOp::Discard,
                    }),
                    stencil_ops: None,
                }),
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            pass.set_pipeline(&self.pipeline);
            pass.set_bind_group(0, &self.bind_group, &[]);
            pass.set_vertex_buffer(0, self.road.slice(..));
            pass.draw(0..self.road_count, 0..1);
            if let Some(cones) = &self.cones {
                pass.set_vertex_buffer(0, cones.slice(..));
                pass.draw(0..self.cone_count, 0..1);
            }
            if !mesh.vertices.is_empty() {
                pass.set_vertex_buffer(0, self.cars.slice(..));
                pass.draw(0..mesh.vertices.len() as u32, 0..1);
            }
        }
        if !chase {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("HUD"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    depth_slice: None,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Load,
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            pass.set_pipeline(&self.hud_pipeline);
            pass.set_bind_group(0, &self.bind_group, &[]);
            pass.set_vertex_buffer(0, self.hud.slice(..));
            pass.draw(0..self.hud_count, 0..1);
        }
        self.queue.submit(Some(encoder.finish()));
        frame.present();
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn road_mesh_contains_elevated_deck_and_underside() {
        let points = [
            [0., 0., 160.],
            [100., 0., 160.],
            [100., 100., 0.],
            [0., 100., 0.],
        ];
        let mesh = road_mesh(&points, 38.);
        assert!(mesh.vertices.iter().any(|v| v.position[2] == 150.));
        assert!(mesh.vertices.iter().any(|v| v.position[2] == 186.));
        assert!(mesh
            .vertices
            .iter()
            .all(|v| v.position.iter().all(|n| n.is_finite())));
    }
    #[test]
    fn shader_parses_and_validates() {
        let module = naga::front::wgsl::parse_str(include_str!("scene.wgsl")).unwrap();
        naga::valid::Validator::new(
            naga::valid::ValidationFlags::all(),
            naga::valid::Capabilities::all(),
        )
        .validate(&module)
        .unwrap();
    }
    #[test]
    fn cockpit_vertices_are_screen_space() {
        let mesh = cockpit_mesh();
        assert!(!mesh.vertices.is_empty());
        assert!(mesh
            .vertices
            .iter()
            .all(|v| v.color[0] < 0. && v.position[2] == 0.));
    }
    #[test]
    fn car_buffers_fit_maximum_traffic() {
        let mut mesh = Mesh::default();
        for _ in 0..64 {
            for _ in 0..2 {
                mesh.box_mesh([-1.; 3], [1.; 3], [1.; 3], |p| p);
            }
        }
        assert_eq!(mesh.vertices.len(), 64 * 60);
    }
}
