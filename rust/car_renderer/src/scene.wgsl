struct Camera {
    position: vec4<f32>,
    rotation: vec4<f32>, // cos(heading), sin(heading), cos(pitch), sin(pitch)
    projection: vec4<f32>, // horizontal scale, vertical scale, horizon offset, unused
};
@group(0) @binding(0) var<uniform> camera: Camera;
struct VertexOut {
    @builtin(position) position: vec4<f32>,
    @location(0) color: vec3<f32>,
    @location(1) world_position: vec3<f32>,
};
@vertex fn vertex(@location(0) p: vec3<f32>, @location(1) color: vec3<f32>) -> VertexOut {
    var out: VertexOut;
    // Negative red marks screen-space cockpit geometry, drawn in a separate pass.
    if (color.r < 0.0) {
        out.position = vec4<f32>(p, 1.0);
        out.color = vec3<f32>(-color.r - 1.0, color.g, color.b);
        out.world_position = camera.position.xyz;
        return out;
    }
    let d = p - camera.position.xyz;
    let r = camera.rotation;
    let right = -r.y*d.x + r.x*d.y;
    let forward = r.x*d.x + r.y*d.y;
    let up = d.z*r.z - forward*r.w;
    let depth = forward*r.z + d.z*r.w;
    // WebGPU clips depth into [0,w]; near=1, far=12000 world units.
    out.position = vec4<f32>(right*camera.projection.x,
        up*camera.projection.y + depth*camera.projection.z,
        depth*(12000.0/11999.0) - 12000.0/11999.0, depth);
    out.color = color;
    out.world_position = p;
    return out;
}
@fragment fn fragment(in: VertexOut) -> @location(0) vec4<f32> {
    let fog = smoothstep(2800.0, 11000.0, length(in.world_position - camera.position.xyz));
    return vec4<f32>(mix(in.color, vec3<f32>(0.56,0.70,0.76),fog), 1.0);
}
