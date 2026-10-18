# Assistert læring fra kjente ruter

Datert 18. oktober 2026. **Datainnsamling og et første forsøk med assistert evolusjon er implementert og kjørt. Den valgte treningsregelen er bare +1/−1 for riktig/feil neste handling; se de siste avsnittene for oppsett og resultater.** Dagens API-trener velger fortsatt modeller gjennom mutasjoner og poeng fra hele forsøk. Gjeldende regler er beskrevet i [Straff, belønning og historikk](MAZE_REWARDS.md).

## Avklart startpunkt: gjenbruk den eksisterende utforskeren

Brukerens presisering 18. oktober: datageneratoren skal være den eksisterende,
belønningsbasert trente gåvarianten som finner frem sensorisk uten å bruke
historikk i bevegelsesvalget. Vi skal ikke først lage en ny tilfeldig gåalgoritme.
I den første innsamlingen ble den bevarte gåmodellen fra generasjon 3000 valgt:
`games/maze/models/junction_detector_v1/walker.json`. Den har åtte følere og
minneinnganger. Alle minneverdier og bruktmarkører settes til null før hvert
handlingsvalg. Dette er en sensorisk kjøring av de lagrede vektene, ikke dokumentasjon
på at modellen opprinnelig ble trent uten minne.

Den første datakilden blir derfor **utforskerens egne vellykkede gjennomføringer**,
ikke ruter beregnet av en løsningsalgoritme. Omtrent 30 % er den ønskede størrelsesordenen
på treffraten, ikke et allerede bekreftet måleresultat for denne kjøringen.
Alle forsøk telles når treffraten beregnes; bare de som faktisk når utgangen blir
treningsdemonstrasjoner. En bedre treffrate skal ikke kunstig reduseres til 30 %.

Under gåingen registrerer simulatoren historikkbrikkene selv om utforskeren ikke
bruker dem til styring. Sluttnettet trenes på observasjonen og historikken **før**
hver handling i de vellykkede rutene, med utforskerens handling som mål.
Punkter fra hele rutene blandes i treningen. Hele labyrinter holdes adskilt mellom
trening og test.

En handling i en vellykket rute er en demonstrasjon, ikke nødvendigvis det korteste
eller eneste riktige veivalget. Ruten kan inneholde omveier. Denne forskjellen må
beholdes i datasettet og i omtalen av «fasit» nedenfor. Beregnede løsningsruter er
fortsatt et mulig senere sammenligningsforsøk, ikke valgt første datakilde.

## Hensikten

Nettet skal slippe å bruke svært mange tilfeldige forsøk på å oppdage problemets grunnleggende struktur. Når treningssystemet allerede kjenner en løsningsrute, kan det bruke denne som fasit for hvilken handling som er riktig underveis.

Vi velger treningspunkter fra forskjellige steder på kjente ruter. Hvert eksempel inneholder observasjonen der agenten er nå, historikkbrikkene fra veien dit og fasiten for neste handling. Nettet vurderes direkte på valget ved dette punktet.

Dermed kan beslutninger fra starten, midten og slutten inngå i samme treningsomgang. Nettet trenger ikke først å mestre starten for å få øve på slutten. «Alle ledd samtidig» betyr her at eksempler fra hele ruten blandes i treningen; de samme vektene lærer av alle eksemplene.

Dette kalles veiledet læring eller imitasjonslæring når fasithandlingene brukes direkte til å justere vektene. Læreren kan være en rutealgoritme; det kreves ikke menneskelige demonstrasjoner.

## Et treningspunkt

| Del | Innhold |
| --- | --- |
| Her og nå | Fire sensorverdier: frem, høyre, bak og venstre, på de samme faste inngangene som i vanlig kjøring. |
| Historikk | Bare tidligere registrerte hjørner og forgreninger. Nyeste registrering først. |
| Minnevekting | 75 % av foregående nivå, med gulv på 25 %. Tomme plasser er null. |
| Fasit | Handlingen som fører til neste rute i den kjente løsningen. |
| Kontrollinformasjon | Kart, posisjon og retning lagres for å kunne kontrollere eksemplet. De gis ikke som ekstra input til nettet. |

