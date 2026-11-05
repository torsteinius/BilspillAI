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
