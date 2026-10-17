# Bilspill i AI-spill

Bilspillet er en simulering sett ovenfra i 2D. En bane bygges automatisk bit for bit, og en bil uten innebygd kunnskap om kjøring skal lære å følge banen ved hjelp av et nevralt nettverk. Bilen får fire avstandsmålinger til banekanten. Å komme nær kanten gir straff, og å treffe kanten gir en betydelig strengere straff.

All banegenerering, bilfysikk, sensormåling, belønningsberegning og læring skal lages i Python. En eventuell React-klient viser simuleringen og henter oppdateringer fra Python via API. Simuleringen skal kunne kjøres og trenes uten React.

Dette er prosjektets første avgrensning. Det skal foreløpig ikke være trafikk, motstandere, 3D eller avansert kjørefysikk.

## Kjør demoen

V1 er bevart uendret med dokumentasjon i `versions/v1/`. Aktivt bilspill ligger i `games/car/` og bruker den felles klassen `NeuralNetwork` i `ai/network.py`. Alle kommandoer nedenfor kjøres fra prosjektroten.

**V2:** Kjør `python3 -m games.car.app` og åpne <http://127.0.0.1:8766/>. To like biler starter side om side ved samme startlinje midt i S-svingen på nedre langside og kjører i motsatt retning med samme nettverk og fast fart. Dermed kommer neste møte omtrent etter en halv runde hver, avhengig av kjøringen. Startplasseringen gir ingen sporregel til nettverket. Hver bil har sju sensorer ved −90°, −60°, −30°, 0°, 30°, 60° og 90° relativt til bilen. Sensorene måler nærmeste vegg eller bil. Veggkontakt straffes og starter bare den berørte bilen på nytt; den andre fortsetter. Ved bilkollisjon starter begge på nytt. En bil venter utenfor aktiv simulering hvis startplassen er opptatt.

V2 bruker et delt nettverk med ni innganger (sju stråler og to radarverdier), to skjulte lag med åtte tanh-nevroner hver og ett tanh-utslag for styring (9 → 8 → 8 → 1, totalt 161 vekter og biasverdier), trent med utvalg og mutasjon i 100 generasjoner med 36 kandidater. Ingen regel for vikeplikt eller kjørefelt er programmert inn. Treningspoengene består bare av straff for nærhet og kollisjon. Kollisjonsstraffen er redusert fra 350 til 50 poeng; nærhetsstraffen er uendret. De seks beste kandidatene kopieres uendret til neste generasjon, som tidligere. Det nye nettverket trenes fra tilfeldige vekter og bruker en egen modellfil; den gamle modellen overskrives ikke. Framdrift, kjøreretning og rundetelling brukes ikke i belønningen. Hver kandidat evalueres i 650 steg, med individuelle omstarter underveis. Begge tilbakestilles når neste kandidat skal evalueres. Treningen bruker standardstarten på en fast bane med S-sving på nedre langside; etterpå kontrolleres også to forskjøvede startplasseringer. Dette er ikke en test av generell kjøring på nye baner.

Visningen følger selve kandidaten som evalueres, med kandidatnummer, steg, poeng og kollisjonsutfall. Hastigheten kan settes til 1×, 3×, 10× eller 30×; den endrer ventetiden, ikke fysikken. Beste nettverk lagres etter hver generasjon i `games/car/models/model_radar_9_8_8_1.json`. Vanlig oppstart trener på nytt fra tilfeldige vekter; `python3 -m games.car.app --replay` viser den lagrede modellen. Tidligere modeller med framdriftsbelønning brukes ikke. Testene kjøres med `python3 -m unittest discover -s v2 -p 'test_*.py' -v`.

### V1

Kjør `python3 versions/v1/demo.py` og åpne <http://127.0.0.1:8765>. Demoen bruker bare standardbiblioteket i Python. Stopp serveren med Ctrl+C.

Demoen trener et lite nettverk med fire inputverdier, fem skjulte nevroner og ett styreutslag gjennom 60 generasjoner med utvalg og mutasjon. Visningen følger beste nettverk ved starten av hvert forsøk. Treningen starter på nytt når serveren startes; modellen lagres foreløpig ikke.

Denne første demoen bruker en fast oval bane og en enkel SVG-visning som henter tilstand fra Python. Tilfeldig banegenerering, React og evaluering på separate testbaner er ikke implementert ennå. Resten av dokumentet beskriver målet for prosjektet.

## Banen

Banen har fast bredde og skal bli en sammenhengende, lukket løype. Et mulig startpunkt ligger til venstre i visningen; plassering og startretning kan justeres.

Genereringen har tre faser:

