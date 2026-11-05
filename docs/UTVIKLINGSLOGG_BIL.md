# Utviklingslogg: hvordan bilforsøket faktisk ble til

Sist oppdatert 5. november 2026. Dette er en kronologisk logg over beslutninger,
endringer og resultater fra arbeidet med bilspillet. Første del er rekonstruert
fra samtalen og eksisterende forsøksnotater; rekkefølgen er dokumentert, men vi
har ikke satt oppdiktede klokkeslett på hvert forslag. Arbeidet startet
4. november og fortsatte 5. november 2026.

Prosjekteieren har formulert målene, foreslått læringshypotesene og korrigert
oppsettet underveis. Codex har skrevet kode og dokumentasjon, kjørt tester og
målinger, og foreslått tekniske løsninger og kontrollforsøk. Dette er ikke et
prosjekt der én innledende bestilling ga en ferdig løsning. Både problemstillingen
og treningsmetoden er endret gjennom mange konkrete vurderinger. Flere av
metodene som er implementert korrekt, har foreløpig gitt dårligere kjøring.

[Detaljert forsøksoppsett](BIL_HUKOMMELSE.md) ·
[Arkiverte målinger og innstillinger](experiments/2026-11-05-results.json)

## 01 — Hukommelse ble delt i to separate spørsmål

**Prosjekteierens forslag:** Først en vanskeligere bane med begrenset synsfelt
og saktere biler. Deretter undersøke om modellen kan huske kommende svinger og
forbedre rundetidene. Fargede banesegmenter skulle gi gjenkjennelige kjennetegn.

**Viktig korrigering fra prosjekteieren:** Fargeavlesing hører til del 2. Del 1
skal først kunne prøves med eksisterende vekter. Det var derfor ikke riktig å
legge alle nye sensorinput inn i det første forsøket.

**Status:** Nye baner og kjøretrening er prøvd. Veggfarger som input og minne
under kjøring er fortsatt hypoteser. En historikkø brukt under trening er ikke
i seg selv hukommelse tilgjengelig for bilen når den senere kjører.

## 02 — Fra oval til åttetall, høyde og trafikk

**Prosjekteierens forslag:** En baneklasse, minst ti ganger lengre bane, mange
svinger begge veier, og et kryss med veier på forskjellige høyder. Fem biler
skulle kjøre samme vei med omtrent ±20 % hastighetsforskjell.

**Presisering:** Bilene skulle ikke starte på samme sted.

**Codex gjennomførte:** Felles banegenerator, xyz-geometri, åttetallsbane med
overpass og fem spredte startposisjoner med fart 80, 90, 100, 110 og 120 %.
Høyde må brukes ved sensorer og kollisjoner, ikke bare tegnes i bildet.

**Senere endring fra prosjekteieren:** Banen viste seg å være for stor for
hyppige møter. Formen skulle beholdes, bredden økes og banen krympes til en
fjerdedel. Det opprinnelige størrelseskravet ble dermed erstattet etter utprøving.

## 03 — Egen treningsbane og mer informasjon om andre biler

**Prosjekteierens forslag:** En bane med raske venstre-/høyresvinger og kjegler.
Bilene måtte bli flinkere til å observere hverandre. Radaren skulle bli omtrent
tre ganger større og gi avstand og høyre-/venstre-posisjon.

**Codex gjennomførte:** Treningsbane med 11 kjegler, radarrekkevidde 540 og
separat nærhet og sideposisjon. Denne sensorendringen krevde et eget forsøk med
nye vekter. Gamle modeller ble beholdt.

**Læringsregel på dette stadiet:** Evolusjon med 36 kandidater per generasjon og
seks eliter. Alle fem biler brukte samme kandidatnettverk. Nærhet og kollisjoner
ga straff; det var ingen egen fremdriftspremie. En generasjon var dermed ikke
bare fem biler eller fem handlinger.

## 04 — Visualisering og faktisk treningshastighet

**Prosjekteierens spørsmål og beslutninger:** Kan Rust tegne bildet? Bør GPU
brukes med en gang? Videoene bør vise hele banen ovenfra, så alle bilene synes.
Trening av 1000 generasjoner skal kjøres uten visning.

**Codex gjennomførte:** Rust/WebAssembly/WebGPU-visning, videoklipp og
ovenfra-visning som standard for treningsopptak. Senere ble de visuelle veggene
senket fra 26 til 2 høydeenheter etter ønske om lave kanter. Kantfølerne beholdt
veigrensen som sensorgrunnlag.

**Måling som korrigerte forventningen:** Å flytte bare nettverket til Rust ga
omtrent 4 % raskere total kjøring i en kort måling. Det var ikke grunnlag for å
si at hele simuleringen allerede kjørte raskt i Rust.

## 05 — Radaren fikk veggskjerming, og så ble det valgt bort

**Prosjekteierens innvending:** Radar gjennom vegger kan registrere irrelevante
objekter på andre deler av banen.

**Codex gjennomførte:** Siktsjekk mot veigrensen og omstart med nye vekter.

**Ny beslutning fra prosjekteieren:** Forenkle geometrien til en kjegle foran
bilen uten veggskjerming. Rapporter avstand, sideposisjon og hastighet til
nærmeste objekt.

**Codex gjennomførte:** 120° kjegle med rekkevidde 540, objektfart og relativ
tilnærmingsfart, i tillegg til avstand og sideposisjon. Sammen med syv kantfølere
ble dette 11 input. Treningsforsøket ble startet på nytt. Dette er to forskjellige
sensoroppsett; resultater fra dem skal ikke beskrives som én uendret treningsserie.

