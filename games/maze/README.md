# Labyrint i AI-spill

En mann lærer å finne ut av tilfeldige labyrinter ved hjelp av den felles klassen `NeuralNetwork`. Labyrintmotor, regler, evaluering og visning er uavhengige av bilspillet. Python beregner alt; nettleseren viser opptak fra faktiske forsøk.

## Start

Fra prosjektroten:

```sh
python3 -m games.maze.app
```

Åpne http://127.0.0.1:8767/. Standard er 60 generasjoner, 36 kandidater, 8 treningslabyrinter og nettverket 107 → 12 → 8 → 2. Modellen lagres etter hver generasjon i `games/maze/models/maze.json`. Et eksisterende forsøk overskrives ikke ved ny oppstart: velg `--resume`, `--replay` eller et nytt filnavn.

```sh
# Et separat, repeterbart forsøk uten nettleser/server:
python3 -m games.maze.app --headless --seed 42 --generations 20 --model games/maze/models/forsok_42.json

# Fortsett trening med de lagrede innstillingene:
python3 -m games.maze.app --resume --generations 40 --model games/maze/models/forsok_42.json

# Vis den lagrede modellen på en ny labyrint uten trening:
python3 -m games.maze.app --replay --model games/maze/models/forsok_42.json
```

Pause og tempo gjelder bare visningen. Treningen fortsetter uavhengig. Under trening spiller visningen ett opptak ferdig, og velger deretter det nyeste; ikke alle kandidater vises. Etter trening eller med `--replay` genereres en ny tilfeldig labyrint etter hvert ferdige forsøk. «Neste labyrint» lar deg bytte med en gang. Demonstrasjonene bruker egne seeds og uendrede vekter. Nye fullførte forsøk teller mot kravet på 10 på rad og kan utløse størrelsesøkning. Gjentatt avspilling teller aldri som nye beståtte prøver. Treningens generasjon/størrelse og opptakets generasjon/størrelse er merket separat.

## Første nivå: lær å gå i åpent terreng

Nye forsøk starter i et 30 × 30 svart landskap med 50 tilfeldig plasserte grå steiner. Mannen starter på en av de fire midterste rutene (15, 15 med nullbaserte koordinater) med tilfeldig retning. Alle kantceller er mål: å nå en hvilken som helst kant gir samme belønning som å komme ut av labyrinten. Steinene opptar én hel rute og stopper bevegelse og følere som vegger. Starten er fri, og motoren kontrollerer at kanten kan nås.

Nye oppsett brukes gjennom treningen, med samme minne, binære handlinger, straffer og opptaksrytme som før. Etter **20 feilfrie nye forsøk på rad** med samme modell økes antallet bokser: **50 → 75 → 100**. Etter 20 feilfrie på rad med 100 bokser overføres vektene til første **5 × 5-labyrint**. Landskapet forblir 30 × 30 under hele gåtreningen. Rekken nullstilles. Først etter dette gjelder 50 % økning for labyrintstørrelsene. Det åpne nivået kommer i tillegg til de fire labyrintnivåene. Ingen løsning eller ekstra styrehjelp gis til nettverket.

`--field-size 30 --field-stones 50` styrer landskapet. `--no-start-in-field` starter direkte med labyrint. Eldre modellfiler uten disse innstillingene fortsetter på sitt lagrede labyrintnivå. Et eget checkpoint med `_field` i navnet lagres når gåtreningen er mestret. Første forsøk med denne progresjonen lagres i `models/field_start.json`; det starter fra nye tilfeldige vekter.

## Den tilfeldige labyrintmotoren

`generator.generate(width, height, seed=...)` bygger et rutenett med tilfeldig dybde-først-søk. Den forbinder rom ved å åpne korridorer mellom dem. Startrom, startretning og plassering av utgangen varierer med seed. Ett hull i ytterveggen merkes `E`. De øvrige ytterkantene er vegger. Det finnes alltid en vei fra starten til utgangen; motoren validerer dette.

