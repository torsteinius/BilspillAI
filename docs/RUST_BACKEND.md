# Rust på CPU

Rust kan nå brukes til nettverksberegning og evolusjon i den lokale bil- og labyrinttreningen. Simulering, poengberegning, rangering, brukergrensesnitt og lagring styres fortsatt av Python. Rust-utvidelsen kalles direkte i samme prosess, uten HTTP eller en separat server.

## Installasjon

Installer Rust med verktøyene fra https://rustup.rs hvis Cargo ikke finnes. Last inn Cargo i det aktuelle skallet, og bygg utvidelsen i Python-miljøet som skal kjøre spillet:

```sh
. "$HOME/.cargo/env"
.venv-gpu/bin/python -m pip install ./rust/ai_native
```

Navnet `.venv-gpu` er bare navnet på det eksisterende miljøet: Rust-backenden bruker CPU og trenger ikke MLX. Alternativt opprett et eget miljø med Python 3.10 eller nyere:

```sh
python3 -m venv .venv-rust
.venv-rust/bin/python -m pip install ./rust/ai_native
```

Byggingen bruker [PyO3](https://pyo3.rs/) og [Maturin](https://www.maturin.rs/tutorial). Pip bygger en optimalisert release-utvidelse. Kjør installasjonen igjen etter endringer i Rust-koden. `Cargo.lock` låser Rust-avhengighetene. På en annen maskin, inkludert Studio, må utvidelsen installeres der også.

## Bruk

```sh
# Nytt bilforsøk; velg et ubrukt modellnavn.
.venv-gpu/bin/python -m games.car.app --backend rust --seed 42 --model games/car/models/rust_trial_42.json

# Nytt labyrintforsøk uten webserver; velg et ubrukt modellnavn.
.venv-gpu/bin/python -m games.maze.app --backend rust --headless --generations 20 --model games/maze/models/rust_trial_42.json

# Fortsett det samme labyrintforsøket.
.venv-gpu/bin/python -m games.maze.app --backend rust --headless --resume --generations 20 --model games/maze/models/rust_trial_42.json
```

Velg `--backend rust` også ved avspilling og videre trening. Standard er fortsatt `python`, slik at eksisterende kommandoer og installasjoner fungerer. Et eksplisitt Rust-valg gir en tydelig feil hvis utvidelsen mangler; det byttes ikke stille til Python. Studio-API-et og eksisterende MLX-trening er ikke endret av dette arbeidet.

Fra Python:

```python
from ai.network import NeuralNetwork

network = NeuralNetwork([9, 8, 8, 1], seed=42).set_backend('rust')
output = network.forward([0.] * 9)
outputs = network.forward_batch([[0.] * 9, [.1] * 9])
# network.train(evaluate, ...) bruker nå også Rust til initialisering og mutasjon.
```

`forward_batch` beregner flere observasjoner med samme vekter i ett kall. Den ordinære spilløkken bruker fortsatt enkeltkall. Vektene overføres fra Python ved hvert kall; dette sikrer at både direkte endringer i vektlisten og alternative kandidatvekter brukes umiddelbart, uten en cache som kan bli utdatert. Batch-kall overfører vektene én gang. Beregningene bruker f64 og støtter eksisterende tanh-nettverk, normaliserte skjulte lag og det forgrenede historikknettet. Forgrenede nett bruker ett Rust-kall per gren.

## Læring og kompatibilitet

Utvalg av eliter, mutasjonsstyrke, belønning og trenings-callbacks følger samme opplegg som før. Rust håndterer tilfeldig initialisering, valg av forelder og normalfordelte vektmutasjoner. Elitene beholdes uendret. Den native `EvolutionRng.mutate` støtter også en boolsk maske for fryste vekter; den lokale `NeuralNetwork.train` har samme mutasjonsregler som tidligere og innfører ingen ny maske-policy.

Rust bruker ChaCha8 og rand_distr til tilfeldige tall. Samme seed og samme treningsopplegg er repeterbart innen denne backenden, men gir andre kandidater enn Python sin `random.Random`. Treningshistorikken merker Rust-generasjoner med backend og RNG-variant. Som før opprettes en ny populasjon ved resume; dette er ikke en eksakt fortsettelse av den gamle generator- og populasjonstilstanden.

JSON-modellformatet er beholdt. En modell trent i Python kan kjøres og trenes videre i Rust og omvendt. Regnemotor velges ved oppstart, ikke fra modellfilen. Nettverksutvidelse under labyrinttrening beholder Rust-valget. Små flyttallsavvik mellom motorene kan forekomme og kan påvirke valg svært nær en beslutningsgrense.

## Kontroll og målinger

```sh
.venv-gpu/bin/python -m unittest discover -s tests -v
.venv-gpu/bin/python -m scripts.benchmark_rust
cargo clippy --manifest-path rust/ai_native/Cargo.toml -- -D warnings
```

Benchmarken endrer ingen modellfiler. Den måler medianen av sju repetisjoner etter oppvarming, med 100 observasjoner per nettverk. Mutasjonstesten beholder seks eliter og fyller opp til 36 kandidater. Alle Python–Rust-konverteringer inngår; dette er ikke en måling av komplett spilltrening eller en sammenligning med optimalisert CPU-matrisekode/GPU.

Første lokale måling 5. november 2026 (Apple Silicon, Python 3.12, release-bygg):

| Nettverk | Enkeltkall, raskere enn Python | 100 observasjoner samlet | Generering av ny populasjon |
| --- | ---: | ---: | ---: |
| 9–8–8–1 | 6,3× | 25,7× | 9,4× |
| 88–32–16–4 | 6,8× | 54,2× | 9,4× |
| 296–223–150–77–4 | 6,8× | 57,6× | 8,4× |

Største absolutte avvik i nettverksutdata i målingen var under 9 × 10⁻¹⁵. Tallene er veiledende og varierer med maskin og belastning. GPU-valg for større arbeidsmengder bør senere vurderes med målinger av hele treningsløpet.