## 06 — Måling lokaliserte flaskehalsen

**Prosjekteierens spørsmål:** Er fysikken fortsatt flaskehalsen, og må den også
skrives i Rust? Målet var omtrent en sjettedel av kjøretiden.

**Codex målte:** Kantfølerne tok omtrent 87 % av tiden i en profilert kortkjøring;
kjegleradaren omtrent 2,5 %. Problemet var gjentatte avstandsberegninger mot
veien, ikke avansert kjøredynamikk.

**Endring og kontroll:** Veiprojeksjon, kandidatcache og kantstråler ble flyttet
til Rust. Tre 500-stegs evalueringer ga i snitt 3,33 s før og 0,195 s etter,
omtrent 17× raskere. Poengsum, distanse og omstarter var identiske. Geometri og
sensorverdier ble også sammenlignet på alle fire banetypene.

**Begrensning:** Dette er en kort ytelsesmåling, ikke en garanti for samme
akselerasjon gjennom hele treningen. Den nye 1000-generasjoners kjøringen
fortsatte som evolusjonsforsøket og ble holdt separat fra senere læringspiloter.

## 07 — Prosjekteieren utfordret hvordan straffen brukes

**Prosjekteierens spørsmål:** Straffes bare selve kollisjonsøyeblikket, eller
også handlingene som skapte situasjonen? Det kan allerede være for sent å
unngå sammenstøtet når bilen faktisk treffer noe.

**Avklaring fra Codex:** Evolusjonen brukte samlet poengsum over hele forsøket.
Den oppdaterte ikke bestemte tidligere handlinger. Å flytte samme straff mellom
tidspunkter uten å endre læringsregelen ville ikke endret totalsummen.

**Konsekvens:** Forslaget om en kø var ikke bare en loggendring. Det krevde en
ny måte å oppdatere vektene på, og dermed et separat eksperiment.

## 08 — Fra halvering bakover til hovedvekt før kollisjonen

**Prosjekteierens første hypotese:** Lagre input/output og fordel straffen med
halvering bakover, fra kollisjonen og to steg av gangen ut til 16 steg.

**Videre presisering:** En kø på 100 steg per bil. Ved objekttreff bør historikken
knyttes til objektet bilen faktisk observerte. Handlingene 3, 6, 12 og 24 steg
før sammenstøtet kan være viktigere enn handlingen i selve kollisjonsøyeblikket.
Størst påvirkning ved 3 og 6, halvparten så mye ved 12 og 24.

**Teknisk forslag fra Codex, deretter prøvd:** 10/30/30/15/15 % ved
0/3/6/12/24 steg, jevnet over nabosteg. Objektidentitet, livnummer og tømming av
historikken ved omstart skulle hindre at straffen traff feil bil eller forrige
forsøk. Policygradient med en lært tilstandsbaseline ble brukt til å endre
handlingssannsynlighetene. Det er en heuristisk ansvarsfordeling, ikke et bevis
på hvilke handlinger som forårsaket kollisjonen, og ikke en full Bellman-critic.

**Resultat:** To varianter fikk 20 treningsforsøk fra samme generasjon-55-modell.
I etterfølgende deterministisk evaluering over 2542 steg og tre startplasseringer:

| Variant | Kollisjoner per 1000 verdenheter |
| --- | ---: |
| Uendret startmodell | 0,685 |
| Forsinket straff | 1,187 |
| Bare umiddelbar straff | 1,755 |

Forsinket straff slo kontrollvarianten, men begge forverret startmodellen.
Piloten viste derfor ikke at den nye metoden var bedre enn eksisterende kjøring.
Én kort kjøring med én seed avgjør heller ikke om ideen kan fungere med andre
innstillinger eller mer trening.

## 09 — Positiv belønning og evolusjon ble eksplisitte krav

**Prosjekteierens neste forslag:** Kjør til kollisjon, straff de siste 50
input/output-handlingene, la fem biler lære uavhengig, og velg den beste etter
flere treningsforsøk. Evolusjon måtte være en del av metoden.

**Viktig presisering fra prosjekteieren:** Det skal ikke bare være straff.
Kollisjonsfri kjøring må premieres.

**Codex gjennomførte:** Hvert sikkert steg gir 0,02 poeng, fremdrift gir 0,05 per
verdenhet, og kollisjon gir totalt 50 i straff jevnt fordelt på inntil 50 siste
handlinger. Hver bil har egne vekter, optimizer, tilfeldighetsgenerator og kø.
Vektene oppdateres etter forsøket. Første kollisjon eller steggrensen avslutter
forsøket. Vinneren kan danne én uendret og fire muterte kopier i neste generasjon.

**Kontrolltiltak foreslått av Codex:** Behold den uendrede forelderen som kandidat,
så gode vekter ikke går tapt bare fordi alle nye varianter er dårligere. Test alle
kandidater i alle bilposisjoner og hastigheter med faste motstandere.

**Første tekniske pilot:** 30 forsøk per bil, én test per bilposisjon, to
generasjoner. Forelderen vant begge. Dette var ikke sluttprotokollen.

## 10 — Prosjekteieren skjerpet protokollen til 100/20

**Presisering fra prosjekteieren:** Øk til 100 treningsforsøk per bil. Test
deretter alle nettverk på alle bilene i 20 runder, og la det beste overleve.

**Gjennomført tolkning, uttrykkelig meldt tilbake:** 20 felles testscenarier i
hver av de fem bilposisjonene, altså 100 testforsøk per nettverk. Ingen læring
eller tilfeldig utforskning under testen. De fem nye nettverkene og forelderen
møter samme oppsett. Vinneren bestemmes av samlet testpoengsum.