Motoren støtter både partalls- og oddetallsdimensjoner, inkludert rektangulære labyrinter. Ved partallsdimensjoner kan den siste veggstripen være to ruter tykk; utgangskorridoren åpnes helt til ytterkanten. Minste størrelse er 5 × 5 ruter, inkludert yttervegger: fire små rom og korridorer mellom dem. Dette er en diskret ruteverden, ikke kontinuerlig fysikk.

Samme seed og størrelse gir samme labyrint. `shortest_path` er et diagnoseverktøy for motorens tester. Ruten brukes aldri som fasit eller input under læringen, og påvirker ikke belønningen.

## Når labyrinten vokser

Hver generasjon får et nytt tilfeldig treningssett. Alle kandidatene og den tidligere vinneren vurderes på dette samme settet for en rettferdig sammenligning; tidligere poeng gjenbrukes ikke når oppgavene endres. Hver femte generasjon prøves den beste modellen på opptil 20 nye labyrinter som ikke inngår i treningen.

**20 nye labyrinter løst feilfritt på rad** med samme modell utløser 50 % økning i begge dimensjoner, avrundet opp. Ett mislykket forsøk nullstiller rekken. Endrede vekter nullstiller også rekken. Prøvene stoppes straks kravet er nådd. Etter trening teller også nye demonstrasjoner med uendrede vekter; gjenvisning av et opptak teller aldri på nytt.

Motoren sammenligner faktiske veggoppsett, ikke bare seed eller startposisjon. Innen hver strøm av nye labyrinter avvises oppsett som matcher de to siste. Visningsopptak har i tillegg en sperre mot tre like oppsett på rad. Størrelsen holdes uendret mens mannen prøver nye oppsett frem til kravet er nådd.

| Nivå | Størrelse |
| --- | --- |
| 1 | 5 × 5 |
| 2 | 8 × 8 |
| 3 | 12 × 12 |
| 4 | 18 × 18 |

Ett mislykket forsøk nullstiller rekken. Standardforsøket har fire størrelsesnivåer. `--stages` endrer antallet. På siste nivå fortsetter treningen innenfor det valgte generasjonsbudsjettet. Størrelsen økes aldri bare fordi et bestemt antall generasjoner er gått.

Før økning lagres også en modell for mestret størrelse, for eksempel `forsok_42_5x5.json`. Vektene følger med til større labyrinter. Poeng måles på nytt fordi oppgaven har endret seg. Generasjonsloggen lagrer hvilken størrelse hvert resultat gjelder; poeng fra forskjellige størrelser bør ikke sammenlignes direkte.

Prøvene styrer progresjonen og er derfor utviklingsevaluering, ikke en endelig uavhengig test. En høy treffprosent på 20 labyrinter dokumenterer heller ikke at alle labyrinter kan løses.

## Handlinger og regler

To utganger representerer venstre og høyre. Hver tanh-verdi terskles uavhengig: større enn null betyr 1 (på), null eller negativ betyr 0 (av). Verdiene er ikke sannsynligheter; største verdi velges ikke lenger.

| Venstre | Høyre | Handling |
| --- | --- | --- |
| 0 | 0 | Stå stille |
| 1 | 0 | Snu 90° venstre |
| 0 | 1 | Snu 90° høyre |
| 1 | 1 | Gå én rute frem |

«Stå stille» bruker én handling, inngår i det komprimerte minnet og omfattes av stillstandsstraffen fra femte handling uten bevegelse. Utgangsbitene vises i panelet. Første ramme før en beslutning viser 00.


| Hendelse | Standard |
| --- | --- |
| Ett vellykket skritt frem | +1 |
| Vending venstre eller høyre | −0,02 |
| Fra femte handling uten endret posisjon | −1 ekstra per handling |
| Forsøk på å gå inn i vegg | −5; blir stående og får fortsette |
| Gå inn på en besøkt rute | −0,5 per tidligere besøk, i tillegg til +1 |
| Gå inn i utgangen | +100 i tillegg til skrittbelønningen |
| Maks handlinger | 128, deretter avsluttes forsøket |