1. **Bygg utover.** Legg til korte banestykker med rette partier og svinger. Svinger med klokka skal være mer sannsynlige enn svinger mot klokka, uten at alle svinger må gå samme vei.
2. **Vend tilbake.** Når den samlede retningsendringen er omtrent 180 grader med klokka, begynner generatoren gradvis å styre banen tilbake mot startområdet. Dette betyr at banen beveger seg tilbake, ikke at bilens hastighet reduseres.
3. **Lukk banen.** Når endene nærmer seg hverandre, beregnes en forbindelse som treffer startpunktet med riktig retning og uten å bryte minste tillatte svingradius. Den siste delen skal planlegges, ikke bare trekkes som en rett strek mellom endene.

### Geometriske krav

- Banen beskrives med en senterlinje og en fast bredde. Kantene ligger en halv banebredde på hver side.
- Minste svingradius gjelder senterlinjen og må være større enn halve banebredden, slik at innerkanten ikke kollapser i en sving.
- Retningen skal være sammenhengende mellom banestykker, også der banen lukkes. Det skal ikke være skarpe hjørner.
- Hele banebredden skal være fri for selvkryssing og overlapp mellom ulike deler av løypa. Nabostykker og selve skjøten ved start skal møtes normalt.
- Forbindelsen tilbake til start må kontrolleres mot resten av banen, både for svingradius og ledig plass.
- Hvis en gyldig avslutning ikke finnes, må generatoren gå tilbake og endre tidligere stykker eller prøve en ny bane. Den skal ikke redusere radiuskravet for å tvinge fram en løsning.

### Forslag til første implementasjon

Bruk rette linjestykker og sirkelbuer med kjent radius. Det gjør radiuskravet tydelig og gir et enkelt grunnlag for sensorer og kollisjonskontroll. Ved lukking søker generatoren etter en kombinasjon av buer og rette partier som forbinder sluttposisjon og sluttretning med startposisjon og startretning. En forbindelse godtas først når hele geometrien er validert.

Samlet retningsendring følges uten å nullstilles ved en hel omdreining. Etter omtrent en halv omdreining økes påvirkningen mot startområdet gradvis. Overgangen til lukking bør avhenge av både avstand, retning og tilgjengelig plass. Generatoren må reservere rom for tilkoblingen tidlig nok.

Tilfeldig generering skal støtte en fast seed, slik at samme bane kan gjenskapes. Bredde, minste radius, stykkelengde, sannsynlighet for sving med klokka og grenser for antall forsøk skal være konfigurerbare.

## Bilen og sensorene

Bilen starter på banen med retning langs senterlinjen. Nettverket har ingen ferdig regel for hvordan det skal svinge, og skal ikke få fasiten i form av banens senterlinje eller kommende svinger.

Nettverkets input er fire avstander fra bilen til første banekant langs fire måleretninger. Retningene følger bilen, ikke verdenskoordinatene. Nøyaktige sensorvinkler er ikke bestemt ennå.

Et forslag til første forsøk er målinger mot venstre, skrått framover mot venstre, skrått framover mot høyre og mot høyre. Fire retninger betyr dermed ikke nødvendigvis foran, bak, venstre og høyre. Vinklene skal kunne endres slik at ulike oppsett kan sammenlignes.

Sensorene får en maksimal rekkevidde, og avstandene normaliseres før de gis til nettverket. Ingen kant innenfor rekkevidden rapporteres som maksimal avstand. Kollisjonskontrollen må bruke bilens utstrekning og hele banekanten; fire sensorstråler alene er ikke nok til å oppdage alle sammenstøt.

### Forslag til første bilmodell

Start med fast, positiv fart og la nettverket bare styre svingutslaget. Dermed kan bilen ikke unngå straff ved å stå stille, og første læringsoppgave blir avgrenset til styring. Gass og brems kan vurderes senere.

Bilen har posisjon, retning og en enkel fysisk utstrekning. Python oppdaterer bevegelsen med fast simuleringstidssteg. Bilens maksimale svingutslag og fart må være forenlige med banens minste radius. Tidssteg og kollisjonskontroll må hindre at bilen hopper gjennom en kant mellom to oppdateringer.

## Læring og straff

Hvert treningssteg følger samme løkke: mål avstander, la nettverket velge styring, flytt bilen, kontroller kollisjon og beregn belønning eller straff. Treningsmetode og bibliotek er foreløpig åpne valg.

Belønningssystemet skal inneholde:

- **Straff nær kanten.** Straffen øker når klaringen mellom bilen og kanten blir liten. En mulig utvidelse er ekstra straff når klaringen minker raskt.
- **Kraftig straff ved kontakt.** Kontakt med kanten gir vesentlig sterkere straff enn vanlig nærhet. Første forslag er at dette også avslutter forsøket.
- **Belønning for framdrift.** Som tillegg til straff foreslås positiv belønning for faktisk framdrift langs banen i ønsket kjøreretning. Dette skal gjøre det lønnsomt å fullføre løypa.