**Resultat fra én full generasjon:**

| Kandidat | Samlet testpoeng | Kollisjoner / 100 tester |
| --- | ---: | ---: |
| Uendret forelder | 5699,41 | 84 |
| Nytt nettverk 1 | −204,60 | 100 |
| Nytt nettverk 2 | 415,07 | 100 |
| Nytt nettverk 3 | 1614,58 | 98 |
| Nytt nettverk 4 | −1388,66 | 100 |
| Nytt nettverk 5 | 3879,61 | 100 |

Forelderen vant og ble beholdt. Den nye kombinasjonen ga ingen forbedring i denne
generasjonen. 63 programtester passerte, men det betyr at den kontrollerte koden
oppfører seg som forventet — det dokumenterer ikke at læringsmetoden lykkes.
Testpoengene her kan ikke sammenlignes direkte med evolusjonens gamle poengsum
eller forrige pilots kollisjonsrate; belønning og evalueringsprotokoll er forskjellige.

## 11 — Utvidelse til 30 generasjoner med samme hybridmetode

**5. november 2026 — prosjekteierens beslutning:** Kjør 30 generasjoner på det
nye oppsettet, slik at vurderingen ikke bare bygger på én kort generasjon.

**Startet av Codex:** En separat bakgrunnskjøring med fem uavhengige lærere,
100 treningsforsøk per bil per generasjon og 20 testscenarier i hver av de fem
bilposisjonene per nettverk. Steggrensen er fortsatt 1000. Belønning for trygg
kjøring og fremdrift, jevn straff på de siste 50 handlingene, mutasjon og vern
av forelderen beholdes uendret.

Startvektene er vinneren fra 100/20-piloten (den uendrede forelderen). Kjøringen
har 30 nye generasjoner, nummerert 1–30 lokalt, med seed 20261106. Nye optimizere
og tilfeldighetssekvenser opprettes; dette er en ny kjøring fra lagrede vekter,
ikke en nøyaktig gjenopptakelse av pilotens optimizer. Alle kandidater testes
på de samme seedede scenariene innenfor den nye kjøringen.

**Status ved oppføring:** Startet, ingen sluttresultater ennå. Forrige pilot
brukte omtrent 136 sekunder for én generasjon inkludert innledende evaluering.
Dette er bare et utgangspunkt for tidsanslag; resultat og varighet for 30
generasjoner er ikke kjent. Den opprinnelige evolusjonskjøringen fortsetter
separat. Ny logg og checkpoints: `.ai-service/car-hybrid-100train-20test-30generations/`.

## 12 — Flere kjegler og smalere radar uten å forkaste vektene

**5. november 2026 — prosjekteierens endringer:** Tredoble antallet kjegler og
behold det som allerede er lært. Deretter halvere bredden på radarkjeglen.

**Gjennomført:** De opprinnelige 11 banekjeglene beholdes, og to nye plasseres
i hvert mellomrom langs banen: 33 totalt. Tester kontrollerer klaring til
veikant, andre kjegler og startposisjoner. Radaren er innsnevret fra 120° til
60° total åpningsvinkel; rekkevidden 540 og de 11 nettverksinputene beholdes.
Dette tolker «halv bredde» som halv åpningsvinkel, ikke halve kjegleradiusen på
banen. Veikjeglene beholder størrelse 6 verdenheter i radius.

**Overgang:** Den aktive hybridgenerasjonen får fullføre. Siste vinnervekter
brukes til resten av målet på 30 generasjoner, med fortsatt generasjonsnummer
og en ny separat logg. Optimizerne opprettes på nytt ved generasjonsgrensen,
slik de også gjør mellom vanlige hybridgenerasjoner. Ny seed er 20261107.
Resultater før og etter endringen skal holdes adskilt; flere hindringer og
smalere radar endrer oppgaven. Den gamle evolusjonskjøringen med 11 kjegler
beholdes som separat referanse.

**Video:** Prosjekteieren påpekte at README bare hadde fått et stillbilde og
fortsatt viste gamle filmer. Et nytt faktisk ovenfra-opptak viser derfor
33 kjegler og 60° radar med lagrede vekter fra generasjon 8, som ennå var trent
med 11 kjegler og 120° radar. Opptaket er en demonstrasjon av overgangen, ikke
et resultat fra ferdig trening i det nye oppsettet.

## 13 — Fire radarobjekter og utvidelse av det trente nettet

**5. november 2026 — prosjekteierens hypotese:** Nærmeste objekt alene gir for
lite informasjon. Radaren skal gi de fire nærmeste objektene, både kjegler og
biler. Manglende objekter skal gi nuller. Prosjekteieren presiserte at det
allerede trente nettet bør brukes og utvides.

**Gjennomført:** Ny inputmodus `cone4` med fire objekter sortert etter avstand
til overflaten. Hver plass gir nærhet, signert sideposisjon, objektfart og
relativ tilnærmingsfart. Tomme plasser gir fire nuller. De syv kantfølerne er
uendret: totalt 7 + 4 × 4 = 23 input, mot tidligere 11. Kjeglens vinkel 60°,
rekkevidde 540 og banens 33 kjegler beholdes.

**Bevaring av læring:** De gamle 11 inputene står først i samme rekkefølge.
Tolv nye input kobles inn med nullvekter; alle gamle vekter og bias beholdes.
En test bekrefter identisk styring for samme opprinnelige input selv når de
nye inputene varierer. Det nye nettet kan deretter lære vekter for objekt
nummer 2–4. Dette er en kontrollert utvidelse, ikke trening fra tilfeldige vekter.
Overgangen ble gjennomført etter fullført generasjon 12. Generasjon 13–30
kjører med det utvidede nettet, ny seed 20261108 og de bevarte vinnervektene.
Den faktiske migrerte startmodellen ga identiske output som originalen på
100 testvektorer; dette kommer i tillegg til regresjonstestene.
Tilstand: `.ai-service/car-hybrid-radar4-transition.json`; ny kjøring:
`.ai-service/car-hybrid-four-targets/`.

