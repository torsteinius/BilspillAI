# AI-spill

Et felles prosjekt for spill som lærer med nevrale nettverk. Bilspillet og labyrintspillet har hver sin motor og visning. Hvert nytt spill får sin egen mappe, egne spilleregler, observasjoner, poengberegning, visning og modellfiler.

## Flytt til Mac Studio

Se [installasjon, GPU-oppstart og videre trening](MAC_STUDIO.md). Alle lagrede modeller og treningsrapporter følger repoet; lokale Python-miljøer og cache ignoreres.

## Struktur

- `ai/network.py`: den felles klassen `NeuralNetwork`. Velger lagstørrelser, beregner nettverkets utdata, trener med utvalg og mutasjon, utvider innganger og lagrer/laster modeller.
- `games/car/`: bilspillet med Python-simulering, bane, webvisning og treningens kobling til spillets poengberegning.
- `games/maze/`: tilfeldig labyrintmotor, mann med trådfølere, komprimert hukommelse og automatisk 50 % størrelsesøkning.
- `games/car/models/`: eksisterende modeller og sikkerhetskopier, flyttet uten endring av innholdet.
- `tests/`: tester av den felles nettverksklassen; `v2/test_*.py`: eksisterende regresjonstester for bilspillet.
- `versions/v1/`: historisk, selvstendig V1-demo. Arkivet beholdes uendret og brukes ikke som grunnlag for nye spill.
- `v2/demo.py` og `v2/advance.py`: kompatible startkommandoer som videresender til bilspillet.

Nettverksklassen kjenner ingen spilleregler. Spillet normaliserer sine egne observasjoner og gir klassen en funksjon `evaluate(weights)` som returnerer poeng. Høyere poeng er bedre. Nettverket kan ha vilkårlig antall og størrelse på skjulte lag samt flere utganger. Bilspillet bruker ni innganger og én utgang.

## Kjør bilspillet

```sh
python3 -m games.car.app
# eller: python3 demo.py
```

Åpne http://127.0.0.1:8766/. Vanlig oppstart starter ny trening. Vis en eksisterende modell med:

```sh
python3 -m games.car.app --replay
```

Standardnettverket er 9 → 8 → 8 → 1. Velg en annen størrelse og en egen fil for et forsøk:

```sh
python3 -m games.car.app --hidden 16 8 --seed 42 --model games/car/models/experiment_42.json
python3 -m games.car.app --hidden 16 8 --model games/car/models/experiment_42.json --fast-generations 20
python3 -m games.car.app --hidden 16 8 --model games/car/models/experiment_42.json --replay
```

Uten `--model` brukes en fil med lagstørrelsene i navnet. Bruk unike modellnavn for forsøk som skal sammenlignes; ny trening på samme fil erstatter det tidligere forsøket. `--hidden` uten tall gir et nettverk uten skjulte lag. Ved avspilling og videre trening må lagstørrelsene stemme med filen.

Videre trening uten server eller animasjon leser størrelsen fra modellfilen og tar sikkerhetskopi før trening:

```sh
python3 -m games.car.advance 100 --model games/car/models/experiment_42.json
```

Modellfiler inneholder lagstørrelser, vekter, generasjon, poeng, seed, spillinnstillinger og historikk for fullførte generasjoner med mutasjonsstyrke og populasjonsstørrelse. Eldre modellfiler kan leses; de mangler historikk fra før omleggingen. Hver generasjon lagres atomisk. Videre trening starter en ny populasjon rundt den lagrede vinneren og måler denne på nytt; den gjenoppretter ikke nøyaktig samme optimizer-tilstand som et uavbrutt løp. Seed gir repeterbare nye forsøk når evalueringen og innstillingene er identiske.

## Kjør labyrintspillet

```sh
python3 -m games.maze.app
```

Åpne http://127.0.0.1:8767/. Start i et åpent 30 × 30-landskap med 50 grå bokser først, fra midten til kanten. Etter 20 feilfrie forsøk på rad går modellen videre til tilfeldige 5 × 5-labyrinter. 20 nye labyrinter løst feilfritt på rad gir 50 % økning i begge dimensjoner: 5 → 8 → 12 → 18. Nettet får sju følere og de siste 50 handlingene, komprimert som handling/antall. 50 skritt frem bruker dermed to aktive minneinnganger. Spillene deler bare `NeuralNetwork`.

Se [full dokumentasjon for labyrintspillet](games/maze/README.md) for regler, inputformat, motor, treningsprogresjon og alle innstillinger.

## Gjenbruk i neste spill

```python
from ai.network import NeuralNetwork

network = NeuralNetwork([4, 12, 2], seed=42)
actions = network.forward([0.1, 0.2, 0.3, 0.4])
# evaluate tilhører det nye spillet og returnerer ett poengtall.
network.train(evaluate, 100, checkpoint="games/my_game/models/run_42.json")
network = NeuralNetwork.load("games/my_game/models/run_42.json")
```

Opprett `games/<spillnavn>/`, og importer bare `ai.network` for nettverk og trening. Spillene skal ikke importere hverandre. Hold modeller og evalueringsoppsett i spillets mappe. Sensorer, belønning, fysikk og presentasjon hører til spillet; lag, vekter, mutasjoner, læring og modellformat hører til `NeuralNetwork`.

## Tester

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s v2 -p 'test_*.py' -v
```

Detaljer og tidligere designnotater for bilspillet finnes i [games/car/README.md](games/car/README.md). Den historiske V1-demoen kjøres med `python3 versions/v1/demo.py` på port 8765.
