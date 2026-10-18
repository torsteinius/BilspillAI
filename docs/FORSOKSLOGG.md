# Forsøkslogg: læring i labyrinter

Oppdatert 18. oktober 2026. Denne oversikten samler gjennomførte forsøk, feilrettinger og foreslåtte neste steg. Den er basert på prosjektets dokumentasjon og lagrede målinger. Flere forhold ble endret mellom forsøkene; dette er en utviklingslogg, ikke en kontrollert sammenligning som isolerer effekten av hvert tiltak.

Gjeldende spillregler finnes i [Straff, belønning og historikk](MAZE_REWARDS.md). Neste foreslåtte læringsopplegg finnes i [Assistert læring fra kjente ruter](ASSISTERT_LARING.md). Eldre forsøk er også beskrevet i [labyrintens README](../games/maze/README.md).

## Hva en runde betyr

I de siste forsøkene er en treningsrunde én **generasjon**: den eksisterende modellen og tre muterte kandidater prøves på de samme to nye labyrintene. Kandidaten med høyest gjennomsnittlig poengsum velges videre. Dermed er én generasjon åtte gjennomføringsforsøk.

Poeng summeres gjennom et forsøk, men vektene justeres ikke etter hvert steg. Dette er evolusjonstrening med belønningsbasert utvalg. Det er ikke direkte veiledet trening med gradienter, og heller ikke samme læringsalgoritme som AlphaStars forsterkningslæring.

«Antall utganger under trening» omfatter også kandidater som senere forkastes. Det må skilles fra hvor mange nye labyrinter den endelige modellen løser. At en kandidat ble valgt, betyr heller ikke at den løste labyrinten: den kan bare ha fått mindre negativ poengsum enn de andre.

## Forsøk med struktur, observasjoner og minne

| Forsøk | Hva vi prøvde | Hva vi kan si etterpå |
| --- | --- | --- |
| Åpent terreng før labyrint | Starte med bevegelse mellom hindringer og øke vanskeligheten før overgang til labyrint. | Et tidligere opplegg for gradvis vanskeligere oppgaver. Det er ikke startopplegget for den nåværende modellen. |
| Selvskrevet minne | Nettet fikk egne utganger for å skrive verdier og velge når minnet skulle brukes. | Dette krevde at det lærte både navigasjon og meningsfull minneskriving. Forsøket alene dokumenterte ikke at minnet ble nyttig. |
| Deterministisk historikk | Simulatoren lagrer sensorbildet ved hjørner og forgreninger, uten at nettet må lære å skrive minne. | Det gir en definert betydning til minneplassene. Registrering av hvert sted én gang hindrer at samme hjørne fyller opp minnet ved pendling. |
| Mange ekstra lag | Utvide fra tre til 23 skjulte lag med gradvis smalere lag. | Nettet kunne kjøres. Lagret status viser 250 av planlagte 400 generasjoner før avbrudd; dette omtales ikke som et fullført 400-runders forsøk. Det finnes ikke et sammenlignbart resultat som viser at dybden ga bedre navigasjon. |
| To ekstra lag | Gå tilbake til fem skjulte lag etter avklaringen om ønsket dybde. | Fem skjulte lag ble videreført i de senere forsøkene. Endringen var en korrigering av oppsettet, ikke dokumentasjon på optimal dybde. |
| Fryste ubrukte minneinnganger | Nullstille forbindelser fra tomme minneplasser og holde dem utenfor mutasjon frem til første faktiske bruk. | Dette hindrer drift før første bruk. Biaser og senere lag lærer fortsatt; minneplassene har ikke egne isolerte baner gjennom hele nettet. |
| Normalisering av skjulte lag | Normalisere beregningen før tanh i hvert skjult lag. | Tiltaket ble innført, men fjernet ikke tendensen til å velge samme handling gjentatte ganger. Normalisering garanterer ikke en jevn fordeling mellom handlingene. |
| To utganger fremfor fire | Bruke bitene 00=bak, 01=høyre, 10=venstre og 11=frem. | Handlingskodingen ble enklere og eksplisitt. De første målingene viste at denne endringen alene ikke løste læringsproblemet. |
| Fire følere fremfor åtte | Måle de fire bevegelsesretningene og fjerne diagonale følere. | På 8×8-kart gikk inngangsbredden fra 296 til 148. Dette ble endret sammen med minnevektingen; effektene kan ikke skilles fra hverandre med disse forsøkene. |
| Nyeste minne først, med demping | Dagens observasjon først; deretter minne med faktor 0,75, 0,5625, 0,421875, 0,31640625 og gulv 0,25. | Dette er oppsettet i den nåværende modellen. Det gjør de eldre inputverdiene mindre, men lærte vekter kan fortsatt gi dem stor innflytelse. |
| Absolutte kartretninger | Vurdere nord/sør/øst/vest i stedet for relative bevegelser. | Diskutert som alternativ, men ikke innført i den nåværende modellen. Handlingene er fortsatt relative. |