**Ytterligere presisering fra prosjekteieren:** Biler som ikke har krasjet må
få fortsette selv om andre krasjer. Dette var allerede implementert i
hybridforsøket: hver bil kjører til egen kollisjon eller steggrensen 1000.
De andre stoppes ikke av dens kollisjon. En test dekker at bil 1 krasjer ved
første steg mens de fire andre fortsetter. En krasjet bil starter først igjen
ved neste felles treningsforsøk; historikk og oppdateringer er individuelle.

## 14 — Fortsett fra samme sted, og behold historikken

**5. november 2026 — prosjekteierens innvending:** Om bilen settes tilbake til
start etter hver vektoppdatering, kan den få for mye trening på samme segment.
Presiseringen var at en bil som **ikke har krasjet** skal fortsette fra samme
sted, og at historikken skal kunne bygges videre fra forrige treningsdel.

**Endring:** Overlevende biler beholder posisjon, høyde, retning, fart og
fremdrift mellom treningsdeler og mellom hybridgenerasjoner i den aktive
kjøringen. Etter maksimalt 1000 steg oppdateres nettverket, og bilen fortsetter.
Krasjede biler håndteres som før: de avslutter sin treningsdel og starter ved
en ledig opprinnelig startplass i neste del. En krasj stopper ikke de andre.
Tester som avgjør generasjonsvinneren bruker fortsatt standardiserte starter;
disse endrer ikke de lagrede treningsposisjonene.

**Historikk:** Hver bil beholder sine siste 50 input/output med sammenhengende
stegnummer over vektoppdateringer. En kollisjon kan derfor fordele straff på
handlinger fra forrige del. Historikken tømmes ved krasj. Allerede innlært
belønning markeres som behandlet og telles ikke på nytt. Nye negative bidrag
fra en senere kollisjon behandles separat.

**Teknisk valg fra Codex:** Tidligere handlinger ble valgt med eldre vekter.
Derfor lagres også den opprinnelige utforskningsverdien og forventningen til
handlingen. For ny straff på en allerede behandlet handling beregnes gradienten
på nytt med gjeldende nettverk, med sannsynlighetsforhold begrenset oppad til 2.
Dette er en begrenset importance-vektet heuristikk, ikke en garanti for korrekt
årsaksfordeling eller stabil læring. Den samme behandlingen brukes når en
bil får nye vinner-/mutasjonsvekter ved generasjonsbyttet.

**Kontroll:** 70 biltester passerer. Nye tester dekker uendret posisjon/retning/
fart mellom deler, videreføring av historikk, straff over en oppdateringsgrense
og at positiv belønning ikke læres to ganger. En kort kjøring over to
generasjoner bekrefter at oppdatering, utvelgelse og videreføring kjører sammen.
Det er ikke dokumentert en læringsforbedring for denne endringen ennå.

**Overgang:** Kjøringen byttet etter fullført generasjon 15 med bevarte
vinnervekter og fortsetter generasjon 16–30. Startvektene er kontrollert
identiske. Ny seed 20261109. Fra prosessbyttet opprettes nye
treningsposisjoner og ny historikk; kontinuiteten gjelder videre innenfor den
nye prosessen. Full gjenopptakelse av bilposisjon, historikk og optimizer etter
prosessavbrudd er ikke implementert. Overgangsstatus:
`.ai-service/car-hybrid-continuous-transition.json`; ny logg og checkpoints:
`.ai-service/car-hybrid-continuous/`.

## 15 — Avgrens til fem generasjoner før ny vurdering

**5. november 2026 — prosjekteierens beslutning:** Gi den nye metoden fem
 generasjoner, og vurder deretter å starte fra nye vekter fordi radaren er
 endret. Dette tolkes som generasjon 16–20, de første fem generasjonene med
 sammenhengende kjøring og historikk. Generasjon 16–18 var ferdige da grensen
 ble satt.

**Tiltak fra Codex:** En separat stoppkontroll venter til generasjon 20 er
 ferdig evaluert og vinneren er lagret, og stopper deretter hybridprosessen.
 Opprinnelig mål 30 er dermed erstattet av en vurderingsgrense på 20 for denne
 kjøringen. Vinnervekter og resultater beholdes. Oppstart med tilfeldige vekter
 er **ikke** bestilt ennå; det er et mulig neste forsøk som skal vurderes ut
 fra resultatene. Den separate evolusjonsreferansen omfattes ikke av stoppen.
 Kontroll og femgenerasjoners resultatoversikt lagres i
 `.ai-service/car-hybrid-continuous/stop-control.json`.

## 16 — Brems, ny initialisering og relativ fart i radaren

**5. november 2026 — prosjekteierens forslag:** Bilen trenger en brems som kan
redusere farten 0–50 %. Når bilen bremser, skal den få mindre fremdriftspremie.
Prosjekteieren bestemte at dette forsøket skal starte på nytt med nye vekter,
og presiserte at brems må inngå i historikken og at radarhastighet må være
relativ til bilen som måler, ikke til bakken.

