# Isolert stedshukommelse med tilfeldig plassering

Botten går ikke. Den plasseres ved tilfeldig valgte hjørner og forgreninger. Gjenbesøk er tillatt. Den frosne kryssdetektoren fra `junction_detector_v1` gir et lagringssignal. Et nytt LSTM-nett får bare de åtte normaliserte stråleavstandene og forrige h/c-tilstand, svarer «vært her før?», og oppdaterer deretter minnet hvis detektoren utløser lagring. Botten vender alltid østover. Ingen koordinater, sted-ID, bevegelse, kart, fasit eller belønning inngår i nettets input.

Svaret leses **før** dagens målinger skrives til tilstanden. Fasit er om den fysiske ruten forekom blant tidligere plasseringer i samme episode; riktig svar gir +1, feil −1. Fasit føres deterministisk i simulatoren og brukes bare i trening/evaluering. Trening bruker binær kryssentropi og Adam som et stabilt læringssignal for denne binære belønningsoppgaven. Dette er ikke REINFORCE. LSTM og svaravlesning trenes sammen; detektoren er frosset. Et svar er feil om det ikke samsvarer med besøksfasiten, også dersom to steder har identiske stråler.

Arkitektur: 8 → 32-encoder → LSTM med 256 enheter (256 h + 256 c); avlesning av dagens åtte målinger og gammel h går via 128 enheter til én ja/nei-logit. Begge tilstandene nullstilles mellom episoder. Den frosne detektoren bruker sin opprinnelige skalering (avstander klippet ved ti ruter); minnenettet får alle åtte stråler uten denne klippingen, delt på to ganger labyrintdiagonalen.

## To gjennomførte forsøk

`models/place_memory_v1`: 1200 oppdateringer, uniform tilfeldig plassering på 15×15. Ved 67 plasseringer er nøyaktighet 75,64 %, men 75,72 % med historikk fra et annet forsøk på samme tidssteg. Dette er ikke bevis på stedshukommelse: andelen gjenbesøk øker med tiden, og modellen kan lære denne sannsynligheten. Ikke bruk sammenligning bare mot nullstilt minne som bevis.

`models/place_memory_v2`: 2400 oppdateringer, 256 treningslabyrinter på 21×21. Halvparten av valgene trekkes fra tidligere besøkte steder og halvparten fra nye når begge finnes. Første plassering er alltid ny. Stedet innen valgt gruppe trekkes tilfeldig. Flere kryss gjør at nye steder er tilgjengelige gjennom de fleste 67-stegssekvenser. Trening øker sekvenslengden gjennom 10, 20, 40 og 67, 600 oppdateringer per nivå, batchstørrelse 32. Dette er et nytt forsøk fra tilfeldige vekter.

På usette labyrinter, 128 testsekvenser per lengde, gir v2 ved 67 plasseringer:

- Normalt minne: 51,43 % riktige svar.
- Minne nullstilt før hvert spørsmål: 49,95 %.
- Avlesning av h fra en annen testsekvens på samme tidssteg: 51,42 %.

Denne modellen har **ikke demonstrert nyttig stedsgjenkjenning**. At h-tilstanden endres, er ikke tilstrekkelig. 4094 av 7199 mulige teststeder har samme strålesignatur som et annet sted i samme labyrint (avrundet til 8 desimaler for numerisk toleranse). Dette er andel steder med tvetydige målinger, ikke et beregnet øvre tak for nøyaktighet. Tilfeldig teleportering uten koordinater, bevegelsesinformasjon eller unike kjennetegn kan gjøre fysisk sted umulig å avgjøre sikkert. Det forklarer ikke alene modellens lave resultat; også læring og minnearkitektur er begrensninger.

Lagring ble utløst på 100 % av de testede hjørnene/kryssene. Grensen på 67 gjelder antall hendelser, ikke 67 forskjellige steder. Ved senere forsøk bør korte sekvenser med tydelig ulike målinger mestres før lengden økes; man kan også teste «har jeg sett denne målesignaturen?» separat fra «har jeg vært på denne fysiske ruten?».

## Kjør

```sh
.venv-gpu/bin/python -m games.maze.place_memory.app --port 8773
# Ny balansert trening; velg ny output-mappe:
.venv-gpu/bin/python -m games.maze.place_memory.train --output games/maze/models/place_memory_new --updates 2400 --maze-size 21 --sampling balanced
# Oppsettet i v1:
.venv-gpu/bin/python -m games.maze.place_memory.train --output games/maze/models/place_memory_uniform_new --updates 1200 --maze-size 15 --sampling uniform
.venv-gpu/bin/python -m unittest tests.test_place_memory
```

Visningen viser en ferdigtrent modell, ikke pågående oppdatering av vekter. Knappene flytter mellom forhåndsberegnede tilfeldige plasseringer. Grønne besøksmarkører og fasit er kun for betrakteren. De tidligere forsøkene og appene er bevart.
