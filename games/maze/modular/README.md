# Tre nett med LSTM — eksperiment 17. oktober 2026

Dette er et separat eksperiment. Det endrer ikke `learned_memory_40_three_layers.json` eller den opprinnelige appen på port 8770. Modellene ligger i `games/maze/models/modular_lstm_v2/`; `report.json` inneholder målte resultater. `v1` er en kortere innledende komponenttest, uten trent beslutningsnett.

## Kjøring

Bruk prosjektets Python 3.12-miljø med MLX fra `requirements-gpu.txt`:

```sh
.venv-gpu/bin/python -m games.maze.modular.app --port 8771
# Nytt eksperiment: velg en ubrukt output-mappe.
.venv-gpu/bin/python -m games.maze.modular.train --output games/maze/models/modular_new --memory-steps 1500 --policy-iterations 180
.venv-gpu/bin/python -m unittest tests.test_modular
```

Trening nekter å overskrive et eksisterende forsøk, unntatt eksplisitt `--phase decision`, som trener et nytt beslutningsnett fra de lagrede komponentene. Det er ikke en gjenopptakelse av optimizer-tilstand. Visningen laster ferdige vekter ved oppstart. Å nullstille minneinput i visningen påvirker bare beslutningsnettets tilgang til h-tilstanden, ikke modellen på disk.

## Arkitektur og grensesnitt

1. **Gjenkjennelse:** 8 → 32 → 32 → 8. Åtte stråleavstander klippes ved ti ruter og deles på ti. Fire utganger beskriver sannsynligheten for fri naborute i rekkefølgen frem, tilbake, høyre, venstre; fire beskriver avstandene. Antall åpne veier og kryssform kan utledes av disse. Trenes på simulatorens lokale fasit, ikke på veien til utgangen, og fryses deretter.
2. **Hukommelse:** LSTM med 15 inputverdier og 256 enheter (256 h + 256 c). Input er åtte utganger fra gjenkjenningsnettet, forrige handling som fire indikatorer, to relative bevegelsesverdier og relativ vending. Ingen absolutte koordinater. LSTM-tilstanden oppdateres ved hver bevegelsesobservasjon; i denne prototypen er en hendelse et steg, ikke bare et veikryss. Ny labyrint nullstiller begge tilstandene. Vektene fryses før navigasjonstreningen.
3. **Beslutning:** En lært avlesning kombinerer nåværende gjenkjennelse og h til 32 verdier. Disse kombineres med følere, gjenkjennelse og forrige handling, og går gjennom et skjult lag på 64 enheter til fire handlingsutganger. Avlesningen trenes sammen med beslutningsnettet. Bevegelseskontrollen er samme diskrete ett-rute-handling som før; det er ikke et fjerde nett. Målet er fast: utforsk og finn utgangen. Ingen målkoordinater eller objektjakt er implementert.

## Trening

Gjenkjennelse trenes med 500 Adam-oppdateringer på 5120 lokale observasjoner fra 160 labyrinter, og testes på 1280 observasjoner fra 40 andre labyrinter. «Åpen retning»-nøyaktighet gjelder individuelle retninger, ikke hele kryss.

Minne trenes med 1500 oppdateringer per nivå (5, 10, 20, 40, 67 hendelser), batchstørrelse 32. Kortere lengder repeteres underveis for å begrense glemsel. Hver sekvens er syntetisk og inneholder tilfeldig kryssbeskrivelse og retningsvalg. Retningsvalget er fasit for gjenhenting. En avlesningsmodul får bare siste h-tilstand og produserer fire klasseverdier for hver av 67 indeksposisjoner. Den kan dermed svare på «hva var valget i hendelse 17?». Den får ikke tidligere skjulte tilstander eller originalsekvensen ved avlesning. Fasit ligger kun i tapet. Testene bruker 256 separate sekvenser per lengde; tilfeldig retningsgjetting gir 25 %. Dette tester retningshistorikk, ikke full rekonstruksjon av kryss og lengder eller gjenkjennelse av et fysisk sted.

Beslutning trenes med REINFORCE og entropibonus i 180 batchrunder à 32 labyrinter, opptil 96 steg. Vanskelighetsgrader er 5×5, 9×9 og 15×15, 60 runder hver. Ingen programmert utforsker, imitasjonsfasit eller skjult løsningssti brukes. Første besøk på ny rute gir +1, hvert steg −0,02, veggkontakt −2 og utgang +20. Retur er lov, og veggkontakt avslutter ikke forsøket. Besøkstellere og hele kartet finnes i simulatoren for belønning, men er ikke input til nettene. Tilfeldig handlingssampling brukes i trening; avspilling og test velger høyeste utgang. Modellen trenger derfor ikke minne for å bryte enkelte løkker under selve treningen.

## Resultater og begrensninger

Gjenkjennelse: 99,73 % riktige enkeltretninger. Etter hele minnekurset er gjenhenting 100 % for 5 og 10 hendelser, 99,98 % for 20, 84,68 % for 40 og 67,36 % for 67. Ingen av de 256 hele 67-hendelses-sekvensene ble gjengitt feilfritt. Målet om pålitelig bevaring av 67 hendelser er derfor **ikke nådd**.

Navigasjon testes på 40 nye labyrinter per størrelse og maks 256 steg, med identiske labyrinter for normalt og nullstilt minneinput. Resultatene for 15×15 er 25/40 med minne og 26/40 uten. Dette viser foreløpig ingen positiv effekt av minnet. Det er ikke direkte sammenlignbart med den gamle modellens 28/100: belønning, testsett, stoppregel og stegbudsjett er forskjellige. En minneablasjon kan dessuten gi input modellen ikke så under trening; eventuell forskjell er ikke alene bevis på romlig hukommelse.

Den viktigste åpne utfordringen er overføring fra syntetisk gjenhenting til beslutningsrelevant romlig minne. En rekurrent tilstand og god sekvensgjenhenting er ikke tilstrekkelig dokumentasjon på systematisk traversering. Videre forsøk bør bruke oppgaver som krever tidligere observasjoner, prøve gjenhenting av besøkte forgreninger og måle normal/shufflet/nullstilt hukommelse på flere seeds.