Historikken skal være en faktisk mulig historikk, ikke et tilfeldig utvalg brikker. Treningssystemet spiller frem den kjente ruten med den samme simulatoren og minnelogikken som brukes ved vanlig kjøring. Det tar vare på nettets observasjon **før** hver handling.

Det bevarer også dagens regel: et nytt hjørne eller kryss registreres etter at handlingen er valgt og blir tilgjengelig som minne ved neste beslutning. Fremtidige hjørner og løsningen videre skal aldri ligge i input.

## Slik bygges og brukes eksemplene

1. La den eksisterende sensoriske utforskeren prøve mange labyrinter, og tell både vellykkede og mislykkede forsøk.
2. Behold rutene som når utgangen, med observasjon, faktisk historikk og valgt handling før hvert steg. En rutealgoritme kan senere brukes som en separat datakilde.
3. Trekk tilfeldige treningspunkter fra hele samlingen. Sørg for at korridorer, svinger og forgreninger alle får plass, slik at lange rette korridorer ikke dominerer treningen.
4. La modellen velge handling fra observasjonen og historikken alene.
5. Sammenlign med fasiten og bruk dette til læring. Bland punktene på nytt i neste omgang.

Eksempel: En rute har 30 steg. En treningsgruppe kan inneholde steg 24, 3, 17 og 9 fra denne ruten, sammen med punkter fra andre labyrinter. Hvert punkt har sin egen korrekte historikk. Nettet må ikke selv ha nådd steg 24 for å få trent på beslutningen der.

## Riktig handling og læringssignal

De to utgangene beholder dagens betydning:

| Bit | Handling |
| --- | --- |
| 00 | Bak |
| 01 | Høyre |
| 10 | Venstre |
| 11 | Frem |

Handlingene er relative til agentens retning. Alle fire innebærer et forsøk på å flytte én rute, med eventuell vending først. Fasitgeneratoren må derfor oversette neste kartposisjon til riktig relativ handling. Trening og visning skal bruke samme dekoder.

To mulige måter å bruke fasiten på må holdes tydelige:

- **Direkte veiledet trening:** Forskjellen mellom nettets to utganger og fasitbitene gir en feil som brukes til å justere vektene med gradienter. Med dagens tanh-utganger kan bit 0 representeres med målverdien −1 og bit 1 med +1. Dette krever en ny treningsmetode; dagens evolusjonstrener gjør ikke dette.
- **Assistert evolusjon:** Behold mutasjoner og kandidatvalg, men vurder kandidatene på samme samling merkede treningspunkter. Et enkelt foreslått poengsystem er +1 for helt riktig handling og −1 for feil handling, med gjennomsnittet som kandidatens poeng. Dette gir direkte tilbakemelding ved hvert punkt, men er fortsatt evolusjon, ikke gradienttrening.

Tallene over er et forslag for den assisterte øvingen. De erstatter ikke automatisk belønningene i vanlige labyrintforsøk. Riktig handling skal også måles som hele handlingen, ikke bare som andelen riktige enkeltbiter.

## Hva nettet kan vite

En kjent løsningsrute gir læreren en fasit, men garanterer ikke at agentens input inneholder nok informasjon til å utlede den. To labyrinter kan gi nøyaktig samme sensorverdier og historikk ved et kryss, mens utgangen ligger til venstre i den ene og til høyre i den andre.

Slike eksempler kan gi motstridende fasit. Dokumenter denne tvetydigheten når treningsdataene vurderes. Ingen treningsmetode kan garantere riktig valg i begge tilfeller fra identisk input. Det kan bli nødvendig å lære systematisk utforsking og retur fra blindveier i tillegg til å følge løsningsruter.

## Kontroll av det som faktisk er lært

Del labyrintene mellom trening og test **før** punktene trekkes. Punkter fra samme kart skal ikke havne på begge sider av skillet.