**Gjennomført:** Ny arkitektur 23 → 8 → 8 → 2. Første output styrer, andre
output omformes fra tanh-området til brems i [0,1]. Faktisk fart er normalfart ×
(1 − 0,5 × brems). Normalfarten har fortsatt bilens individuelle faktor
80–120 %. Bremsingen er direkte fartsregulering i denne enkle modellen, uten
forsinkelse, gir eller akselerasjonsfysikk. Bremsekommando, latent utforskning
og handlingssannsynlighet lagres sammen med styringen i hver erfaring.
Begge outputhodene lærer av belønning og historisk kollisjonsstraff; historikk
som krysser en oppdatering bruker sannsynligheten for den samlede handlingen.

Fremdriftspremien er fortsatt 0,05 per faktisk verdenhet. Halv fart gir dermed
omtrent halv fremdriftspremie per steg på samme rette strekning. Den separate
premien 0,02 for et kollisjonsfritt steg beholdes. Ingen ekstra vilkårlig
bremsestraff er lagt til.

**Radarens nye betydning:** Hvert av de fire objektene gir nærhet,
sideposisjon, relativ fart langs bilens kjøreretning og relativ tilnærmingsfart
langs siktlinjen. Begge fartene bruker forskjellen mellom de to faktiske
hastighetsvektorene etter forrige bevegelsessteg. Negativ langsgående relativ
fart betyr at målet sakker akterut; positiv tilnærmingsfart betyr at avstanden
minker. Like hastigheter i samme retning gir null. En stillestående kjegle
har negativ relativ fart sett fra bilen, ikke null. Normaliseringen av begge
fartsinputene er /7,2 med avgrensning til ±1. Manglende objekter gir fortsatt
nuller. Ny modus/version: `cone4relative` / `seven_rays_four_relative_targets_v6`.
De gamle inputmodusene beholdes for korrekt tolkning av eldre modeller.

**Forsøksrekkefølge:** Den første korte bremseoppstarten brukte fremdeles ett
absolutt fartsinput i tillegg til tilnærmingsfart. Etter prosjekteierens
presisering ble den avsluttet og merket som erstattet. Den korrigerte kjøringen
startet fra nye tilfeldige vekter med seed 20261110; ingen tidligere trente
vekter ble brukt. «Nullstille» betyr her ny tilfeldig initialisering, ikke
identiske nuller i alle nevroner. Gamle modeller beholdes som referanser.

**Nytt budsjett:** Fem generasjoner som første vurderingspunkt, med 100
treningsforsøk per bil og 20 tester i hver bilposisjon per nettverk, steggrense
1000, fem uavhengige lærere, 33 kjegler og 60° radar. Sammenhengende posisjon
og historikk beholdes for biler som ikke krasjer. Evalueringene har faste
starter og ingen læring. Nye kjøredata:
`.ai-service/car-brake-relative-fresh-5generations/`.

**Kontroll:** 77 biltester passerer, inkludert 0/25/50 % faktisk fartsreduksjon,
relativ fart ved lik hastighet og ved bremsing, retning/rotasjon, stasjonære
kjegler, gradienter for begge output mot numerisk differensiering, og
kollisjonsstraff på begge handlingene over en oppdateringsgrense. En kort
kjøring gjennom to generasjoner er også fullført. Ingen læringsgevinst er
rapportert ennå for det nye bremseforsøket.

## 17 — Resultat etter fem generasjoner med brems

**5. november 2026 — målt oppfølging:** Forsøket fra tilfeldige vekter er ferdig
etter fem generasjoner og omtrent 6 minutter og 14 sekunder. Det stoppet som
planlagt. Et nytrent nettverk slo forelderen i hver generasjon.

| Generasjon | Testpoeng | Kollisjoner / 100 tester | Samlet distanse |
| --- | ---: | ---: | ---: |
| Tilfeldig startmodell | −3473,05 | 100 | 26 346 |
| 1 | −3428,06 | 100 | 27 048 |
| 2 | −3068,61 | 100 | 33 039 |
| 3 | −2669,35 | 100 | 39 957 |
| 4 | −2629,15 | 100 | 40 577 |
| 5 | −2595,10 | 100 | 41 176 |

Distansen før kollisjon økte fra omtrent 263 til 412 verdenheter per test,
omtrent 56 %. Alle 100 testforsøk endte likevel i kollisjon, også etter
treningen. De to ekstra startforskyvningene hadde også fem kollisjoner hver.
Dette viser lengre kjøring og bedre poengsum, ikke kollisjonsfri eller stabil
kjøring. Forsøket isolerer ikke effekten av brems fra øvrig læring; det gir
ikke grunnlag for å si at brems alene forårsaket forbedringen. Resultat og
oppsett er arkivert i [resultatfilen](experiments/2026-11-05-braking-results.json).
Ingen videre trening er startet automatisk etter de fem generasjonene.

## 18 — To ekstra skjulte lag og 100 generasjoner fra nye vekter

**5. november 2026 — prosjekteierens forslag og presiseringer:** Prøv minst ett,
gjerne to ekstra lag siden andre beregninger tidligere tok mest tid. Start på
nytt og øk treningsbudsjettet. Budsjettet ble først presisert til 20, deretter
til **100 generasjoner**, med ønske om et tidsanslag mens kjøringen går uten
visning.

**Codex sitt konkrete valg:** Fire skjulte lag med åtte nevroner hver:
23 → 8 → 8 → 8 → 8 → 2, mot tidligere 23 → 8 → 8 → 2. Antall trenbare
vekter og bias øker fra 282 til 426. Baseline-nettverket får tilsvarende fire
skjulte lag, men fortsatt én verdioutput. `--hidden` gjør dybden konfigurerbar.
Bremseoutput, relative radarinput, 33 kjegler, 60° radar, belønningsregler,
sammenhengende kjøring og 50-stegs historikk beholdes.

