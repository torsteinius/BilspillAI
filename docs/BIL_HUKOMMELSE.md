# Pågående eksperiment: begrenset synsfelt og hukommelse i bilspillet

Opprettet 4. november 2026, oppdatert 5. november 2026. **Status: underveis, første bane og evaluering i steg 1 er gjennomført.** Steg 2 er fortsatt under planlegging. Det er ikke gjennomført ny trening i dette forsøket.

## Hensikt og utgangspunkt

Forsøket er et første, avgrenset steg mot å undersøke hukommelse og hvordan den kan trenes. Vi starter med en mer avansert bane og begrenset synsfelt, og tester først hvordan de eksisterende trente vektene fungerer der, før eventuell videre trening. Deretter blir målet å slå rundetider og undersøke om det gir en fordel å huske løypa og når svingene kommer.

Dagens bilmodell velger styring fra aktuelle sensorverdier uten egen historikk fra kjøringen. Den trenes gjennom utvalg og mutasjon, med straff for nærhet og kollisjon. Erfaring er lagret i vektene, men modellen har ikke et eget minne om den pågående turen. Se [bilspillets dokumentasjon](../games/car/README.md) for eksisterende oppsett.

## Steg 1: kjøring med begrenset synsfelt

Lag en mer avansert, sammenhengende bane med flere og mer varierte svinger. Det opprinnelige kravet var **minst ti ganger så lang som dagens bane** (senere erstattet av nedskaleringen beskrevet nederst), målt langs senterlinjen for én hel runde. Lengden skal komme fra en lengre løype ved sammenlignbar bil- og veiskala, slik at dette blir en større kjøreoppgave.

Formen skal være tydelig forskjellig fra en oval eller sirkel, med både venstre- og høyresvinger og variasjon i hvordan de følger etter hverandre. **En åttetallslignende løype er en mulig utforming**, gjerne med variasjon utover to enkle, like sløyfer.

Banen kan også ha stigninger og nedoverbakker, slik at ett parti kan gå over et annet som en bro eller overpass. Ved en slik kryssing ligger veidelene på forskjellige høyder, og bilen fortsetter på sin egen veidel. Dette utvider det tidligere plane baneoppsettet: geometri, sensorer, kollisjonskontroll og måling av framdrift må skille mellom øvre og nedre veidel. Biler på hver sin høyde skal ikke registreres som kolliderende bare fordi de overlapper sett ovenfra. Eksakt høydeprofil og hvor detaljert stigninger skal påvirke kjørefysikken, er ennå ikke bestemt.

Bilen skal bare ha tilgang til et begrenset område rundt eller foran seg gjennom sensorene. Begrensningen skal gjelde informasjonen modellen mottar, ikke bare hva visningen tegner. Nøyaktig synsvinkel og rekkevidde er foreløpig åpne valg; ved høydeforskjeller må også skjerming fra veien og overpass avklares.

Start med å laste de eksisterende trente vektene og evaluere dem på den nye banen **uten vektoppdateringer**. Steg 1 bruker dagens sensorinput uten fargeavlesing og uten en ny hukommelsesmekanisme. Behold nettverksarkitekturen og inputenes rekkefølge og koding kompatible med den lagrede modellen, slik at vektene kan brukes direkte. Eventuelle endringer i sensorrekkevidde og synsfelt registreres som del av forsøksoppsettet.

Denne første evalueringen viser hvordan det bilen allerede har lært, fungerer på den lengre og mer varierte banen. Ved behov kan modellen deretter trenes videre med samme grunnmetode som tidligere. Resultater før og etter videre trening føres separat, og de opprinnelige vektene beholdes som sammenligningsgrunnlag.

En mulig utvidelse i dette steget er noen saktere biler som kjører i samme retning. Da kan modellen trenes til å unngå kollisjoner og passere dem. Dette er en del av forsøksideen, men er foreløpig valgfritt. Start gjerne uten disse bilene for å få et sammenligningsgrunnlag.