Mål både riktig handling på separate testpunkter og faktisk gjennomføring av hele, nye labyrinter uten hjelp. God treffprosent på isolerte punkter er ikke alene bevis på at agenten finner utgangen.

Etter den første assisterte treningen bør også tilstander fra modellens egne feil tas med: spill frem dens faktiske bevegelser, behold den faktiske historikken, og beregn veiledning fra stedet den havnet. Da kan den få øve på å komme tilbake etter feil og håndtere blindveier.

Automatisk større labyrinter skal fortsatt avgjøres av selvstendige gjennomføringer. Trening med fasit teller ikke som bestått mestringskontroll.

## Avgrensning

Den eksisterende utforskeren er brukt til innsamling som beskrevet nedenfor. Vektene i utforskeren og det eksisterende sluttnettet er ikke endret, og ingen imitasjonstrening er startet. Neste implementering må velge mellom direkte veiledet trening og assistert evolusjon, og teste at treningspunkter og historikk stemmer med simulatoren steg for steg.


## Bakgrunn fra forsøkene og AlphaStar

[Forsøksloggen](FORSOKSLOGG.md) dokumenterer forsøkene som ledet frem til dette forslaget, inkludert tilbakegang og kontroller av simulatoren. Der finnes også en kildebelagt sammenligning med AlphaStars bruk av demonstrasjoner før og under videre læring. Sammenligningen gjelder prinsippet; den er ikke en påstand om identisk treningsmetode.


## Første innsamling: 1000 forsøk

Kjørt 18. oktober 2026. Gåmodellen fra generasjon 3000 ble kjørt sensorisk på
8×8-labyrinter med 1000 nye seeds. Den valgte høyeste av sine fire opprinnelige
bevegelsesutganger. Ingen tilfeldig handlingssampling, rutefasit eller vektendring
ble lagt til. Tilfeldigheten kommer fra kart og startretning. Fireføler-historikken
ble registrert separat til sluttnettet, med dagens strenge avslutningsregler.

- **529 av 1000** forsøk nådde utgangen: **52,9 %**.
- **4989** observasjon–handling-eksempler ble lagret fra vellykkede ruter.
- Trening: **469 ruter / 4420 eksempler**.
- Separat kontrollsett: **60 ruter / 569 eksempler**.
- Forsøkene omfattet **601 forskjellige veggoppsett**, hvorav 359 hadde minst én vellykket gjennomføring.

Små kart kan gjentas selv om seedene er forskjellige. Delingen gjøres derfor etter
hash av veggoppsettet, før man vet om forsøket lykkes. Samme kart kan aldri finnes
både i trening og kontrollsettet. Mislykkede forsøk finnes i forsøksloggen, men
inngår ikke som demonstrasjoner. Hele kart, posisjoner og utforskerens råutganger
finnes som kontrollinformasjon i ruteopptakene; `train.jsonl` og `validation.jsonl`
gir sluttnettet observasjonen med fire følere og historikk, samt handling og målbit.

Alle 4989 steg ble rekonstruert etter innsamlingen. Sensorinput, historikk,
handlinger og opptaksrammer stemte. Utforskerens 80 minne-/bruktinnganger var null,
og begge kildemodellene var uendret. Treffraten gjelder dette kartsettet og denne
sensoriske kjøringen; den er ikke et målt resultat for et nytt trent sluttnett.

Datasett: `.ai-service/datasets/sensor-walker-g3000-1000-v2/`:

| Fil | Innhold |
| --- | --- |
| `manifest.json` | Modellidentitet, regler, skalering, seeds, tellerverk og status. |
| `attempts.jsonl` | Alle 1000 forsøk, inkludert de mislykkede. |
| `successful-routes.jsonl` | Vellykkede ruter med faktiske observasjoner og avspillingsrammer. |
| `train.jsonl` | Merkede steg fra treningskartene. |
| `validation.jsonl` | Merkede steg fra kontrollkartene. |
| `teacher.json`, `student-config.json` | Kopier av kildevektene og konfigurasjonen som ble brukt. |
| `audit.json` | Resultatet av rekonstruksjonskontrollen. |