Venstre/høyre roterer mannen 90° på stedet; de flytter ham ikke. Frem flytter én hel rute i nåværende retning. Vendinger teller i handlingshistorikken, men øker ikke besøkstelleren for ruten. Et veggkrasj flytter ikke mannen gjennom veggen. Å nå åpningen i ytterveggen regnes som å komme ut.

Fremoverbelønningen gjelder vellykket bevegelse, ikke kortere avstand til målet. Første retur til en rute gir netto +0,5, neste netto 0, deretter negativ belønning. Gjentakelsesstraffen vokser med antall besøk for å gjøre vedvarende sirkling mindre lønnsomt. Besøkstellerne gjelder hele forsøket og nullstilles ved neste start. Vendingstraffen er liten, men motvirker å snurre uten å bevege seg.

Dette er første regelsett, ikke en påstand om at belønningene er optimale. Se særlig etter sirkling, overdreven vending og strategier som går langt uten å finne ut. Alle tall kan endres for et nytt forsøk, for eksempel:

```sh
python3 -m games.maze.app --model games/maze/models/andre_regler.json --forward-reward 1 --wall-penalty 8 --revisit-penalty 0.75 --exit-reward 100 --turn-penalty 0.03 --max-steps 200
```

## Trådfølere

Sju stråler ligger ved −90°, −60°, −30°, 0°, 30°, 60° og 90° relativt til mannens retning, samme vinkeloppsett som bilspillet. De måler avstand fra midten av ruten til første vegg. Motoren beregner skjæringer med rutenettet; stråler slipper ikke gjennom hjørner mellom tilstøtende vegger.

Alle følerne har maksimal rekkevidde lik to ganger labyrintens diagonal, altså lengre enn hele labyrinten. En stråle som går uhindret gjennom utgangen fortsetter ut i det fri og returnerer maksimal rekkevidde. En vegg foran åpningen blokkerer strålen. Det gis ingen separat beskjed om utgangens retning: nettet må tolke avstandene. Avstandene deles på maksimal rekkevidde før de mates inn.

## Hukommelse: de siste 50 handlingene, komprimert

1. Ta de siste 50 handlingene i kronologisk rekkefølge.
2. Slå sammen påfølgende like handlinger til `(handling, antall)`.
3. Mat hvert par inn som to verdier. Fyll resten med nuller.

Eksempel:

```text
frem × 50                    → (frem, 50)
frem × 20, høyre, frem × 10  → (frem, 20), (høyre, 1), (frem, 10)
frem × 60, høyre × 3        → (frem, 47), (høyre, 3)
```

Grensen gjelder 50 opprinnelige handlinger, **ikke** 50 komprimerte sekvenser. Den eldste delen kuttes før komprimering. Frem etter en vending slås ikke sammen med frem før vendingen.

For numerisk input kodes frem som 1/4, venstre som 2/4, høyre som 3/4 og stå stille som 1. Antallet deles på 50. `(frem, 50)` blir dermed `[1/4, 1]`: to aktive innganger. `(0, 0)` betyr en ubrukt plass. Ved oppstart er hele minnet null, og ved nytt forsøk nullstilles det.

I verste fall veksler hver handling, og det trengs 50 par = 100 minneinnganger. Sammen med de sju følerne gir dette **107 faste innganger**. Komprimering gjør ikke lagstørrelsen dynamisk; den reduserer antall aktive minneverdier for lange like sekvenser. Den felles nettverksklassen hopper over multiplikasjon med nullverdier.

Nettet får ikke kartet, besøkskartet, absolutte posisjoner, tidligere poeng eller utgangens koordinater. Motoren lagrer fortsatt alle besøk og posisjoner separat for straff og visning. Å huske mer enn de siste 50 handlingene er ikke tilgjengelig for nettverket. `--memory-steps` kan endre vinduet i et nytt forsøk; det endrer også inngangsstørrelsen.

