# Oppdrag til ChatGPT på Mac Studio

## Målet

Bygg en lokal AI-tjeneste på denne Mac Studio-maskinen som appene mine på Mac Mini eller en annen Mac kan bruke. Tjenesten skal registrere nevrale nettverk med type, arkitektur, app-ID og nettverks-ID, trene dem på Studio og lagre vekter og treningsstatus. Appene skal kunne bestille trening, følge fremgangen og hente resultater gjennom et API.

Start med det eksisterende labyrintspillet i BilspillAI. Bevar nettverket som allerede er trent. Første mål er en fungerende vertikal løsning for én modell, ikke et generelt rammeverk for alle tenkelige modeller.

Dette dokumentet er overlevering fra den andre maskinen. API-et nedenfor er et implementeringsforslag; det finnes ikke i prosjektet ennå. Undersøk filene før du endrer dem, og arbeid videre fra faktisk kode og checkpoint.

## Prosjekt og overføring

Prosjektet på kildemaskinen ligger i:

`/Users/torsteinlunde/Documents/GitHub/BilspillAI`

Hele mappen er flyttet fra Documents/ChatGPT til Documents/GitHub. Den inneholder et lokalt Git-repo, kode, dokumentasjon, modellvekter og et lokalt Python-miljø. Det er ikke opprettet noen GitHub-remote eller lastet opp noe repo. Navnet GitHub viser her til en lokal mappe. Ikke anta at en tidligere foreslått GitHub-URL finnes.

Finn den overførte prosjektmappen på Studio. Dersom den mangler, be brukeren overføre den eller oppgi kildemaskinens tilkoblingsinformasjon. Dette dokumentet alene inneholder ikke kode eller vekter. Kopier alle modellfiler, inkludert JSON, safetensors, rapporter og sikkerhetskopier. Ikke kopier et aktivt virtuelt miljø som grunnlag for kjøring på Studio; opprett et nytt.

Den andre maskinen kan fortsatt trene. Et overført checkpoint er et øyeblikksbilde. Avklar overtakelsen før begge maskiner begynner å skrive til samme modell. Ikke stopp andre maskiners prosesser uten at dette inngår i avtalt overtakelse.

## Dagens kode

| Fil eller mappe | Ansvar |
| --- | --- |
| `ai/network.py` | Generelt tett tanh-nett, vekter, evolusjonstrening, JSON-lagring |
| `ai/mlx_backend.py` | Batchet nettverksberegning på Apple GPU med MLX |
| `games/maze/training.py` | Treningssett, evaluering, progresjon, checkpoints og opptak |
| `games/maze/app.py` | Lokal HTTP-server og kommandolinje for trening og avspilling |
| `games/maze/history.py` | Deterministisk historikk og nettverk som vokser med labyrinten |
| `games/maze/memory.py` | Bevegelse, belønning og avslutning av forsøk |
| `games/maze/world.py` | Labyrint, sensorer og regler |
| `games/maze/history.html` | Visning for dagens labyrintmodell |
| `games/maze/models/` | Labyrintmodeller og tidligere eksperimenter |
| `games/car/` | Bilspill med egen simulering og trening |
| `tests/` | Tester for nettverk og labyrintforsøk |
| `requirements-gpu.txt` | MLX-avhengighet, nå låst til 0.32.4 |

`NeuralNetwork.train` bruker utvalg og mutasjon. Dagens labyrintmodell trenes ikke med backpropagation. `Trainer.evaluate_batch` simulerer mange kandidater og labyrinter og bruker `BatchedNetwork.forward` på GPU for hvert simuleringstidssteg. Simuleringen og deler av treningen kjører på CPU. Mer GPU-kraft gir derfor ikke automatisk tilsvarende økning i total hastighet.

## Den første modellen som skal støttes

Checkpoint:

`games/maze/models/deterministic_history_v1.json`

Avhengig, fryst kryssdetektor:

`games/maze/history_detector.json`

Foreslått app-ID: `maze`

Foreslått nettverks-ID: `maze-history-v1`

Ved kontroll 17. oktober 2026 var checkpointet på generasjon 1810, med 8 × 8-labyrint og arkitektur `296 → 223 → 150 → 77 → 4`. Treningen fortsetter, så importer verdiene fra den faktiske filen. Les toppnivåets `architecture` og lagret `curriculum`; ikke utled aktuell arkitektur fra `config.hidden` eller startstørrelsen i config.

Observasjonsversjon: `rays8_complete_landmark_history_v1`.