Foreslåtte målinger er fullførte runder, kollisjoner og, dersom saktere biler innføres, vellykkede forbikjøringer. Bane, sensorbegrensninger, fart og treningsoppsett registreres sammen med resultatene.

## Steg 2: fargeavlesing, rundetider og hukommelse om banen

Når grunnleggende kjøring er etablert, flyttes målet til å forbedre rundetidene. Dette kan også prøves med dagens treningsmetode og uten egen hukommelse, slik at vi har et utgangspunkt å sammenligne med.

Fargeavlesing innføres først i dette steget, som en utvidelse av sensorinputene fra steg 1.

Veggene skal ha **forskjellige farger i forskjellige banesegmenter**, med en fast fargefordeling for denne banen. Fargene fungerer som synlige kjennetegn modellen kan lære å forbinde med deler av løypa. Hver sensorretning skal gi **to inputverdier: avstand og veggfarge**. Med N retninger blir dette 2N inputverdier fra disse sensorene; eventuelle separate radarinput kommer i tillegg. Fargen representeres med én kodet verdi, med konkret koding bestemt før implementering.

Fargeinformasjonen skal komme fra veggen sensoren faktisk ser innenfor det begrensede synsfeltet. Modellen får ikke segmentnummer eller fargen til en skjult, kommende vegg direkte. Hvordan manglende veggtreff og treff på andre biler representeres, må avklares slik at de ikke forveksles med en veggfarge.

**Hypotesen er at modellen kan få en fordel ved å huske deler av løypa og forutse når svingene kommer, selv når de ennå ikke er synlige.** Det kan gi bedre forberedelse til svingene og dermed raskere runder. Fordelen er en hypotese som skal undersøkes, ikke et dokumentert resultat.

Treningen skal bevisst spesialiseres mot **denne ene banen med den samme fargefordelingen**, også når dette innebærer overtilpasning til banen. Hensikten er å lære igjenkjennelige steder og hva som kommer etter dem, slik at bilen kan bruke erfaring fra tidligere runder. Generalisering til ukjente baner er ikke målet for dette forsøket. Brukerens arbeidshypotese er at denne banespesifikke innlæringen er nødvendig for å få inn den ønskede hukommelsen i forsøket.

Brukeren har egne hypoteser om hvordan hukommelsen skal utformes og trenes. Disse beskrives senere; ingen bestemt minnearkitektur eller treningsregel er valgt her.

Ved sammenligning bør bane, synsfelt, trafikk og treningsbudsjett holdes mest mulig like. Registrer både rundetid for fullførte runder og hvor ofte bilen kolliderer eller ikke fullfører. En rask enkeltstående runde alene sier lite om stabil kjøring.

Det må også skilles mellom banekunnskap lært inn i vektene gjennom gjentatt trening og hukommelse som oppdateres under kjøring. Fargekjennetegn kan gjøre det mulig å lære banespesifikke handlinger direkte fra dagens observasjon. Bedre rundetider med farger alene dokumenterer derfor ikke at modellen bruker historikk. Sammenligningsmodellen uten egen hukommelse bør få de samme avstands- og fargeinputene. Hvordan vi ellers skiller disse effektene i forsøket, avklares sammen med hypotesene for steg 2.

## Åpne valg og neste oppfølging

- Detaljert baneutforming innenfor kravet om minst tidoblet lengde og en form tydelig forskjellig fra oval/sirkel; åttetallsform med overpass er et aktuelt forslag.
- Høydeprofil, stigningenes påvirkning på kjørefysikken og presis begrensning av synsfeltet, inkludert skjerming ved overpass.
- For steg 2: fargefordeling mellom segmenter, koding av veggfarge som én inputverdi per retning og representasjon av manglende veggtreff eller treff på biler.
- Om saktere biler skal inngå fra første forsøk eller legges til etter grunntreningen.
- Hvordan rundetid skal inngå i treningsmålet. Dagens oppsett bruker fast fart og kun styring; eventuell kontroll over gass og brems må avklares.
- Brukerens hypoteser for hukommelse, hvordan den trenes og når den eventuelt nullstilles.