## Forslag: observert kart som input — 16. oktober 2026

Dette er en dokumentert idé til neste modell, **ikke implementert**. Den skal erstatte den komprimerte handlingshistorikken med et bilde/matrise av det mannen hittil har sett av labyrinten. Målet er å gi nettet direkte romlig informasjon om vegger og ruter han har gått, fremfor at det må rekonstruere dette fra handlingene.

Kartet skal skille mellom ukjente områder, observerte vegger, observert fri plass og besøkte ruter. Bare det mannen faktisk har oppdaget skal inngå; hele den skjulte labyrinten skal ikke gis til nettet. Kartminnet oppdateres under forsøket og nullstilles ved en ny labyrint. Egen posisjon og retning må også representeres, enten i kartet eller med egne innganger, slik at kartet kan brukes til å velge handling.

Brukerens forslag til nettverk er at hvert påfølgende lag har omtrent **en fjerdedel så mange nevroner** som det forrige, helt ned til de to utgangene. Et illustrerende eksempel med én verdi per rute i et 30 × 30-kart er:

```text
900 innganger → 225 → 57 → 15 → 4 → 2 utganger
```

Her avrundes kvartdelingen oppover, og siste lag settes til to. Eksemplet viser dimensjoneringen, ikke et endelig valg av kartkoding. Flere kartkanaler eller egne innganger for posisjon og retning vil endre antallet innganger. De to binære styringsutgangene beholdes: begge av = stå stille, bare venstre på = snu venstre, bare høyre på = snu høyre, begge på = gå frem.

Før implementering må vi velge kartkoding, hva følerne kan avdekke, og hvordan kartets størrelse holdes kompatibel med samme nettverk når labyrintene vokser, for eksempel med et fast kartvindu eller et fast maksimalformat. Det må også avklares om de sju avstandsfølerne beholdes som ekstra innganger. Forslaget innebærer ikke i seg selv et konvolusjonsnett; en matrise kan også flates ut til innganger i den eksisterende felles nettverksklassen.

Effekten må måles på nye labyrinter med samme treningsbudsjett som referansemodellen. Flere lag og flere vekter er en hypotese om bedre læring, ikke dokumentasjon på at det trengs færre treningsrunder. Nye modeller får eget observasjonsformat og egne modellfiler.

## Innstillinger og modellfiler

Bruk `python3 -m games.maze.app --help` for alle valg. De viktigste er:

| Flagg | Standard | Betydning |
| --- | --- | --- |
| `--width`, `--height` | 5, 5 | Startstørrelse inklusive vegger |
| `--stages` | 4 | Maks antall størrelsesnivåer |
| `--generations` | 60 | Antall nye generasjoner i denne kjøringen |
| `--seed` | 42 | Nettverk og labyrintutvalg |
| `--hidden` | 12 8 | Skjulte lag |
| `--population` | 36 | Kandidater per generasjon |
| `--train-mazes` | 8 | Labyrinter i treningssettet per størrelse |
| `--validation-mazes` | 20 | Nye labyrinter per prøve |
| `--check-every` | 5 | Generasjoner mellom prøver |
| `--success-streak` | 20 | Nye labyrinter løst på rad før økning |
| `--memory-steps` | 50 | Antall siste handlinger før komprimering |
| `--max-steps` | 128 | Maks handlinger per forsøk |

En siste, kortere generasjonsblokk evalueres også. Ved lange labyrinter kan 128 handlinger bli for lite. Sett en høyere grense ved starten av et nytt forsøk; det endrer ikke nettverksstørrelsen når minnevinduet er uendret.

Modellen lagrer vekter, arkitektur, seed, generasjonslogg, alle regler, størrelsesnivå, prøveindeks, bestått-rekke og prøveresultater med seed og utvalgsstørrelse. Videre trening og avspilling bruker de lagrede innstillingene; de avviser motstridende konfigurasjonsflagg. Bruk et nytt filnavn for nye regler eller annen arkitektur. En bilmodell kan ikke lastes som labyrintmodell.

