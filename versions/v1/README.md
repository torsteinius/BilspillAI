# BilspillAI

BilspillAI er en simulering sett ovenfra i 2D. En bane bygges automatisk bit for bit, og en bil uten innebygd kunnskap om kjøring skal lære å følge banen ved hjelp av et nevralt nettverk. Bilen får fire avstandsmålinger til banekanten. Å komme nær kanten gir straff, og å treffe kanten gir en betydelig strengere straff.

All banegenerering, bilfysikk, sensormåling, belønningsberegning og læring skal lages i Python. En eventuell React-klient viser simuleringen og henter oppdateringer fra Python via API. Simuleringen skal kunne kjøres og trenes uten React.

Dette er prosjektets første avgrensning. Det skal foreløpig ikke være trafikk, motstandere, 3D eller avansert kjørefysikk.

## Kjør demoen

Kjør `python3 demo.py` og åpne <http://127.0.0.1:8765>. Demoen bruker bare standardbiblioteket i Python. Stopp serveren med Ctrl+C.

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