**Ny kjøring:** 100 generasjoner fra tilfeldige vekter med seed 20261110,
100 treningsforsøk per bil og 20 tester i hver bilposisjon per nettverk.
Den korte 20-generasjoners oppstarten ble avsluttet da budsjettet ble økt;
den nye kjøringen bruker samme initialiseringsseed og nye loggfiler. Gamle
modeller og oppstartsloggen er beholdt. Ingen gamle trente vekter brukes i
100-generasjoners kjøringen.

**Kontroll:** 78 biltester passerer, inkludert numerisk kontroll av gradienter
gjennom fire skjulte lag og historisk straff på begge output. En kort kjøring
gjennom to generasjoner med den dypere arkitekturen er fullført. Dette beviser
ikke at flere lag gir bedre kjøring. Både kapasitet og treningsbudsjett er endret;
resultater bør også sammenlignes ved likt antall generasjoner.

**Tid og observasjon:** Den tidligere femgenerasjoners kjøringen med to skjulte
lag tok omtrent 374 sekunder. Det er ikke tilstrekkelig som eksakt anslag for
det dypere nettet: kjøringer kan vare lenger når bilene overlever lenger, og
policygradientberegningen er en annen arbeidslast enn den tidligere profilerte
evolusjonen. Første fullførte generasjon i den korte oppstarten med samme dype nett tok
62,3 sekunder inkludert innledende evaluering. Lineært tilsvarer det omtrent
1 time og 45 minutter for 100, men anslaget settes foreløpig til 2–4 timer
fordi økt overlevelse kan gi lengre forsøk. Fremdrift og faktisk tid må leses
fra den nye kjøringens logger.

Ny mappe: `.ai-service/car-brake-deep-100generations/`.
Prosessinfo: `.ai-service/car-brake-deep-100generations-process.json`.
Kjøringen lagrer kandidater og vinner etter hver generasjon og skriver
`complete.json` når alle 100 er ferdige. Start er ikke et ferdig læringsresultat.

## 19 — Automatisk forbedringslogg per generasjon

**5. november 2026 — prosjekteierens ønske:** Loggfør hvor mye forbedring hver
generasjon gir, ikke bare den siste beste poengsummen.

**Gjennomført:** `scripts/log_car_generation_progress.py` leser eksisterende
målinger uten å endre eller starte treningen på nytt. En separat prosess
oppdaterer [tabellen](experiments/deep-100-generation-progress.md) og
[CSV-filen](experiments/deep-100-generation-progress.csv) lokalt hvert tiende
sekund ved nye data. Kun fullførte generasjoner føres. Prosessen avslutter når
treningen er ferdig eller treningsprosessen avsluttes.

Loggen viser valgt vinner, testpoeng og poengendring, gjennomsnittlig distanse
per test, distanseendring, kollisjoner, antall tester uten krasj og endring fra
startmodellen. Resultater fra de ekstra startforskyvningene står separat.
Distanse per test er ikke nødvendigvis distanse til krasj når bilen når
steggrensen. Poengforbedring og kollisjonsreduksjon holdes adskilt. GitHub får
ikke automatisk nye tall uten push. En test dekker valg av vinner, fortegn,
uendrede resultater og utelatelse av uferdige generasjoner.

## 20 — Trening uten løpende visualisering

**5. november 2026 — prosjekteierens presisering:** Ressursene skal brukes til
trening; mange forsøk må gjennomføres mellom visualiseringene.

**Kontroll:** Den aktive 100-generasjoners hybridprosessen kjører allerede uten
webserver, rendering, videoopptak eller avspillingspauser. Også testkjøringene
mellom generasjonene beregnes uten bilder. Generasjonsloggen leser lagrede tall
og lager tekst/CSV. Den separate avspillingen som tidligere ble åpnet etter
ønske om å se modellen, var fortsatt aktiv og er nå stoppet.

Videre visninger skal være korte, separate avspillinger av lagrede modeller ved
forespørsel, ikke en kontinuerlig del av treningsløkken. Treningen ble ikke
stoppet eller startet på nytt ved denne endringen.

## 21 — Asynkron rotasjon av nettverk mellom bilene

**5. november 2026 — prosjekteierens forklaring og forslag:** Flate generasjoner
kunne skyldes at forelderen stadig vant. Nettverkene bør trene på forskjellige
biler og hastigheter, ikke være låst til hver sin bil. Ved avsluttet kjøring
skal bilen plukke neste nettverk fra en ringkø, uavhengig av når andre stopper.
Vinneren skal velges blant nettverkene som faktisk har trent.

**Gjennomført:** `--rotate --trained-only`. De fem nettverkene tildeles i
rullerende rekkefølge ved hver nye kjøring. Et nettverk får nøyaktig 100
avsluttede treningskjøringer per generasjon. Når flere biler avslutter samtidig,
roteres også rekkefølgen de får tildeling i, slik at synkron avslutning ikke
låser samme nettverk til samme bil. Fordelingen av kjøringer per nettverk og
bil lagres som en 5×5-matrise. Ringkøen gir ikke i seg selv garanti for nøyaktig
like mange kjøringer i hver bil ved asynkrone avslutninger; matrisen skal brukes
til å kontrollere variasjonen.

Biler trenger ikke vente på en felles rundeslutt. En krasjet bil kan starte
igjen når startplassen er ledig; en overlevende fortsetter fra samme posisjon
med neste tildelte nettverk. Biler som er ferdige med hele generasjonens
treningsbudsjett parkeres mens gjenstående kjøringer fullføres.

