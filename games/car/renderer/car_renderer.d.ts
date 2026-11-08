/* tslint:disable */
/* eslint-disable */
export class Renderer {
  private constructor();
  free(): void;
  [Symbol.dispose](): void;
  static create(canvas: HTMLCanvasElement, coordinates: Float32Array, half_width: number, closed?: boolean | null): Promise<Renderer>;
  render(cars: Float32Array, selected: number, chase: boolean): void;
  /**
   * Each car: x,y,z,heading,pitch,crashed,r,g,b. Inputs contain no learned state.
   */
  set_cones(cones: Float32Array): void;
}

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
  readonly memory: WebAssembly.Memory;
  readonly __wbg_renderer_free: (a: number, b: number) => void;
  readonly renderer_create: (a: any, b: number, c: number, d: number, e: number) => any;
  readonly renderer_render: (a: number, b: number, c: number, d: number, e: number) => [number, number];
  readonly renderer_set_cones: (a: number, b: number, c: number) => [number, number];
  readonly wasm_bindgen_f0cd39f1508ddffc___convert__closures_____invoke___wasm_bindgen_f0cd39f1508ddffc___JsValue_____: (a: number, b: number, c: any) => void;
  readonly wasm_bindgen_f0cd39f1508ddffc___closure__destroy___dyn_core_37ee0ce0c4cd57d5___ops__function__FnMut__wasm_bindgen_f0cd39f1508ddffc___JsValue____Output_______: (a: number, b: number) => void;
  readonly wasm_bindgen_f0cd39f1508ddffc___convert__closures_____invoke___wgpu_88218f2ca1cfdcda___backend__webgpu__webgpu_sys__gen_GpuUncapturedErrorEvent__GpuUncapturedErrorEvent_____: (a: number, b: number, c: any) => void;
  readonly wasm_bindgen_f0cd39f1508ddffc___closure__destroy___dyn_core_37ee0ce0c4cd57d5___ops__function__FnMut__wgpu_88218f2ca1cfdcda___backend__webgpu__webgpu_sys__gen_GpuUncapturedErrorEvent__GpuUncapturedErrorEvent____Output_______: (a: number, b: number) => void;
  readonly wasm_bindgen_f0cd39f1508ddffc___convert__closures_____invoke___wasm_bindgen_f0cd39f1508ddffc___JsValue__wasm_bindgen_f0cd39f1508ddffc___JsValue_____: (a: number, b: number, c: any, d: any) => void;
  readonly __wbindgen_malloc: (a: number, b: number) => number;
  readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
  readonly __wbindgen_exn_store: (a: number) => void;
  readonly __externref_table_alloc: () => number;
  readonly __wbindgen_externrefs: WebAssembly.Table;
  readonly __wbindgen_free: (a: number, b: number, c: number) => void;
  readonly __externref_table_dealloc: (a: number) => void;
  readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;
/**
* Instantiates the given `module`, which can either be bytes or
* a precompiled `WebAssembly.Module`.
*
* @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
*
* @returns {InitOutput}
*/
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
* If `module_or_path` is {RequestInfo} or {URL}, makes a request and
* for everything else, calls `WebAssembly.instantiate` directly.
*
* @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
*
* @returns {Promise<InitOutput>}
*/
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