Læring skjer med den felles klassens utvalg og mutasjon, ikke en egen treningsalgoritme i spillet. Resume lager en ny populasjon rundt den beste modellen og måler den på nytt; det er ikke en nøyaktig gjenoppretting av en avbrutt populasjon. Lagring skjer atomisk etter fullførte generasjoner. Stopp midt i en generasjon mister arbeidet siden siste lagring.

## Filer og tester

- `world.py`: labyrintdata, handlinger, regler, stråler, komprimering og observasjoner.
- `generator.py`: tilfeldig generering, 50 %-vekst og rutediagnostikk.
- `training.py`: spillvurdering, valideringsprøver, progresjon og kobling til `NeuralNetwork`.
- `app.py`: kommandolinje og lokalt HTTP-API.
- `index.html`: mann, vegger, utgang, følere, besøkte ruter og treningsstatus.
- `../../ai/network.py`: felles nettverk og læring, uten spilleregler.
- `../../tests/test_maze.py`: regresjonstester for motor, spill, hukommelse og progresjon.

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s v2 -p 'test_*.py' -v
```

Motoren testes på mange seeds og både like og ulike dimensjoner. Testene dekker også lang sikt gjennom utgangen, blokkering ved vegg/hjørne, vendinger, kollisjon, utgangsbelønning, gjentakelsesstraff, komprimering, 50-handlingsgrense, lagring/videre trening og automatisk størrelsesøkning. Kontrollert suksess brukes i progresjonstesten for å teste regelen; den er ikke dokumentasjon på at en trent modell har mestret labyrintene.

## Første gjennomførte forsøk

15. oktober 2026: `models/first_run.json`, seed 42, standardregler og standardnettverk, 20 generasjoner. Prøvene ved generasjon 5, 10, 15 og 20 hadde hver 11 av 20 vellykkede forsøk på nye 5 × 5-labyrinter (55 %). Beste gjennomsnittlige treningspoeng var 77,935. Kravet for økning ble ikke nådd, så modellen ble på 5 × 5. Dette er et første referanseresultat, ikke en ferdig lært labyrintløser.

Vis eller fortsett dette forsøket:

```sh
python3 -m games.maze.app --replay --model games/maze/models/first_run.json
python3 -m games.maze.app --resume --model games/maze/models/first_run.json --generations 40
```

Nytt forsøk etter tilbakestilling av vektene: `models/random_restart.json`, seed 20261015. Det tidligere forsøket i `first_run.json` beholdes uendret som referanse. Den nye progresjonsregelen erstatter den gamle 90 %-regelen; gamle prøverekker overføres ikke.

## Stillstand og rask bakgrunnstrening

Begge vendinger støttes: venstre er −90°, høyre +90°. Nettverket terskler venstre- og høyreutgangen hver for seg; det kaster ikke terning for hver handling. Derfor kan en svak modell velge samme vending gjentatte ganger.

Fra femte handling på samme rute gis −1 ekstra per handling, også ved vekslende venstre/høyre. Vellykket bevegelse nullstiller telleren, også når ruten har vært besøkt før. Vanlig vending koster fortsatt −0,02, så femte vending koster totalt −1,02. Veggstraffen beholdes. `--stationary-penalty` endrer ekstrastraffen i et nytt forsøk.

Under trening kjøres ti hele forsøk uten opptak, deretter tas opptak av det ellevte. Treningen venter aldri på avspilling. Validering tar fortsatt ett kontrollopptak per prøve. Følerberegninger gjenbrukes for identiske posisjoner og retninger i samme labyrint, med begrenset mellomlager. Dette endrer ikke fysikk, input eller belønning. Nettleseren viser nyeste tilgjengelige opptak når forrige er ferdig; ved rask trening kan flere opptak passere uten å bli vist.

`models/anti_spin.json` fortsetter fra de lærte vektene i `random_restart.json` med stillstandsstraffen. Tidligere poeng og bestått-rekke nullstilles fordi reglene er endret. Den tidligere modellfilen beholdes.

## Fortsett etter veggkontakt

Et forsøk avsluttes nå bare ved utgangen eller grensen på 128 handlinger. Tidligere avsluttet første veggkontakt forsøket, som ofte ga korte opptak på omtrent ti handlinger. Nå gir veggkontakt fortsatt −5, men mannen blir stående og kan snu og prøve igjen. Stillstandsstraffen gjelder også ved gjentatte veggkontakter. Dermed har han rom for 20–30 handlinger og mer uten å øke tidsgrensen.


Det nye forsøket `models/binary_controls.json` starter fra tilfeldige vekter på 5 × 5 med to utganger. Modeller med den gamle tre-utgangskodingen og det gamle minneformatet avvises som inkompatible, men beholdes som historiske filer. Arkitekturen er 107 → 12 → 8 → 2. Begge skjulte lag er beholdt.

`--field-stones-step 25 --field-stones-max 100` styrer økningen. Gjeldende antall bokser lagres i modellen og vises i panelet. Forsøket `field_50_fresh.json` starter fra nye tilfeldige vekter, generasjon 0 og nullstilt suksessrekke, i 30 × 30 med 50 bokser. Ingen vekter overføres fra gamle modeller. Handlingsgrensen er fortsatt 128.

Gjeldende krav: 20 feilfrie nye forsøk på rad. Et forsøk teller bare når kanten/utgangen nås uten kollisjoner og uten en eneste stillstandsstraff. En feil eller endrede vekter nullstiller rekken. Gamle rekker fra tidligere kriterier overføres ikke. `field_20_clean.json` starter godkjenningen på nytt med 50 bokser, men beholder de lærte vektene.

## Forsøk med 150 bokser — 16. oktober 2026

`models/field_150_boxes.json` viderefører vektene fra `field_20_clean.json` i 30 × 30 med nøyaktig 150 grå bokser. Oppsettene varierer, og motoren kontrollerer at kanten kan nås. Suksessrekken er nullstilt for den nye vanskelighetsgraden. Etter 20 feilfrie nye forsøk på rad går modellen videre til første labyrint. Belønningene og handlingskodingen er uendret.

## Overgang til labyrinter — 16. oktober 2026

På brukerens ønske flyttes modellen fra 150-bokslandskapet til 5 × 5-labyrinter etter generasjon 380. `models/maze_transfer.json` beholder vektene; poeng og godkjenningsrekke nullstilles. Overgangen er manuell og dokumenterer ikke bestått landskapskrav. Videre vekst til 8 × 8 krever fortsatt 20 feilfrie nye forsøk på rad.

## Planlagt overgang etter 500 generasjoner

`maze_500_then_larger.json` fortsetter fra generasjon 885 til 1385 på fast 5 × 5. Deretter bytter den automatisk til 8 × 8 og viser modellen der. Vektene beholdes, suksessrekken nullstilles og en kopi fra før overgangen lagres. Dette er en brukerbestemt overgang, ikke et bevis på at mestringskravet er nådd. Videre trening på 8 × 8 kan startes med `--resume`.

## Forsøk med selvskrevet minne — 16. oktober 2026

Start: `python3 -m games.maze.app --learned-memory --model games/maze/models/learned_memory_40.json --generations 60 --port 8770`.
Bruk `--resume` eller `--replay` og samme modellfil ved senere oppstart (uten `--learned-memory`; innstillingene er lagret).

Denne valgfrie modellen starter fra tilfeldige vekter på 5 × 5-labyrinter, uten landskapstrinnet. Gamle modeller og deres regler beholdes. Standard er 40 skrivebeskyttede minneplasser per forsøk. Nettet har 88 innganger: åtte stråler med 45° mellomrom, 40 minneverdier og 40 bruktmarkører som skiller lagret null fra tom plass. Arkitekturen er 88 → 12 → 8 → 6.

De fire første utgangene konkurrerer (høyeste verdi vinner; likhet avgjøres i fast rekkefølge frem, tilbake, høyre, venstre). Alle handlinger forsøker å flytte én rute relativt til gjeldende retning. Mannen vender seg i valgt retning, også ved veggkontakt. Ingen stillstands- eller rene snuhandlinger finnes. Utgang fem > 0 skriver til neste ledige plass. Utgang seks kvantiseres til −1 under −⅓, +1 over ⅓, ellers 0. Skriving skjer etter beslutningen og er synlig i neste observasjon. Fulle minner ignorerer videre skriving; ingen eksisterende verdi overskrives. Ny labyrint nullstiller minnet.

Belønningsmotoren beregner en deterministisk korteste sti og avstand til utgangen, men disse inngår aldri i observasjonen. Vegg gir −5; ny minsteavstand til utgangen gir +0,25 per rute; første besøk på en rute i stien gir +0,2; økt avstand gir −0,05; gjenbesøk gir ytterligere −0,05; utgang gir +100. Framgang og stibesøk belønnes bare én gang for å hindre gjentatt poengsanking på samme strekning. Ingen ekstra stillstandsstraff brukes. Standardgrensen er 128 handlinger. Belønningen er evalueringssignal for evolusjonstreningen, ikke input til agenten.

Trening bruker fortsatt mutasjoner og utvalg, med nye labyrinter per generasjon. Tidlige minneplasser kan være brukt oftere, men dette garanterer ikke at de lærer en stabil betydning først. Suksess alene viser heller ikke at minnet er nyttig; sammenlign senere samme vekter med minneinput slått av på et separat testsett. De første 60 generasjonene er et innledende eksperiment, ikke et bevis på lært hukommelse.

## GPU-trening med Apple Metal — 17. oktober 2026

Valgfri GPU-støtte er tilgjengelig for modellen med selvskrevet minne. Installer i et eget miljø:

```sh
python3.12 -m venv .venv-gpu
.venv-gpu/bin/python -m pip install -r requirements-gpu.txt
.venv-gpu/bin/python -m games.maze.app --resume --model games/maze/models/learned_memory_40_three_layers.json --backend mlx-gpu --generations 1000 --port 8770
```

MLX kjører nettverkslagene på Metal GPU, samlet for kandidatene og treningslabyrintene ved hvert tidssteg. Spillregler, minnelagring, mutasjoner og utvalg kjører fortsatt på CPU. Beste eksisterende modell evalueres på samme nye labyrinter som kandidatene. GPU-modus tar et CPU-opptak av den valgte modellen per generasjon; validering og avspilling bruker også CPU. UI viser valgt backend. Ingen stille fallback: manglende MLX/Metal gir feil ved oppstart. Standard `python` krever fortsatt ingen ekstra pakker.

Modellformatet og arkitekturen er uendret. GPU bruker float32 mot Pythons double; små numeriske avvik kan påvirke valg ved terskler og nesten like utganger, så identiske framtidige treningsløp garanteres ikke. På denne M3 Pro-maskinen ga en oppvarmet måling med 36 kandidater, åtte 15 × 15-labyrinter og 60 steg median 0,490 s for Python og 0,191 s for GPU (2,57× for evaluering, ikke hele treningsløpet). Poengene var identiske for kandidatene i målingen. Kjør `.venv-gpu/bin/python -m scripts.benchmark_gpu` for en ny sammenligning uten å endre modellen. Kjør testene med `.venv-gpu/bin/python -m unittest discover -s tests` for å inkludere Metal-testene.

## Fortsett til feil eller utgang — 17. oktober 2026

Aktiv modell fra generasjon 3000 bruker `until_failure: true`. Den gamle grensen på 60 steg brukes ikke i denne modusen. Første veggtreff avslutter forsøket med vanlig veggstraff; utgang avslutter med utgangsbelønning. Tilbakegang og gjenbesøk avslutter ikke i seg selv. Gjentas nøyaktig samme posisjon, retning og hele lagrede minne, avsluttes forsøket som en deterministisk løkke, med veggstraff. Nettet observerer verken poeng, besøkstellere eller stegnummer, så identisk tilstand gir samme framtidige handlinger. Endret minne teller som en annen tilstand. Regelen brukes både av CPU-avspilling og GPU-trening; GPU-batchen fortsetter til alle forsøk er ferdige. Nye forsøk kan velge `--until-failure`; eksisterende modeller bruker lagret innstilling.

## Deterministisk historikk og fem lag — nytt forsøk

`deterministic_history_v1.json` starter fra tilfeldige vekter med GPU, 500 generasjoner og 5×5-labyrinter. Ingen LSTM eller lærbar skriveport brukes. Kommando:

```sh
.venv-gpu/bin/python -m games.maze.app --deterministic-history --backend mlx-gpu --model games/maze/models/deterministic_history_v1.json --generations 500 --port 8774
# Senere: --resume og samme modellfil, uten --deterministic-history.
```

Input er dagens åtte stråleavstander, deretter åtte verdier per tidligere registrert sted i første besøksrekkefølge, til slutt nuller. Alle målinger deles på to ganger labyrintdiagonalen. Den fryste kryssdetektoren fra `junction_detector_v1` avgjør om et sted registreres; dens tidligere feilmarkeringer av enkelte blindveier kan fortsatt forekomme. Gjenkjenning bruker samme klipping og skalering som under detektorens trening. `history_detector.json` er den samme modellen eksportert til stdlib-nettet; positiv tanh i siste lag gir samme stoppsignal som sigmoid >0,5.

Hvert fysisk sted lagres én gang. Simulatorens koordinater brukes til deduplisering, men gis ikke som input. Det lagres målinger med retningen ved første registrering; både startretning og bevegelsesretning varierer. Ingen rotasjonsnormalisering gjøres. Den nåværende observasjonen registreres etter at bevegelsesvalget er beregnet, slik at den først kommer inn i historikken ved neste beslutning. Steder som allerede er registrert beholder sine opprinnelige målinger. Ingen historikk kuttes eller overskrives.

Kapasiteten er antall mulige innvendige ruter `(bredde−2)*(høyde−2)`. Det er en sikker øvre grense også med falske detektorsignaler. På 5×5 blir det ni historikkplasser og 80 inputverdier. Fem lag tolkes som inngangslag, tre skjulte lag og utgangslag, med jevn lineær reduksjon: **80 → 61 → 42 → 23 → 4**. Utgangene velger frem/tilbake/høyre/venstre. Inputen har fast størrelse på hvert labyrintnivå, og fylles gradvis under forsøket; nettstrukturen endres ikke for hvert steg.

Ved automatisk økning av labyrintstørrelsen økes historikkapasitet og alle skjulte bredder. Gamle vekter og biaser kopieres til de tilsvarende nevronene, nye forbindelser settes til null. Dette bevarer tidligere beregninger når de nye inngangene er null; videre mutasjoner kan ta de nye nevronene i bruk. Checkpoint lagrer faktisk arkitektur og nivå. Vekst utløses av det eksisterende kravet om 20 feilfrie nye forsøk på rad.

Belønningene følger det tidligere gåforsøket: +0,25 for ny minsteavstand mot utgangen, +0,2 for første besøk på skjult løsningssti, −0,05 ved økt avstand, −0,05 ved gjenbesøk, −5 ved vegg og +100 ved utgang. Ingen skjult sti eller målavstand gis som input. Forsøket fortsetter til utgang, første veggtreff eller eksakt gjentatt posisjon/retning/historikk (løkke med veggstraff). Minne nullstilles ved ny labyrint. Gamle modeller og øvrige eksperimenter er bevart.