Input består av åtte aktuelle sensormålinger først, etterfulgt av åtte målinger for hvert tidligere registrerte sted. Ubrukte plasser fylles med null. Målingene normaliseres med labyrintens sensorrekkevidde. Nettet får ikke kart eller målkoordinater.

En fryst detektor avgjør om et sted skal registreres. Historikken lagrer hver fysisk posisjon én gang og bruker koordinater internt til deduplisering. Koordinatene sendes ikke til beslutningsnettet. Målingene lagres i retningen botten hadde ved første registrering. Dette er deterministisk historikk, ikke LSTM.

De fire outputverdiene velges med argmax og betyr, i rekkefølge: frem, tilbake, høyre, venstre. Det finnes ingen stå-stille-handling. En vegg kan likevel hindre faktisk forflytning.

Gjeldende regler inkluderer minst 20 handlinger før veggkontakt eller eksakt gjentatt tilstand kan avslutte forsøket. Utgang avslutter umiddelbart som vellykket. Etter 20 handlinger fortsetter botten frem til feil eller utgang; 20 er ikke en maksimumsgrense. Minimumet teller handlingsforsøk, også ved veggkontakt. Behold belønningene og progresjonen i checkpointet.

## Arkitektur for tjenesten

Kjør både treningsmotoren og labyrintsimuleringen på Studio. Appen på den andre maskinen sender et treningsoppdrag og henter status og opptak. Unngå en nettverksforespørsel for hvert labyrintsteg i treningen.

Skill mellom:

- `app_id`: app eller domene, eksempelvis maze eller car.
- `network_id`: stabil identitet for modellen som videreutvikles.
- `run_id`: én treningskjøring med eksplisitt startcheckpoint og innstillinger.
- `checkpoint_id`: en bestemt, uforanderlig versjon av vekter og metadata.

La AI-biblioteket eie modellformat, beregningsbackend og generelle treningsmetoder. La spilladapteren eie observasjoner, handlinger, belønning, simulering og progresjon. Bruk eksisterende kode fremfor å skrive om motoren.

En mulig struktur er `ai_service/` for API, register og jobbstyring, og `ai_service/adapters/maze.py` for koblingen til dagens Trainer. Bruk en enkel persistent registerløsning, for eksempel SQLite og modellfiler på disk. Hold dette utenfor spillenes visningskode.

Start med én aktiv GPU-treningsjobb. Kø eller avvis neste jobb tydelig. Kjør trening i en separat prosess slik at API-et forblir tilgjengelig hvis treningen feiler.

## Foreslått API

| Operasjon | Betydning |
| --- | --- |
| `POST /networks` | Registrer modell og importer checkpoint med nødvendige avhengigheter |
| `GET /networks` | List modeller og gjeldende versjoner |
| `POST /training-runs` | Start eller kølegg et treningsoppdrag |
| `GET /training-runs/{run_id}` | Hent status, fremgang, målinger og eventuell feil |
| `POST /training-runs/{run_id}/stop` | Be om kontrollert stopp og lagring |
| `GET /training-runs/{run_id}/recording` | Hent et nyere opptak med identifikator |
| `GET /networks/{network_id}/checkpoint` | Last ned en bestemt eller siste ferdige versjon |
| `POST /networks/{network_id}/predict` | Senere: batchet inferens mot en valgt checkpointversjon |

Eksempel på treningsbestilling:

```json
{
  "network_id": "maze-history-v1",
  "additional_generations": 2000,
  "request_id": "unik-id-fra-klienten"
}
```

Returner `run_id`, startgenerasjon og målgenerasjon. Samme `request_id` må ikke starte to jobber ved retry. Bruk eksplisitte tilstander som queued, running, stopping, completed, stopped og failed. Nettverksbrudd hos klienten skal ikke stoppe treningen.

Registrer nettverkstype, arkitektur, observasjonsversjon, handlingsformat, trener, spilladapter, konfigurasjon og avhengige modeller. Valider formater og antall vekter ved import. API-et skal velge kjente adaptere, ikke kjøre vilkårlige kommandoer mottatt fra klienten.

Start med lokal binding på Studio og SSH-tunnel fra den andre maskinen. Ved direkte LAN-tilgang, legg til autentisering og konfigurer eksplisitt lytteadresse. Maskinnavn og bruker må finnes i miljøet eller oppgis; de er ikke kjent fra dette dokumentet.

## Lagring og videre trening

