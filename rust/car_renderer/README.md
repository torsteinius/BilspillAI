# Rust/WebGPU-renderer for bilspillet

Rendereren kjører som WebAssembly i nettleseren. Rust bygger geometrien og sender tegnekommandoer gjennom `wgpu`; GPU-en utfører kameratransformasjon, perspektiv, klipping, dybdetest og rasterisering. Ingen bildeoverføring fra Python-serveren er nødvendig.

Bane, vegger, brodekke og bakken lastes til en statisk vertexbuffer én gang. Bilgeometrien og kameraet oppdateres ved nye tilstandsbilder eller kameravalg. Første versjon bruker fortsatt visningens eksisterende oppdateringsfrekvens (HTTP-polling med 70 ms ventetid); den innfører ikke interpolering eller lover en bestemt bildefrekvens. Simulering, sensorer, modell og trening er uendret av rendererbyttet.

`games/car/renderer/bridge.js` laster modulen og sender tilstand fra grensesnittet. `car_renderer.js` og `car_renderer_bg.wasm` er genererte filer som følger repoet, slik at vanlig oppstart ikke krever Rust. Statusfeltet viser om GPU er aktiv eller den gamle Canvas-visningen brukes som reserve. Reservevisningen tar over ved manglende WebGPU, oppstartsfeil eller registrert GPU-feil. Oversiktskartet og videoopptaket av kartet bruker fortsatt SVG/Canvas.

## Bygg

Fra prosjektroten, med Rust og Cargo tilgjengelig:

```sh
rustup target add wasm32-unknown-unknown
cargo install wasm-bindgen-cli --version 0.2.105 --locked
./scripts/build_car_renderer.sh
```

Versjonen av `wasm-bindgen-cli` må samsvare med den låste bibliotekversjonen. `Cargo.lock` lagres i Git. Endre Rust/WGSL-kilden, bygg på nytt og last nettsiden på nytt. Ikke rediger de genererte filene manuelt.

```sh
cargo test --locked --manifest-path rust/car_renderer/Cargo.toml
python3 -m unittest discover -s v2 -p 'test_*.py' -v
python3 -m games.car.app --track figure_eight --traffic convoy --replay
```

Åpne <http://127.0.0.1:8766/> i en nettleser med WebGPU. Lokalhost er egnet; WebGPU krever en sikker nettleserkontekst. `/renderer/gpu-check.html` gir statiske kontrollbilder under broen, på broen og i rampen på `figure_eight`. Disse bildene bruker samme Rust-renderer, men er ikke opptak fra simuleringen.

## Grensesnitt

- `Renderer.create(canvas, xyz, half_width)`: lukket senterlinje som flat `Float32Array` med xyz-tripler, pluss halve veibredden.
- `render(cars, selected, chase)`: flat `Float32Array`, ni verdier per bil: x, y, z, heading, pitch, crashed (0/1), r, g, b. Farge er kun visualisering og går ikke til modellen.
- Rendererens canvas er 1200 × 650, skalert av CSS og fullskjermvisning. GPU-dybdebufferen har samme oppløsning. Dynamisk oppløsning og kantutjevning er ikke lagt til.
- Førermiljøet er en enkel GPU-tegnet ramme, dashbord og ratt. Rattet i GPU-versjonen er foreløpig statisk; høyde, stigning og bilvalg vises i HTML-grensesnittet.
