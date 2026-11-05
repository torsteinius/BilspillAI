#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PATH="$HOME/.cargo/bin:$PATH"
# wasm-bindgen CLI must match the crate version pinned in Cargo.toml.
if ! wasm-bindgen --version | grep -q '0.2.105'; then
    echo 'Install matching tool: cargo install wasm-bindgen-cli --version 0.2.105 --locked' >&2
    exit 1
fi
cargo build --locked --manifest-path rust/car_renderer/Cargo.toml --target wasm32-unknown-unknown --release
wasm-bindgen rust/car_renderer/target/wasm32-unknown-unknown/release/car_renderer.wasm \
    --target web --no-typescript --out-dir games/car/renderer --out-name car_renderer
