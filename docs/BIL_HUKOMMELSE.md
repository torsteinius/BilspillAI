# Pågående eksperiment: begrenset synsfelt og hukommelse i bilspillet

Opprettet 4. november 2026. **Status: underveis, i planleggingsfasen.** Dette dokumentet beskriver et nytt forsøk i to steg. Implementering og treningskjøringer for dette opplegget er ikke gjennomført som del av denne dokumentasjonen; resultater føres inn etter hvert.

## Hensikt og utgangspunkt

Forsøket er et første, avgrenset steg mot å undersøke hukommelse og hvordan den kan trenes. Vi starter med en mer avansert bane og begrenset synsfelt, og tester først hvordan de eksisterende trente vektene fungerer der, før eventuell videre trening. Deretter blir målet å slå rundetider og undersøke om det gir en fordel å huske løypa og når svingene kommer.

Dagens bilmodell velger styring fra aktuelle sensorverdier uten egen historikk fra kjøringen. Den trenes gjennom utvalg og mutasjon, med straff for nærhet og kollisjon. Erfaring er lagret i vektene, men modellen har ikke et eget minne om den pågående turen. Se [bilspillets dokumentasjon](../games/car/README.md) for eksisterende oppsett.

## Steg 1: kjøring med begrenset synsfelt

Lag en mer avansert, sammenhengende bane med flere og mer varierte svinger. Banen skal være **minst ti ganger så lang som dagens bane**, målt langs senterlinjen for én hel runde. Lengden skal komme fra en lengre løype ved sammenlignbar bil- og veiskala, slik at dette blir en større kjøreoppgave.

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

Neste praktiske steg er å konkretisere den nye banen og evaluere de eksisterende vektene der som første del av steg 1. Steg 2 bygger videre på dette grunnlaget når hypotesene for hukommelse er dokumentert. Ingen resultater er registrert for det nye forsøket ennå.