Den første innsamlingsmappen uten `-v2` er et **ufullført** forsøk: den stoppet etter
964 gjennomføringer fordi samleren krevde unike veggoppsett. Den inngår ikke i
datasettet over. Den korrigerte samleren teller alle forsøk med nye seeds og holder
gjentatte kart på samme side av delingen.

Kjør på nytt med en ny output-mappe:

```sh
.venv-gpu/bin/python -m scripts.collect_successful_routes \
  --teacher games/maze/models/junction_detector_v1/walker.json \
  --student-config .ai-service/history-4rays-decay75-v1.json \
  --attempts 1000 --seed 202610180100000 \
  --output .ai-service/datasets/ny-innsamling
```

Samleren nekter å overskrive et eksisterende datasett. Tester finnes i
`tests/test_route_collection.py`. Fire tester dekker isolering av minneinput,
registrering før handling, rekonstruksjon, avvisning av feil/avbrudd og deling ved
gjentatte kart. Neste steg er å trene sluttnettet fra treningsfilen og måle både
handlingsvalg og selvstendig navigasjon på separate kart.


## Utvidet grunnmateriale: 5000 forsøk på flere størrelser

Den neste innsamlingen brukte samme sensoriske gåmodell og **1000 forsøk på hver
av 5×5, 8×8, 12×12, 15×15 og 18×18**. Størrelsene ble vekslet mellom gjennom kjøringen.

| Størrelse | Løste / forsøk | Treffrate | Merkede steg fra løste forsøk |
| --- | ---: | ---: | ---: |
| 5×5 | 516 / 1000 | 51,6 % | 2362 |
| 8×8 | 546 / 1000 | 54,6 % | 5263 |
| 12×12 | 430 / 1000 | 43,0 % | 8701 |
| 15×15 | 304 / 1000 | 30,4 % | 9478 |
| 18×18 | 283 / 1000 | 28,3 % | 10 884 |

Totalt **2079 vellykkede ruter og 36 688 eksempler**. Treningsdelen inneholder
1877 ruter / 33 546 eksempler; kontrollsettet 202 ruter / 3142 eksempler. Forsøkene
omfatter 3637 forskjellige veggoppsett. Kart som gjentas holdes alltid på samme
side av delingen, også sammenlignet med det tidligere datasettet.

Datasettet ligger i `.ai-service/datasets/sensor-walker-g3000-mixed-5000/`.
Mappens `README.md` beskriver format og reproduksjon. `manifest.json` gir tallene
per størrelse og `audit.json` dokumenterer kontrollen av alle vellykkede steg.

De flate trenings- og kontrollfilene bruker **1028 inputverdier**. Observasjonene
fra mindre kart er fylt ut med nuller, slik at nåværende sensorer og minneplasser
alltid står på samme indeks. Ruteopptakene bevarer også observasjonenes opprinnelige
lengde. Dagens 148-inngangsnett er ikke utvidet eller trent i dette arbeidet; det
må tilpasses før det kan bruke det samlede materialet. `student-config.json` er
fortsatt en kopi av oppsettet som bestemmer regler og historieskalering.

Samleren støtter nå `--sizes 5 8 12 15 18`. Fem tester kontrollerer blant annet
fordeling mellom størrelser og nullutfylling uten å endre den opprinnelige
observasjonen. Alle 36 688 vellykkede steg ble rekonstruert med samsvar i handling,
input, minne og rammer. De lagrede kildevektene er uendret. Dette er grunnmateriale
for videre læring, ikke et målt resultat fra et nytt sluttnett.


## Valgt treningsregel: bare neste handling i den vellykkede ruten

Presisert 18. oktober 2026: **Ingenting annet gir straff eller belønning i denne
treningsmodusen.** Hver handling sammenlignes med handlingen som faktisk ble tatt
fra det samme punktet i den vellykkede ruten:

| Nettets valg | Belønning |
| --- | ---: |
| Samme handling som i ruten | +1 |
| En annen handling | −1 |