Den nåværende arkitekturen er **148 → 124 → 100 → 75 → 51 → 27 → 2** på 8×8-kart. Tomme minneplasser er null, og nåværende observasjon ligger alltid i de fire første inngangene.

## Belønning og utforsking

Et hovedproblem var at pendling kunne være et bedre valg etter poengreglene enn å prøve noe nytt og treffe veggen gjentatte ganger. Dette er forskjellig fra at «bakover» skulle gi en egen positiv bonus.

Vi endret ny-rute-belønningen til å gjelde første besøk på alle gangbare ruter, la egen bonus på nye hjørner og forgreninger, og hindret at gjenbesøk ga de samme bonusene igjen. I det strenge regelsettet avslutter veggtreff eller gjentatt full tilstand straks med −2. Gjenbesøk koster −0,30. Utgang gir +100. Detaljer og tidligere regelverdier står i [regeldokumentet](MAZE_REWARDS.md).

Vi fant også en faktisk feil i mutasjonsgeneratoren: rekonstruerte økter kunne bruke samme tilfeldighetsstrøm på nytt i hver generasjon. Den ble rettet slik at generasjonsnummeret inngår i strømmen. Dette er en feilretting, ikke et alternativt læringsprinsipp.

## Kontroller av pendling, vekter og avspilling

**Tomme innganger:** I undersøkte bakoverforsøk var bidraget fra 288 tomme minneinnganger nøyaktig null. Å nullstille forbindelsene deres endret ikke handlingen. Beregningen i de aktive lagene og biasene kunne fortsatt foretrekke bakover. Null input betyr derfor ikke automatisk null output eller et tilfeldig handlingsvalg.

**Tilfeldige vekter:** En diagnose brukte 30 nett og 80 observasjoner per nett. Etter mutasjon med sigma 0,12 valgte 25 av 30 nett samme handling på over 90 % av observasjonene. Med normalisering var tallet 20 av 30. Dette viser at tilfeldig endring av vektene kan gi nesten konstant oppførsel; det er ikke det samme som å trekke en tilfeldig handling ved hvert steg. Målingen er en diagnose av de undersøkte oppsettene, ikke en universell egenskap ved alle nett.

**Valgt kandidat:** En rekonstruert generasjon i det normaliserte forsøket ga kandidatpoengene −8,45, −77,625, −33,075 og −4,45. Kandidaten med −4,45 ble lagret, med identiske rekonstruerte vekter og riktig filhash. Ingen av kandidatene nådde utgangen. Utvalget fulgte poengene, men det gjorde ikke vinneren til en god navigatør.

**Trening mot avspilling:** En senere kontroll rekonstruerte 50 generasjoner, 400 forsøk og 7958 steg i forsøket med to utganger. Handlinger, posisjoner, belønninger og de valgte vektene stemte i denne kontrollen. Dette avgrenser hvilke feil den undersøkte; det beviser ikke at alle tidligere visninger var feilfrie.

Visningen ble gjort mer etterprøvbar med poeng fra den aktuelle animasjonsrammen, identifikasjon av kandidat og kontrollpunkt, og mulighet for å spille alle forsøk i rekkefølge. Under lange kjøringer lagret vi i stedet utvalgte milepæler hver 300. generasjon. Et slikt opptak viser bestemte forsøk, ikke gjennomsnittlig mestring på mange kart.

## Målte treningsforløp

