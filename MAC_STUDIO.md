# Flytt til Mac Studio (Apple Silicon)

Repoet inkluderer kode, lagrede modellvekter, modellens konfigurasjon og tilgjengelige treningsrapporter/historikk for alle forsøk. Virtuelle miljøer og cache følger ikke med. Modellene ligger direkte i Git; Git LFS er ikke nødvendig for dagens filstørrelser.

## Installer og start

Installer Python 3.12 hvis den ikke finnes (for eksempel `brew install python@3.12` med Homebrew). Klon det private repoet med en GitHub-konto som har tilgang:

```sh
git clone https://github.com/torsteinius/BilspillAI.git
cd BilspillAI
python3.12 -m venv .venv-gpu
.venv-gpu/bin/python -m pip install -r requirements-gpu.txt
```

Vis siste lagrede modell uten å starte ny trening:

```sh
.venv-gpu/bin/python -m games.maze.app --replay --model games/maze/models/deterministic_history_v1.json --backend mlx-gpu --port 8774
```

Åpne http://127.0.0.1:8774/ på Mac Studio. Stopp serveren med Ctrl+C før du starter en ny på samme port.

Fortsett fra lagrede vekter med 2000 **ekstra** generasjoner:

```sh
.venv-gpu/bin/python -m games.maze.app --resume --model games/maze/models/deterministic_history_v1.json --generations 2000 --backend mlx-gpu --port 8774
```

Lagrede regler brukes automatisk, inkludert minst 20 handlinger før veggtreff eller gjentatt tilstand avslutter et forsøk. Utgangen kan avslutte tidligere. MLX kjører nettverksberegningene på Apple GPU; simulering og deler av treningen bruker CPU.

## Modellene

- `games/car/models/`: bilspillets modeller og sikkerhetskopier.
- `games/maze/models/`: labyrintmodeller, tidligere forsøk og sikkerhetskopier.
- Undermappene i `games/maze/models/` inneholder også MLX-vekter (`.safetensors`) og rapporter for kryssdetektor, LSTM og stedshukommelse.
- `games/maze/history_detector.json`: den fryste kryssdetektoren brukt av dagens modell.

Et checkpoint er ikke en kopi av en kjørende Python-prosess. Evolusjonstreningen fortsetter fra lagrede vekter og progresjon, med en ny populasjon. MLX-eksperimentene lagrer vekter, men ikke nødvendigvis optimizer-tilstand. Se dokumentasjonen for hvert eksperiment for egne startkommandoer.

## Flytt nyere treningsresultater

Git lagrer bare vektene ved hver commit; nye treningsresultater sendes ikke automatisk. Før selve overflyttingen bør treningen på den gamle maskinen stoppes etter ønsket checkpoint. Send deretter de nye resultatene:

```sh
git add games/car/models games/maze/models games/maze/history_detector.json
git commit -m "Save latest training checkpoints"
git push
```

På Mac Studio, før lokal trening startes:

```sh
git pull --ff-only
```

Unngå å trene til samme modellfil på begge maskiner samtidig. Bruk ulike modellnavn eller grener til parallelle forsøk; vektfiler kan ikke meningsfullt flettes automatisk.

## Tester

```sh
.venv-gpu/bin/python -m unittest discover -s tests -v
.venv-gpu/bin/python -m unittest discover -s v2 -p 'test_*.py' -v
```
