// UI/data bridge only. Mesh generation, GPU commands and shaders live in Rust.
import init, { Renderer } from './car_renderer.js';
let renderer=null, failed=false;
const status=document.getElementById('rendererStatus');
const gpuCanvas=document.getElementById('gpuCanvas');
const cpuCanvas=document.getElementById('cockpit');
const colors=[[.447,.894,.690],[.435,.725,1],[.953,.788,.412],[.902,.608,1],[1,.525,.373]];
function fallback(error){
 failed=true; renderer=null; gpuCanvas.hidden=true; cpuCanvas.hidden=false;
 status.textContent='Canvas-reservevisning · '+String(error);
 console.error('Rust/WebGPU renderer:',error);
}
window.carGpu={
 ready:false,
 async initialize(track){
  try{
   if(!navigator.gpu)throw Error('WebGPU er ikke tilgjengelig');
   await init();
   renderer=await Renderer.create(gpuCanvas,new Float32Array(track.points.flat()),track.width/2);
   renderer.set_cones(new Float32Array((track.cones||[]).flatMap(c=>[c.x,c.y,c.z,c.radius])));
   this.ready=true;gpuCanvas.hidden=false;cpuCanvas.hidden=true;
   status.textContent='Rust + WebGPU · GPU-rendering aktiv';
   window.dispatchEvent(new Event('car-gpu-ready'));
  }catch(error){this.ready=false;fallback(error);}
 },
 render(state,selected,chase){
  if(!renderer||failed)return false;
  try{
   const packed=new Float32Array(state.cars.flatMap((c,i)=>[c.x,c.y,c.z||0,c.heading,c.pitch||0,c.crashed?1:0,...colors[i%colors.length]]));
   renderer.render(packed,selected,chase);
   return true;
  }catch(error){this.ready=false;fallback(error);return false;}
 }
};
window.dispatchEvent(new Event('car-gpu-module'));