Framdrift må måles sammenhengende langs løypa, slik at bilen ikke belønnes for å hoppe mellom nærliggende banedeler eller passere startstreken fram og tilbake. Simulatoren kan bruke senterlinjen til denne beregningen uten at nettverket får den som input.

Et forsøk avsluttes ved kollisjon, fullført runde eller en tidsgrense. Belønningsvektene må prøves ut; ingen konkrete verdier er bestemt. Først brukes en fast bane for å undersøke om bilen lærer. Deretter brukes flere genererte baner og egne testbaner som ikke inngår i treningen.

## Python og React

Python er eneste kilde til simuleringstilstand og har ansvar for:

- Banegenerering og validering av geometri.
- Bilbevegelse, sensorer og kollisjoner.
- Nettverk, trening og beregning av belønning.
- Lagring av baneseed, innstillinger og trente modeller.
- Et API for styring og avlesning av simuleringen.

React er valgfritt og har ansvar for å tegne banen og bilen ovenfra, vise sensorstrålene og presentere treningsstatus. Brukerhandlinger som start, pause og tilbakestilling sendes til Python. React skal ikke beregne fysikk eller læring.

API-et bør kunne levere banegeometri, bilens posisjon og retning, sensoravstander, belønning, forsøksnummer, kollisjonsstatus og framdrift. Hver tilstandsoppdatering bør ha forsøks-ID og stegnummer, slik at visningen kan skille forsøk og håndtere forsinkede oppdateringer. Endepunkter og valg mellom periodisk henting og strømming bestemmes ved implementering.

Treningen og skjermoppdateringen skal ha uavhengig tempo. Python må kunne kjøre mange treningssteg mellom hver oppdatering til React.

## Første milepæler

1. Generer og valider en lukket bane i Python med fast bredde og minste svingradius.
2. Legg til en bil med enkel bevegelse, fire sensorer og kollisjonskontroll.
3. Koble inn et nevralt nettverk og tren styring på en fast bane.
4. Undersøk læring på flere baner og mål resultatet på separate testbaner.
5. Koble på en valgfri React-visning via API.

Første fungerende versjon skal kunne gjenskape en bane fra seed, avvise ugyldige baner, kjøre og trene uten frontend og vise målbare resultater. Relevante mål er framdrift før kollisjon, antall fullførte runder og kollisjoner per forsøk. En pen animasjon alene er ikke dokumentasjon på at bilen har lært.

## Valg som gjenstår

Sensorvinkler, banebredde, minste radius, bilstørrelse, fart, nettverksarkitektur, treningsmetode og belønningsvekter bestemmes gjennom første implementasjon og forsøk. Fast fart, foreslått sensoroppsett og belønning for framdrift er startforslag; Python som kjerne, fire avstandsmålinger, straff ved kanten og 2D ovenfra er prosjektkrav.

### Uavhengig visualisering

Visningshastigheten styrer bare avspillingen av opptak fra faktiske treningsforsøk. Python trener uten animasjonsventing. Visningen fullfører ett opptak før den henter det nyeste ferdige forsøket; noen kandidater vises derfor ikke. Generasjonen som trenes og kandidaten som vises merkes separat.

### Radar

Bilene har i tillegg en radar med en rund deteksjonsboble med radius 90, sentrert 90 lengdeenheter foran bilen. Den oppdager den andre bilens utstrekning mellom sensorstrålene og gir to ekstra inputverdier: nærhet og relativ retning. Banekanter skjermer ikke radar i denne enkle modellen. Et oransje felt viser treff. Nettverket er nå 9 → 8 → 8 → 1 med 161 parametere. Tidligere vekter overføres med nullvekter for radarinputene, som bevarer tidligere styring nøyaktig før videre trening. Modellen lagres separat i `games/car/models/model_radar_9_8_8_1.json`.

### Ta opp banevideo

Trykk «Ta opp banevideo» over banen og deretter «Stopp opptak». Opptaket kan forhåndsvises og lastes ned fra lenken som vises. Bare banefeltet med biler, sensorstråler og radar tas opp, uten lyd, i 1600 × 1080. Nettleseren velger MP4 hvis det støttes, ellers WebM. Hold fanen synlig under opptaket. Last ned videoen før siden lukkes eller lastes på nytt. Treningen fortsetter uavhengig av opptaket.

### Førerplass i 3D

V2 har en enkel 3D-perspektivvisning fra førersetet over oversiktskartet. Velg grønn eller blå bil med «Følg». Banen og den møtende bilen projiseres fra samme geometri og posisjoner som i Python-simuleringen. Frontrute, dashbord og ratt gir følelsen av å sitte inne i bilen. Rattutslaget illustrerer endring i kjøreretning, ikke nettverkets eksakte styreutslag. Bruk 1× for rolig avspilling. Visningen bruker Canvas uten ekstra biblioteker. Videoopptaket gjelder fortsatt oversiktskartet.