## Første bane og evaluering, 5. november 2026

Den første versjonen av `Track.generate('figure_eight')` laget en åttetallslignende bane med ekstra svinger, 28 637 lengdeenheters rundelengde og ett overpass med 160 enheters høydeforskjell. Banen er 16,94 ganger så lang som dagens S-bane, med uendret veibredde. Den nye baneklassen inneholder også S-banen og V1-ovalen. [Kjøring og geometrimodell](../games/car/README.md#genererte-baner-med-høyde).

En første evaluering brukte de eksisterende vektene i `games/car/models/model_radar_9_8_8_1.json`, generasjon 473, uten vektoppdateringer. Oppsettet beholdt sju avstandsstråler med rekkevidde 180 og to radarinput, to biler i motsatt retning og dagens faste fart i xy-planet. Ingen fargeavlesing eller saktere trafikkbiler inngikk.

Etter **14 319 steg** hadde begge biler kjørt minst **1,506 runder**, med **ingen kollisjonsomstarter eller sluttkollisjoner**. Samlet poengsum var omtrent −0,00147. Dette er én evaluering fra standardstarten på den nye banen, ikke en bred mestringstest. Modellfilen ble ikke endret. Kjøringen tok omtrent 28 sekunder uten visning på maskinen som ble brukt.

Tester kontrollerer blant annet høyde og framdrift gjennom krysset, veggsensorer ved overpasset, at biler på forskjellige nivåer ikke kolliderer eller gir biltreff i sensorene, og at det gamle biloppsettet fortsatt fungerer. Videre oppfølging er flere startplasseringer og eventuelt saktere biler. Steg 2 bygger videre på dette når hypotesene for hukommelse er konkretisert.

## Oppfølging: fem biler med forskjellig fart

Steg 1 er utvidet med fem biler i samme retning, med faste fartsfaktorer 80, 90, 100, 110 og 120 %. De raskeste starter bakerst med 60 enheters mellomrom, slik at de tar igjen de saktere. Først prøves de eksisterende vektene uten trening. Sensorer og kollisjoner tar hensyn til alle andre biler; nettverket beholder ni inputverdier. Dette oppsettet skal undersøke faktiske forbikjøringer, og garanterer ikke at den gamle modellen mestrer dem. Resultatet med to biler ovenfor gjelder fortsatt bare det tidligere oppsettet.

Den første direkte avspillingen med de gamle vektene viste kollisjoner og flere omstarter allerede tidlig i kjøringen. Oppsettet gir dermed innhentingssituasjoner, men stabil forbikjøring er ennå ikke dokumentert. Ingen vekter ble endret.

## Justering: separate startplasser og videre visualisering

Bilene starter nå jevnt fordelt rundt hele banen, med en femtedels runde mellom hver, i stedet for samlet med 60 enheters mellomrom. Hver bil beholder sin egen startplass ved omstart. Fartsfaktorene 80–120 % er uendret. Dermed tar det lengre tid før bilene møtes; kollisjonene beskrevet over gjelder den tidligere, tette startgruppen.

## Implementert: Rust og GPU direkte

Den opprinnelige planen om en Rust-basert CPU-renderer først ble erstattet av å gå direkte til GPU. En Rust-renderer med `wgpu` kjører nå som WebAssembly i nettleseren. Banegeometrien lastes én gang, og GPU-en håndterer perspektiv, klipping, dybdetest og tegning. JavaScript formidler bil- og kameratilstand og håndterer knapper. Simulering og trening er uendret; ingen ny trening ble startet i denne omleggingen.

WebGPU-støtte og faktisk rendering er kontrollert i appens nettleser. Visningen har førerplass og kamera bak bilen, samt geometrikontroller for undergang, bro og rampe. Den gamle Canvas-visningen brukes som reserve hvis GPU-rendereren ikke kan kjøre. Det er ikke gjennomført en sammenlignbar ytelsesbenchmark, og visningens tilstandsoppdatering bruker fortsatt det eksisterende pollingoppsettet. [Bygg og begrensninger](../rust/car_renderer/README.md).

## Mindre bane med samme form

Etter vurdering i visningen er hele den opprinnelige senterlinjen skalert til **¼ i x, y og z**, uten å glatte eller endre svingene. Veien er gjort fire ganger bredere før nedskaleringen, slik at endelig veibredde fortsatt er 76, og bilstørrelsen er uendret. Rundelengden er nå **7159** i stedet for 28 637 lengdeenheter. Broens topp ligger på z=40, og bilene starter med omtrent **1432** lengdeenheter mellom hver. Fartsfaktorene 80–120 % er beholdt.

Dette erstatter det tidligere kravet om minst tidoblet banelengde. Svingene er nå fysisk skarpere (minste senterlinjeradius omtrent 26), og tidligere feilfrie resultater på den store banen gjelder ikke automatisk her. Det nye oppsettet prøves med eksisterende vekter uten ny trening. Sensor- og kollisjonstestene for overpasset passerer med den lavere broen.

Første avspilling på den nedskalerte banen viser flere tidlige kollisjoner og omstarter med de eksisterende vektene. Formen er beholdt som ønsket; dette er ikke dokumentasjon på at modellen allerede mestrer de skarpere svingene.

## Egen treningsbane, kjegler og radar

En separat `training`-bane er lagt til, med hyppige svinger begge veier og 11 faste kjegler fordelt langs veien. Kjeglene inngår i sensorer, radar og kollisjonskontroll, og tegnes også av Rust/WebGPU. Første visning bruker eksisterende vekter uten ny trening.

Radaren er utvidet til tre ganger lineær størrelse: rekkevidde 540, radius 270 og sentrum 270 foran bilen. Strålene har fortsatt rekkevidde 180. API-et leverer avstand og fremover-/sideplassering for alle oppdagede mål. For ny trening finnes `spatial`-formatet, med separat normalisert nærhet og sideplassering for det nærmeste målet. Gamle vekter vises med sitt opprinnelige inputformat; det nye formatet brukes ikke umerket på disse vektene. [Oppsett og semantikk](../games/car/README.md#treningsbane-med-kjegler-og-større-radar).

## Startet trening med romlig radar, 5. november 2026

Ny trening er startet på `training`-banen med samme evolusjonsmetode som tidligere: 36 kandidater, seks eliter og mutasjon, planlagt i 100 generasjoner. Hver kandidat kjører 2542 steg med fem biler, fartsfaktorer 80–120 %, kjegler og radarskala 3. Fitness er fortsatt straff for nærhet og kollisjoner, uten egen bonus for forbikjøring eller runder.

Forsøket bruker `spatial`-radar (separat nærhet og sideplassering) og nettverket 9 → 8 → 8 → 1. Det starter fra nye vekter, siden gamle vekter bruker et annet radarformat. Seed er 20261105. Kontrollpunkt lagres etter hver fullførte generasjon til `games/car/models/training_spatial_convoy_20261105.json`; eldre modeller beholdes. Ingen ferdige treningsresultater er rapportert ved oppstart.

Startkommando:

```sh
python3 -m games.car.app --track training --traffic convoy --radar-mode spatial --radar-scale 3 --model games/car/models/training_spatial_convoy_20261105.json --seed 20261105 --port 18766
```

Etter at et kontrollpunkt finnes, kan forsøket videreføres med `--fast-generations ANTALL` i samme kommando. Vanlig oppstart uten dette flagget starter en ny trening, så den skal ikke brukes til å gjenoppta en eksisterende kjøring.

## Status ved dokumentasjons- og videooppdatering

Avlest 05.11.2026 kl. 11:25: treningen er aktiv i generasjon **1 av 100**, kandidat **13 av 36**. Beste kandidatpoeng registrert så langt er **-10311.2**. Dette er løpende fitness fra utviklingsforsøket, ikke et mål på sikker forbikjøring eller dokumentert generalisering. Ingen fullført generasjon var lagret ved denne avlesningen.

Vi arbeider nå med den egne treningsbanen på omtrent 5083 lengdeenheter, med vekslende svinger, 11 kjegler, fem biler og radaren i `spatial`-format. Den nedskalerte åttetallsbanen er bevart som et separat forsøk. Hukommelse og veggfarge i steg 2 er fortsatt ikke implementert. Rust/WebGPU brukes til 3D-visningen.

De nye videoene nedenfor viser faktiske kandidater under trening, inkludert kollisjoner og omstarter. Generasjon, kandidat, steg og avspillingshastighet er brent inn i bildet. Visningen spiller ferdige kandidatopptak og kan derfor ligge etter kandidaten som beregnes akkurat nå. Klippene er ikke presentert som kjøring med ferdigtrent modell.

### Nye videoklipp

- [Oversiktskart: biler, kjegler og radar (31 sekunder)](media/training-cones-overview.mp4) — generasjon 1, kandidat 7.
- [3D bak bilen med Rust/WebGPU (60 sekunder)](media/training-cones-3d.mp4) — generasjon 1, kandidat 13.

Begge er 1600 × 1080 MP4/H.264 uten lyd, tatt ved 1× avspilling. Forhåndsvisninger ligger i prosjektets README. Opptakene viser den eksisterende treningskjøringen uten å endre vektene eller treningsoppsettet for opptakets skyld.


### Ny radar og ny trening: 1000 generasjoner uten visning

05.11.2026: Radaren skjules nå av veikantene. En siktlinje fra bilen til
nærmeste side av målet må ligge innenfor veien; ellers blir bilen eller kjeglen
utelatt fra både nettverksinput og radarens målliste. Høyden interpoleres langs
siktlinjen, og eksisterende høydefilter skiller trafikk ved brokrysset.
Dette er en tilnærming basert på banens veiflate, ikke en full 3D-stråletest mot
renderte veggpolygoner. Testene dekker skjulte biler/kjegler, synlige mål og ramper.

Treningen er startet på nytt med tilfeldige vekter, 1000 generasjoner,
36 kandidater per generasjon, fem biler, spatial radar med 3× rekkevidde og
treningsbanen med kjegler. Tidligere lagrede modeller beholdes. Den tidligere
visuelle treningsprosessen er stoppet. Ny modell:
`games/car/models/training_spatial_occluded_20261105.json`.

```bash
.venv-training/bin/python -u -m games.car.advance 1000 --fresh --backend rust \
  --model games/car/models/training_spatial_occluded_20261105.json
```

Kjøringen har ingen webserver, avspilling eller videoopptak. Checkpoint lagres
etter hver fullførte generasjon. Lokal prosessinformasjon og logg finnes i
`.ai-service/car-occluded-1000/`. Oppstart betyr ikke at de 1000 generasjonene er
ferdige. Rust akselererer nettverket og mutasjonene; fysikk og sensorer er fortsatt
Python. En kort måling før siktsperringen ga 5,62 sekunder med Python mot 5,39 med
Rust, omtrent 4 % raskere totalt. Hele kjøringen kan derfor ta flere døgn.

Videoene ovenfor viser den tidligere radaren og generasjon 1 før denne omstarten;
de dokumenterer ikke resultatet av treningen med siktsperring. Veggfarger og
hukommelse hører fortsatt til del 2.


Treningsvideoer skal vise hele banen ovenfra som standard, med alle fem bilene
synlige samtidig. 3D-opptak er et supplement. Dette endrer ikke den pågående
1000-generasjoners treningen uten visning.