**Viktig teknisk avklaring:** Codex nevnte først å unngå samtidig bruk av samme
nettverk. For å unngå at bilene må vente på nettverket i køen, bruker hver
kjøring i stedet en frosset kopi av vektene. Samme nettverk kan dermed ha flere
kjøringer i gang. Oppdateringene bruker lagret handlingssannsynlighet og
begrenset importance-vekt, ikke en antakelse om at alle handlinger ble valgt
med de nyeste vektene. Dette er en off-policy-heuristikk.

Historikken eies av bilen, ikke nettverket. Hver handling merkes med sitt
opprinnelige nettverk. Ved senere kollisjon sendes bare det nye straffebidraget
til dette nettverket. Historikk fra bil A flyttes ikke til bil B, og opptjent
belønning telles ikke to ganger. Handlinger fra en tidligere generasjons
nettverk tilordnes originalen; de ommerkes ikke til et ubeslektet nytt barn.

**Utvelgelse:** Forelderen testes fortsatt som referanse, men er ikke kandidat
i den nye varianten. Den beste av de fem trente modellene overlever, selv om
alle er dårligere enn forelderen. Derfor kan resultatet gå ned fra én generasjon
til neste. Både rotasjon og utvelgelsesregel er endret; en eventuell effekt kan
ikke tilskrives rotasjon alene.

**Overgang og kontroll:** Generasjon 27 ble fullført under forrige metode.
Vinnervektene er kontrollert identiske ved oppstart av generasjon 28–100 med
rotasjon; nettet nullstilles ikke. Ny prosess betyr at posisjoner, optimizer og
historikk initialiseres på nytt ved denne overgangen, og videreføres så innenfor
kjøringen. Fire rotasjonstester dekker ringrekkefølge, eksakt antall kjøringer,
variasjon ved samtidige avslutninger, uavhengig gjenstart og riktig eier av
historisk straff. En teknisk pilot over to generasjoner er fullført.

Ny kjøring: `.ai-service/car-brake-deep-rotating/`.
[Ny generasjonslogg](experiments/rotating-generation-progress.md).
[Forrige metodes logg](experiments/deep-100-generation-progress.md) beholdes
separat. Testscenarienes seed er uendret, men referansetrafikken bruker nå
startmodellen fra denne overgangen; bruk derfor den nye startmålingen ved
sammenligning innenfor rotasjonsforsøket.

## 22 — Bredere sidesyn og 300 nye generasjoner med beholdte vekter

**Dato:** 5. november 2026. Prosjekteieren observerte kjøringen ovenfra og
påpekte at bilen trengte bedre sidesyn. Deretter ba han om minst tre ganger
så mye trening og foreslo å beholde vektene siden inngangsformatet er uendret.

**Endring:** Radarens totale åpningsvinkel økes fra 60° til 120° (±60°).
Fire nærmeste objekter, rekkevidde 540, relative hastigheter, nullutfylling,
brems og arkitekturen 23 → 8 → 8 → 8 → 8 → 2 beholdes.
83 programtester passerer, inkludert deteksjon på begge sider ved 45° og
59°, og avvisning ved 61°. Dette verifiserer implementeringen, ikke læring.

**Videreføring:** Startvektene er kontrollert identiske med vinneren fra
generasjon 100 i rotasjonsforsøket. Ingen vekter nullstilles. Optimizer,
bilposisjoner og handlingshistorikk initialiseres på nytt ved prosessstart.
Det bredere synsfeltet endrer observasjonsfordelingen selv om formatet er
kompatibelt; bedre resultater er derfor en hypotese, ikke en garanti.

**Budsjett:** 300 nye generasjoner, nummerert 101–400, uten rendering.
Fem nettverk med asynkron rotasjon får 100 treningsforsøk hver per generasjon.
Hvert nettverk testes i 20 scenarier × fem bilroller. Beste trente kandidat
velges; forelderen er bare referanse. Steggrense 1000, seed 20261110.
Treningsbelønning og 50-stegs historikk er uendret.

**Måling:** Ny startmåling med 120° radar og generasjon-100-modellen som fast
referansetrafikk. Sammenlign framgang mot denne målingen; tidligere 60°-tester
har andre observasjoner og annen referansetrafikk. Loggen viser gjennomsnittlig
distanse per test, endring per generasjon, kollisjoner og ekstra testforskyvninger.
Startmålingen vises som rad 0 og betyr generasjon-100-vektene før videre trening.

Kjøring: `.ai-service/car-brake-deep-wide-300/`.
[Fortløpende resultatlogg](experiments/wide-300-generation-progress.md).
Status ved oppføring: startet; ingen konklusjon om forbedring ennå.
Forrige 73 generasjoner tok 7339,6 sekunder; lineært tilsvarer 300 omtrent
8,4 timer. Lengre overlevelse eller maskinbelastning kan øke tiden.

## 23 — Gradienter, radar og kollisjonsavstander flyttes til Rust

**Dato:** 5. november 2026. Prosjekteieren spurte hva flaskehalsen var og ba
om å flytte også disse beregningene til Rust. En kort profilering viste at
Python-gradienter tok rundt 56 % av treningstiden; radar og kontinuerlige
kollisjonsavstander tok henholdsvis rundt 43 % og 38 % av testtiden.
Disse tallene gjelder separate profiler, ikke andeler av én hel generasjon.