Tallene er antall løste labyrinter blant 64 separate evalueringslabyrinter, før og etter hver kjøring. Før/etter i hver rad vurderes med samme oppsett. Resultater på tvers av ulike regelsett skal ikke behandles som en isolert sammenligning av nettarkitektur.

| Oppsett | Generasjoner | Løst før → etter | Hva resultatet viste |
| --- | ---: | ---: | --- |
| To utganger, eldre regler | 1 → 51 | 1/64 → 1/64 | Bedre gjennomsnittspoeng uten flere løste labyrinter. Bakover utgjorde omtrent 44 % av handlingene etter trening. |
| To utganger, strenge regler, åtte følere | 0 → 50 | 2/64 → 4/64 | En liten forbedring i denne kjøringen. |
| Samme modell, 20 til | 50 → 70 | 4/64 → 1/64 | Videre trening kunne også gi tilbakegang. |
| Åtte følere, 2000 til | 70 → 2070 | 1/64 → 7/64 | Fremgang, men fortsatt lav mestring. |
| Fire følere og dempet minne, fra nye vekter | 0 → 2000 | 0/64 → 7/64 | Samme antall løste som åtteføler-modellen, med et mindre nett. |
| Fire følere og dempet minne, 5000 til | 2000 → 7000 | 7/64 → 17/64 | Klar fremgang på disse kartene, men fortsatt 47 mislykkede forsøk. Ingen bakoverhandlinger i sluttesten. |

De tre siste radene bruker de samme 64 kartene, kontrollert mot de lagrede kartnavnene og seedene. Gjentatt bruk gjør dette til et nyttig sammenligningssett under utvikling; en endelig vurdering bør også bruke helt nye kart.

Den første fireføler-kjøringen tok **5 min 26 sek** og omfattet 16 000 forsøk, hvorav 710 nådde utgangen. De neste 5000 generasjonene tok **14 min 53 sek** og omfattet 40 000 forsøk, hvorav 4822 nådde utgangen. Disse utgangstallene gjelder alle kandidater gjennom treningen, ikke bare sluttmodellen. Kjøretidene er målinger fra disse kjøringene, ikke en isolert maskinvarebenchmark.

## Automatisk større labyrinter

Etter kjøringen til generasjon 7000 koblet vi mestringskontrollen inn i API-treneren. Hver femte generasjon kontrolleres den valgte modellen på nye labyrinter. Kravet er 20 feilfrie gjennomføringer på rad med samme modell før begge dimensjoner økes med 50 %.

Funksjonen er kontrollert med tester av både økning, blokkering etter feil og videre trening etter størrelsesbytte. I en kontroll med den faktiske modellen på 20 nye labyrinter løste den 8. Den ble derfor stående på 8×8. De fullførte 2000- og 5000-kjøringene ovenfor ble ikke kjørt med denne nye automatiske økningen.

## Hvorfor assistert læring er neste forslag

Forsøkene viser at flere generasjoner, større nett og endret belønning ikke alene garanterer jevn fremgang. Kandidatutvalget har dessuten brukt bare to labyrinter per generasjon, slik at en kandidat kan vinne på et lite sett uten å bli bedre generelt.

Forslaget er å la treningssystemet kjenne løsningen og trekke punkter fra hele ruten med korrekt historikk og riktig neste handling. Da kan modellen øve på sene forgreninger før den selv klarer veien dit. Dette er dokumentert i [Assistert læring fra kjente ruter](ASSISTERT_LARING.md), men er ennå ikke implementert eller resultatmålt. Neste forsøk må også undersøke hvor ofte samme tilgjengelige input har motstridende fasit i forskjellige kart.

## Sammenligning med AlphaStar