Det gis ingen delpoeng for én riktig bit. Vegger, gjenbesøk, avstand, nye ruter,
hjørner og utgang gir ingen tillegg eller trekk. Treningsløkken kjører ikke en
labyrintepisode; den vurderer bare lagrede observasjoner og neste handling.
Gamle episodepoeng og belønningsfelt fra datainnsamlingen leses ikke som fitness.

Vi bruker **assistert evolusjon**: behold den eksisterende modellen med historikk,
lag muterte kandidater og velg den med høyest gjennomsnitt av +1/−1 på de samme
punktene. Dette er ikke gradienttrening. Poengene er direkte tilbakemelding på
handlingsvalget ved hvert punkt, ikke en sum fra en ny gjennomspilling av ruten.

Størrelsene fordeles omtrent likt i hver treningsgruppe. Innen hver størrelse
velges en tilfeldig vellykket treningsrute og et tilfeldig steg. Hele historikken
før dette steget gis til nettet samtidig. Vi bygger ikke minnet gradvis under
treningen, og vi lar ikke modellens tidligere feil hindre trening på senere steg.
Historikken består fortsatt bare av de registrerte hjørnene og forgreningene,
med samme demping og nullutfylling som ved innsamlingen.

Det første forsøket viderefører generasjon 7000. Bare inngangsbredden økes fra
148 til 1028, med nullvekter på nye forbindelser. De fem skjulte lagene og tidligere
vekter beholdes, slik at normaliseringen av skjulte lag ikke endres. Ubrukte nye
minneinnganger forblir fryst frem til de forekommer i en faktisk trukket observasjon.

Oppsett: 200 generasjoner, fire kandidater, 128 rutepunkter per generasjon,
mutasjonssigma 0,03. De 3142 punktene fra kontrollkartene måles før og etter,
men brukes verken til kandidatvalg eller aktivering av minnevekter. Resultatet
måles som andel riktige **neste handlinger**, ikke som løste hele labyrinter.

Implementasjon: `scripts/train_route_matches.py`. Resultat, komplette trekninger
av rutepunkter og kilde-/sluttmodell lagres i en ny forsøksmappe. Hver generasjons
logg identifiserer rute, steg, faktisk minnelengde, fasithandling og kandidatpoeng.
Dermed kan man kontrollere at et sent rutepunkt faktisk hadde historikken sin.

```sh
.venv-gpu/bin/python -m scripts.train_route_matches \
  --dataset .ai-service/datasets/sensor-walker-g3000-mixed-5000 \
  --source-network history-4rays-decay75-v1 \
  --rounds 200 --batch-size 128 --population 4 --sigma 0.03 \
  --output .ai-service/nytt-rutepunkt-forsok
```


## Første resultat med bare rutepunkt-belønning

200 nye generasjoner er gjennomført fra historikkmodellen ved generasjon 7000.
På de 3142 separate kontrollpunktene økte riktig neste handling fra **2630 / 83,70 %**
til **2722 / 86,63 %**. Det er 92 flere riktige valg, en økning på 2,93 prosentpoeng.
Dette gjelder handlinger fra gitt historikk, ikke selvstendig gjennomføring av hele
labyrinter. Konstant «frem» ville gitt 66,17 % på samme kontrollsett.

Modellen bruker 1028 innganger, fem uendrede skjulte lag og to bevegelsesutganger.
Den lagres under `.ai-service/route-match-200-v1/final.json` og API-identiteten
`route-match-c4ce804264d5`. Kildemodellen er bevart. Kjøringen brukte cirka 87 sekunder
inkludert før-/ettermåling. Sluttmodellen er på generasjon 7200; de siste 200 er
trent med det nye målet, de foregående 7000 med tidligere regler.

Alle trukne punkter og deres historikk er kontrollert mot treningsrutene. Siste
kandidatutvalg ble rekonstruert med nøyaktig samsvar i fitness og vinnervekter.
Forsøksmappens `README.md`, `state.json`, `rounds.jsonl` og `audit.json` gir detaljene.
Kontrollsettet inneholder bare ett bakover-eksempel; et godt samlet resultat er
ikke alene bevis på mestring av alle handlingstyper.