**Endring:** Rust beregner nå nettverkets gradienter, radarens geometri og
relative hastigheter, samt kontinuerlige avstander mellom biler og kjegler.
Radaren og kollisjonsavstandene sendes som grupper til Rust. Python beholder
historikk, belønningsfordeling, gradientoppsummering, Adam, hendelsesrekkefølge
og styringen av forsøket. Høydefilteret i radaren bruker fortsatt samme
veibasert logikk. Python beregner avstand på synlige radarmål på nytt for å
bevare avrunding og rekkefølge ved lik avstand. Python-versjonene beholdes
som referanse og reserve når Rust ikke er valgt.

Ved valg av handling beregnes nå bare nettverkets ubundne utdata, ikke en
full gradient som deretter kastes. Støy legges fortsatt til før tanh; vi
bruker ikke allerede begrensede utdata som om de var ubundne.

**Kontroll:** 87 tester passerer. Nye tester sammenligner gradienter for
flere arkitekturer, numerisk derivasjon, radar på begge sider av synsfeltet,
høydeforskjeller, kontinuerlige 3D-avstander, hendelser og belønning.
En separat CLI-pilot har fullført trening, utvelgelse og lagring.

**Målt effekt:** Tre repetisjoner med 25 treningsforsøk og 15 testforsøk,
med samme modell og seed og Rust-veigeometri i begge varianter. Medianen
viser 3,65× raskere trening og 3,49× raskere testing. Største forskjell i
trente vekter var 1,11e-16; testpoeng var identiske. Dette er en kort
mikromåling, ikke en garanti om samme gevinst gjennom hele langtidsforsøket.
[Alle målinger](experiments/2026-11-05-rust-training-kernels.json).
Kjør om målingen med `scripts/benchmark_car_training_kernels.py`.

**Videreføring:** Den gamle prosessen ble stoppet etter ferdig generasjon 110
og lagring av alle modellfilene. Generasjon 111–400 kjører nå med Rust.
Startvektene er kontrollert identiske med vinneren fra 110, og starttestens
poeng, kjørelengde og kollisjonsantall samsvarer med før byttet.
Den nye kjøringen beholder vinnervektene og
bruker den opprinnelige generasjon-100-modellen som fast testtrafikk.
Budsjettet slutter fortsatt ved generasjon 400. Ny prosess initialiserer
bilposisjoner, historikk, optimizer og tilfeldighetsgenerator på nytt;
dette er videre trening fra vekter, ikke eksakt gjenopptakelse av RAM-tilstand.
Metodeparametre og belønning endres ikke.

Ny kjøring: `.ai-service/car-brake-deep-wide-rust/`.
[Resultatlogg etter byttet](experiments/wide-rust-generation-progress.md).
[Resultater før byttet](experiments/wide-300-generation-progress.md) beholdes.

## 24 — Ny video etter observert framgang

**5. november 2026:** Prosjekteieren observerte tydelig bedre kjøring og ba
om et nytt opptak i README. En ny 60-sekunders video viser generasjon 156
ovenfra i 1× hastighet, med 33 kjegler, 120° radar, fire radarobjekter og brems.
Alle fem biler bruker samme lagrede modell. Vektene er faste i avspillingen;
treningen fortsetter separat. Opptaket inkluderer faktiske krasj og omstarter.

Modellens 100 utvelgelsestester ga gjennomsnittlig kjørelengde 771,37, mot
405,14 ved generasjon 110. Alle 100 endte fortsatt i krasj. Videoen er ikke
selve testoppsettet; testene bruker én kandidatrolle mot faste motstandere.
[Resultater](experiments/2026-11-05-generation156.json).
Den tidligere videoen fra generasjon 8 beholdes i README som historikk.
En utdatert, hardkodet tekst om trening med 11 kjegler er fjernet fra opptaksbåndet.

## Hva vi vet, og hva som står åpent

Vi har dokumentert en stor ytelsesgevinst og reproduserbare, separate forsøk.
Vi har ikke dokumentert at historikkstraffen eller hybridmetoden forbedrer
startmodellen. Minne under kjøring, fargesensorer og bedre rundetider gjenstår.

1000-generasjoners evolusjonsforsøk kjørte fortsatt ved siste statuskontroll
5. november. De korte historikk- og hybridpilotene er avsluttet. Dette dokumentet
er et datert forsøkssnapshot, ikke en live prosessmonitor.

Detaljerte lokale kjørelogger ligger under `.ai-service/` og følger ikke automatisk
med repositoryet. Den lenkede [resultatfilen](experiments/2026-11-05-results.json)
bevarer utvalgte målinger og innstillinger for lesere av prosjektet. Fullstendige
lokale logger og modellvekter er ikke publisert gjennom denne resultatfilen.

## Slik skal nye oppføringer føres

Legg til en ny nummerert oppføring ved hver vesentlig metodeendring. Oppgi dato,
hvem som foreslo eller presiserte endringen, problemet/hypotesen, nøyaktig hva
som ble endret, startmodell og forsøksbudsjett, testoppsett, faktiske resultater
og beslutningen etterpå. Skill forslag fra implementering, programtester fra
læringsresultater og resultater fra forklaringshypoteser.

Behold mislykkede forsøk i loggen. Rett faktiske feil med en tydelig rettelse;
ikke skriv om et tidligere forsøk som om den nye metoden alltid var planen.
Når prosjekteieren endrer eller presiserer retningen, skal dette komme fram
som en del av utviklingen, ikke forsvinne inn i en etterkonstruert suksesshistorie.


Overgangen er bekreftet: generasjon 9 ble fullført med det gamle oppsettet,
og videreføringen kjører generasjon 10–30 med 33 kjegler og 60° radar.
Startvektene er kontrollert identiske med vinneren fra generasjon 9; ingen
vekter ble nullstilt. Den nye videoen i README viser generasjon-8-vekter
på det nye oppsettet, før videreføringen.