AlphaStar, DeepMinds StarCraft II-prosjekt, startet med veiledet læring fra menneskelige spillopptak og trente deretter gjennom forsterkningslæring mot en liga av agenter. Det ga et utgangspunkt med spillkunnskap før videre utforsking. [DeepMind, januar 2019](https://deepmind.google/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii).

I den senere versjonen brukte ligaen også agenter som avdekket svakheter, og imitasjonsbaserte metoder bidro til å bevare strategier under videre trening. [DeepMind, oktober 2019](https://deepmind.google/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/).

Vår sammenligning er derfor: lær først fra gode eksempler, og øv deretter selvstendig. Den dokumenterer ikke at AlphaStar brukte akkurat vårt foreslåtte opplegg med tilfeldige rutepunkter og eksplisitte historikkbrikker. Våre demonstrasjoner kan genereres av en rutealgoritme; menneskelige spill er ikke nødvendig her. Detaljert forskningskilde: [Vinyals mfl., Nature, 2019](https://doi.org/10.1038/s41586-019-1724-z).

## Grunnlaget for målingene

Råfiler ligger lokalt i `.ai-service/` og er forsøksartefakter; de følger ikke nødvendigvis med et klonet repository. Resultatene som brukes her er derfor også skrevet ut i tabellen over.

| Tema | Lokal kilde under `.ai-service/` |
| --- | --- |
| Dypt nett og avbrutt kjøring | `deep-history-23.json`, `deep-400-interrupted-state.json` |
| Handlingsfordeling før/etter normalisering | `action-diagnostics.json`, `action-diagnostics-normalized.json` |
| Tomt minne og bakovervalg | `backward-weight-diagnosis.json` |
| Kandidatvalg og samsvar med opptak | `selection-audit.json`, `bits2-training-audit.json` |
| To utganger med eldre regler | `bits2-50-analysis.json` |
| Strenge regler, 50 og 20 til | `bits2-strict-50-analysis.json`, `bits2-strict-next20-analysis.json` |
| Åtte følere, 2000 til | `bits2-strict-headless2000-analysis.json` |
| Fire følere, 2000 og 5000 til | `four-rays-headless2000-analysis.json`, `four-rays-next5000-analysis.json` |
| Kontroll før eventuell størrelsesøkning | `curriculum-check-g7000.json` |

Denne oppdateringen endrer bare dokumentasjonen. Den starter ikke et nytt forsøk og endrer ikke modellen.


## Oppfølging: demonstrasjoner fra eksisterende gåmodell

Etter forslaget om assistert læring ble 1000 sensoriske kjøringer gjennomført med
den bevarte gåmodellen fra generasjon 3000, med alle minneinnganger nullstilt.
På 8×8-kart nådde 529 forsøk utgangen (52,9 %). De ga 4989 merkede steg med
fireføler-historikk til sluttnettet. 469 vellykkede ruter er satt av til trening
og 60 til kontroll; ingen veggoppsett forekommer i begge delene.

Dette er datainnsamling, ikke en ny trening av sluttmodellen. Alle vellykkede ruter
ble rekonstruert og kontrollert. Se [innsamlingsrapport og kjørekommando](ASSISTERT_LARING.md#første-innsamling-1000-forsøk).


Neste innsamling utvidet dette til **5000 forsøk fordelt likt på fem størrelser**
(5×5, 8×8, 12×12, 15×15, 18×18). Den ga **2079 vellykkede ruter og 36 688 merkede
steg**. Treffraten på de to største størrelsene var 30,4 % og 28,3 %. Alle
vellykkede steg og nullutfyllingen til felles inputbredde ble kontrollert.
[Fordeling og dataformat](ASSISTERT_LARING.md#utvidet-grunnmateriale-5000-forsøk-på-flere-størrelser).


## Første assistert trening med kun handlingsfasit

Det første forsøket videreførte historikkmodellen fra generasjon 7000 i 200 nye
generasjoner. Hver generasjon brukte 128 tilfeldig valgte punkter fra vellykkede
treningsruter, med full historikk. **Kun +1 ved riktig neste handling og −1 ellers**
ble brukt som fitness, uten simulatorpoeng eller delpoeng for én riktig bit.

På 3142 punkter fra separate kontrollkart økte nøyaktigheten fra **83,70 % til
86,63 %** (2630 til 2722 riktige). Dette er en måling av handlingsvalg, ikke løste
labyrinter. Alle treningspunkter og siste generasjons kandidatvalg er kontrollert.
Oppsett og begrensninger finnes i [Assistert læring](ASSISTERT_LARING.md#første-resultat-med-bare-rutepunkt-belønning)
og `.ai-service/route-match-200-v1/`.