Bevar originalcheckpointene. Importer en kopi til tjenestens modellområde, og registrer filhash og opphav. Lagre checkpoints atomisk. Bevar regler, arkitektur, generasjon, historikk, progresjon og relevante seeds sammen med vektene. Den fryste kryssdetektoren må følge modellen.

Dagens evolusjonstrening gjenopptar fra lagrede vekter og progresjon, men lager en ny populasjon. Dette er ikke en bit-for-bit videreføring av en uavbrutt prosess. Ikke lov eksakt gjenopptak uten å implementere lagring av hele treningstilstanden. De tidligere MLX-eksperimentene har heller ikke nødvendigvis lagret optimizer-tilstand.

Git-repoet inkluderer modellvekter og rapporter. Behold dette. Ignorer virtuelle miljøer, cache, logger, hemmeligheter og midlertidige filer. Serverens aktive database, låser og runtimefiler bør holdes utenfor Git; eksporter ferdige, portable checkpoints til repoets modellområde når brukeren vil versjonere dem. Ikke ignorer hele models-mappen.

## Oppsett på Mac Studio

Kontroller først maskintype, Python og eventuelle prosjektinstruksjoner. Python 3.12.8 og MLX 0.32.4 var et fungerende oppsett på kildemaskinen. Installer Python 3.12 hvis det mangler, med tilgjengelig installasjonsverktøy.

Fra den overførte prosjektmappen:

```sh
python3.12 -m venv .venv-studio
.venv-studio/bin/python -m pip install -r requirements-gpu.txt
.venv-studio/bin/python -c 'import mlx.core as mx; print("Metal tilgjengelig:", mx.metal.is_available())'
.venv-studio/bin/python -m unittest discover -s tests -v
```

Kontroller faktisk GPU-beregning, ikke bare at importen lykkes. Installer eventuelle nye API-avhengigheter i miljøet og dokumenter dem i en egen avhengighetsfil.

Eksisterende avspilling kan brukes som kontroll før API-et bygges:

```sh
.venv-studio/bin/python -m games.maze.app --replay --model games/maze/models/deterministic_history_v1.json --backend mlx-gpu --port 8774
```

Dette starter den gamle appen, ikke den foreslåtte AI-tjenesten. Velg en egen ledig port for den nye tjenesten, for eksempel 8780. Dokumenter den faktiske startkommandoen etter implementering.

## Gjennomfør i denne rekkefølgen

1. Finn repo og vekter, les lokale instruksjoner, og kontroller Python og MLX på Studio.
2. Bekreft at dagens modell kan lastes og kjøre uten arkitektur- eller formatendring.
3. Lag modellregister og importer en kopi av dagens modell med kryssdetektoren.
4. Koble en treningsjobb til eksisterende Trainer. Legg til status, opptak, kontrollert stopp og atomisk lagring.
5. Test med noen få generasjoner i en separat testmodell før lengre trening.
6. Lag en liten Python-klient og et konkret eksempel på bruk fra en annen Mac. La serveren fortsette når klienten kobles fra.
7. Legg til en valgfri remote-konfigurasjon i appen. Behold lokal kjøring. Status og opptak skal kunne komme fra Studio uten lokal trening.
8. Dokumenter oppstart, tilkobling, import, eksport, stopp og gjenopptak. Vis faktisk testresultat og hva som gjenstår.

Første versjon er ferdig når klienten kan bestille trening av den importerte labyrintmodellen, følge fremgangen, vise et opptak, stoppe kontrollert og starte videre fra lagrede vekter. En fullført jobb må produsere et checkpoint som fortsatt kan lastes av eksisterende kode. Test også ugyldig input, dobbelt innsending av samme oppdrag og omstart av API-et under en jobb. Gjenopprett eller marker avbrutte jobber tydelig; ikke la dem stå som kjørende uten prosess.

## Senere modeller

Bilspillet kan bruke en egen adapter for evolusjonstrening; GPU-evalueringen er ikke allerede generell for bilspillet. Kryssdetektoren i `games/maze/junction/` bruker MLX-trening med en differensierbar belønning. LSTM-forsøkene i `games/maze/modular/` og `games/maze/place_memory/` har egne sekvensoppgaver og treningssløyfer. Bevar disse forsøkene, men utsett API-integrasjonen til labyrintmodellen fungerer.

Svar brukeren på norsk. Begynn med å undersøke prosjektet på Studio, og bygg første fungerende versjon stegvis. Be om prosjektfilene hvis de mangler; ikke erstatt de trente modellene med tilfeldige vekter.
