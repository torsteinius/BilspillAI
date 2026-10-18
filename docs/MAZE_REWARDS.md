# Straff, belønning og historikk i labyrinttreningen

Oppdatert 18. oktober 2026. Gjelder `HistoryEpisode` med deterministisk historikk, brukt av `games.maze.remote_ai_app`. Tallene nedenfor er de **strenge reglene** (`reward_version=strict_v3`), brukt av den ferske modellen `.ai-service/history-5-bits2-strict.json`. Eldre modellfiler beholder sine lagrede regler (veggtreff −5, gjenbesøk −0,05, `min_steps=20`). Reglene er uavhengige av antall skjulte lag. Se avsnittet «Strenge regler» nederst for begrunnelsen.

Et foreslått neste opplegg er beskrevet i [Assistert læring fra kjente ruter](ASSISTERT_LARING.md). Det bruker fasit ved enkeltpunkter og er foreløpig ikke implementert; reglene på denne siden gjelder fortsatt dagens trening.

## Fire følere og dempet historikk

Modellen `history-4rays-decay75-v1` bruker fire normaliserte sensoravstander:
frem, høyre, bak og venstre (0°, 90°, 180°, 270° relativt til figurens retning).
Fem skjulte lag, to bevegelsesutganger og de strenge reglene beholdes.
Inngangen på 8×8-kart har 148 verdier.

| Inngangsgruppe | Innhold | Faktor |
| --- | --- | ---: |
| 1 (inngang 1–4) | Sensorene her og nå | 1,00 |
| 2 (inngang 5–8) | Sist registrerte hjørne/kryss | 0,75 |
| 3 | Nest siste registrering | 0,5625 |
| 4 | Tredje siste registrering | 0,421875 |
| 5 | Fjerde siste registrering | 0,31640625 |
| 6 og videre | Eldre registreringer | 0,25 |

For minneplass nummer `k` etter dagens sensorer er faktoren `max(0.25, 0.75**k)`.
Nye registreringer legges først i minnedelen av inngangen og flytter eldre bakover.
Lagrede råmålinger endres ikke; vektingen beregnes når inngangen bygges, slik at den
ikke dempes gjentatte ganger bare fordi flere steg går. Tomme plasser forblir null.
Dette skalerer inputverdier, men garanterer ikke at lærte vekter gir dagens sensorer størst innflytelse.

Rekkefølge, antall følere og vekting lagres i checkpoint-konfigurasjonen.
Eldre modeller lastes fortsatt med åtte følere, eldste registrering først og faktor 1.

## Poeng per handling

Den nye modellen bruker **to utgangsnevroner** (`history_output_encoding=bits2`).
Hver tanh-utgang blir bit 1 ved verdi > 0, ellers bit 0:
**00 = bak, 01 = høyre, 10 = venstre, 11 = frem**.
Bak betyr å snu 180° og forsøke å gå én rute. Treningsforsøk og avspilling
bruker samme dekoder; opptaket inneholder både råverdier, bit og valgt handling.
Eldre fireutgangsmodeller beholder sin opprinnelige argmax-tolkning.

| Hendelse | Poeng | Nøyaktig betingelse |
| --- | ---: | --- |
| Utgang | +100 | Agenten flytter inn på utgangsruten. Forsøket avsluttes umiddelbart. |
| Nytt hjørne eller ny forgrening | +1 | Første ankomst til denne posisjonen i forsøket. Startposisjonen gir ingen slik bonus, heller ikke ved retur. |
| Ny rekord i avstand til utgangen | +0,25 per rute forbedring | Avstanden blir mindre enn den laveste avstanden tidligere i samme forsøk. |
| Ny rute | +0,20 | Første besøk på en gangbar rute, også utenfor den korteste stien. |
| Bevegelse bort fra utgangen | −0,05 | Avstanden til utgangen øker sammenlignet med posisjonen før handlingen. |
| Gjenbesøk | −0,30 | Agenten flytter inn på en allerede besøkt rute. Koster mer enn en ny rute gir (+0,20). |
| Veggkontakt | −2 | Den valgte bevegelsen treffer en vegg. Posisjonen endres ikke. Forsøket avsluttes straks. |
| Gjentatt tilstand | −2 | Samme posisjon, retning og hele historikk som i en tidligere registrert tilstand (også starttilstanden). Forsøket avsluttes straks. |

Avstanden er korteste gangbare vei til utgangen, ikke luftlinje. Simulatoren beregner avstand for framgangsbonusen; nettet får ikke denne avstanden som input. Ny-rute-bonusen er uavhengig av den skjulte løsningsstien.

Poengbidrag summeres når betingelsene overlapper. Eksempler:

- Ny vanlig rute som forbedrer avstandsrekorden med én: **+0,45**.
- Samme situasjon på et nytt hjørne eller en ny forgrening: **+1,45**.
- Retur til en besøkt rute som samtidig øker avstanden: **−0,35**.
- Ny utgangsrute som forbedrer avstandsrekorden med én: **+100,45**. Utgangsruten regnes ikke som et hjørne eller en forgrening.

Gjenbesøk får ingen positiv framgangs-, ny-rute- eller landemerkebonus. Startposisjonen teller allerede som besøkt. Et nytt besøk nærmere utgangen gir dermed −0,30, og et nytt besøk lenger fra utgangen −0,35. Løkkestraffen på −2 kommer i tillegg dersom besøket gjentar en tidligere tilstand. En helt ny rute som ligger lenger fra utgangen gir +0,20 −0,05 = +0,15, pluss eventuell landemerkebonus.

Veggkontakt bruker sin egen gren i poengberegningen: den gir ikke samtidig gjenbesøksstraff eller tilbakegangsstraff. Når veggkontakt avslutter forsøket, legges heller ikke en ekstra løkkestraff på. Løkkestraff etter en vellykket bevegelse kan derimot komme i tillegg til bevegelsens øvrige poeng.

## Hva er et hjørne eller en forgrening?

Kun vanlige gangbare ruter (`.`) klassifiseres. Simulatoren undersøker de fire direkte nabocellene; både vanlig gulv og utgang teller som åpning.

- **Hjørne:** nøyaktig to åpninger som står vinkelrett på hverandre.
- **Forgrening:** tre eller fire åpninger.
- **Rett korridor:** to motstående åpninger; ingen landemerkebonus eller historikkoppføring.
- **Blindvei:** én åpning; ingen landemerkebonus eller historikkoppføring.

Klassifiseringen er geometrisk. Det tidligere fryste detektornettet brukes ikke til denne avgjørelsen i gjeldende `HistoryEpisode`.

## Historikk

Bare hjørner og forgreninger lagres, én gang per fysisk posisjon. En oppføring inneholder modellens fire eller åtte normaliserte sensoravstander med retningen agenten hadde da stedet ble registrert. Den nye modellen gir nettet nyeste registrering først, som beskrevet over. Koordinater brukes internt til å unngå duplikater, men sendes ikke til nettet.

Bonus og minneskriving skjer på ulike tidspunkter:

1. Agenten når et nytt landemerke og får bonus på ankomststeget.
2. Ved neste beslutning får nettet dagens sensorer og tidligere historikk.
3. Etter at nettet har valgt handling, registreres sensorbildet fra det aktuelle landemerket, før bevegelsen utføres.
4. Den nye oppføringen blir tilgjengelig for nettet ved neste beslutning.

Et landemerke på startposisjonen kan registreres i minnet selv om det ikke gir ankomstbonus. Historikk, besøksregistrering og bonusregistrering nullstilles for hver labyrint. Historikken overskrives ikke; ubrukte inputplasser fylles med null.

## Når avsluttes et forsøk?

Den aktuelle modellen bruker `until_failure=true` og `min_steps=0`:

- Utgang avslutter umiddelbart.
- Første veggkontakt avslutter forsøket med −2.
- Første gjentatte tilstand avslutter forsøket med −2. To «bak» på rad i en korridor uten nytt landemerke gjentar starttilstanden og avslutter dermed etter to steg.
- Det finnes ingen generell tidsgrense. Forsøket fortsetter så lenge agenten unngår vegg og gjentatte tilstander.
- `max_steps=128` brukes ikke når `until_failure=true`. I modusen med `until_failure=false` avsluttes forsøket ved `max(max_steps, min_steps)`, uten egen sluttstraff.

Med `min_steps>0` (eldre modeller) gir veggkontakt og gjentatt tilstand straff uten å avslutte før steget er nådd.

Det gis ingen separat straff bare for å svinge eller stå stille, og ingen generell fremoverbonus i denne varianten. Feltene `turn_penalty`, `stationary_penalty` og `forward_reward` finnes i den felles konfigurasjonen, men brukes ikke av denne bevegelsesmodellen.

## Hvordan poengene brukes i trening

Hvert forsøk summerer poengene fra alle handlingene. Kandidatens fitness er gjennomsnittet av sluttpoengene over generasjonens labyrinter. Alle kandidater evalueres på de samme labyrintene innen én generasjon; neste generasjon får nye labyrinter.

Vektene endres ikke per handling. API-et beregner bare nettets svar under forsøket. Når alle kandidatene er ferdige, sendes fitness til `tell`; kandidaten med høyest score blir vinner. Neste `ask` beholder vinneren og lager muterte kopier. Ingen backpropagation brukes.

Enkeltgenerasjoners score er derfor ikke en kontrollert måling av læringsfremgang på tvers av generasjoner: labyrintene skifter. Separate, faste evalueringslabyrinter trengs for en slik sammenligning.

## Konfigurasjon og kildekode

Aktuelle verdier: `progress_reward=0.25`, `exploration_reward=0.2`, `landmark_reward=1.0`, `backtrack_penalty=0.05`, `revisit_penalty=0.3`, `wall_penalty=2.0`, `min_steps=0`, `exit_reward=100.0`. `wall_penalty` brukes både for veggkontakt og gjentatt tilstand.

Modellens lagrede `config.rules` brukes ved lasting. Manglende felter får standardverdier fra `Rules`; den aktuelle modellfilen mangler `landmark_reward` og får derfor standardverdien **1.0**. Den generelle standardverdien for `revisit_penalty` er 0.5, men denne modellen lagrer **0.3**, som dermed brukes. `games.maze.app` bruker de strenge verdiene som standard for nye modeller med deterministisk historikk.

- [Poengberegning og avslutning](../games/maze/memory.py): `MemoryEpisode.step`.
- [Landemerker, bonus og historikk](../games/maze/history.py): `HistoryEpisode`.
- [Regelfelter og standardverdier](../games/maze/world.py): `Rules`.
- [Kandidatfitness og API-flyt](../games/maze/remote_ai_app.py): `LocalRunner.run`.
- [Utvalg og mutasjon](../ai_engine/src/ai_engine/evolution.py): `EvolutionSession`.
- [Regeltester](../tests/test_history.py).

## Forsøk med fryste minnevekter — 18. oktober 2026

Den separate modellen `history-5-frozen-v1` har fem skjulte lag. Alle forbindelser fra de 288 minneinngangene til første skjulte lag starter på null. `mutation_active_inputs` i checkpointet angir hvilke innganger som er åpnet for mutasjon; de åtte nåværende sensorene er aktive fra starten.

Klienten teller fylte minneplasser ved hver faktisk inferensforespørsel. På slutten av generasjonen sender den `used_inputs` til `tell`: unionen av brukte innganger for alle kandidater og labyrinter. Aktivering bygger på plassens tilstedeværelse, ikke på om sensorverdien er ulik null. Minne som først blir skrevet ved siste handling, men aldri sendt til nettet, teller ikke som brukt.

En plass som brukes for første gang, har fortsatt nullvekter gjennom den generasjonen. Fra neste `ask` kan disse vektene muteres. Aktivering er varig og lagres både i økten og checkpointet; den følger med ved omstart og nye økter. En tidligere aktivert plass fryses ikke på nytt i generasjoner der den tilfeldigvis ikke brukes. Biaser og senere lag trenes som før.

Dette hindrer tilfeldig drift før første bruk. Det garanterer ikke bedre læring og er ikke en separat minnegren gjennom alle lag. Vanlige modeller uten `mutation_active_inputs` beholder tidligere mutasjonsoppførsel. Forsøket gjelder det generelle evolusjons-API-et og `remote_ai_app`, ikke den eldre treningsløkken i `NeuralNetwork.train`.

Opprett en fersk forsøksmodell fra prosjektroten:

```sh
.venv-gpu/bin/python -m scripts.create_deep_history_model --hidden-layers 5 --freeze-unused-memory --output .ai-service/history-5-frozen.json
```

Kommandoen nekter å overskrive en eksisterende fil. Tester i `tests/test_memory_freeze.py` kontrollerer nullvekter før aktivering, aktivering uavhengig av sensorverdi, fortsatt mutasjon av bias og senere lag, validering, idempotens og videreføring etter omstart.

## Rettelse av mutasjonsgenerator — 18. oktober 2026

Det generelle API-et rekonstruerer `EvolutionSession` mellom kall. Tidligere ble tilfeldighetsgeneratoren da startet med samme seed hver generasjon. Ved uendret mutasjonsmaske ble de samme mutasjonsmønstrene gjentatt, selv om vinnervektene kunne endre seg. Dette var en feil i utforskningen, ikke en feil i nullutfyllingen av minnet.

Mutasjonsstrømmen avledes nå fra både seed og generasjon. Nye API-økter bruker checkpointets generasjonsnummer som startoffset. Tester bekrefter nye mutasjoner mellom generasjoner, reproduksjon etter rekonstruksjon og korrekt videreføring i en ny økt. Tidligere treningsresultater dokumenterer ikke effekten av den korrigerte algoritmen.

## Normalisert nett — 18. oktober 2026

Forsøksmodellen `history-5-normalized-v1` bruker `normalization=layernorm_hidden_v1`. I hvert skjulte lag beregnes først `z = xW + b`, deretter `tanh((z - mean(z)) / sqrt(mean((z - mean(z))²) + 1e-5))`. Gjennomsnitt og varians beregnes over nevronene i laget, separat for hver observasjon og kandidat. Ingen lærbare skala-/forskyvningsparametere legges til. Utgangslaget beholder vanlig `tanh(xW + b)` og argmax.

CPU-referansen og begge GPU-inferensbanene bruker samme regel. Innstillingen følger checkpoint og økter; gamle modeller uten feltet beholder gammel beregning. Normalisering kontrollerer skjulte lags nivå og spredning, men garanterer ikke like handlingssannsynligheter eller god læring. Forsøket starter med nye vekter, fem skjulte lag og fryste ubrukte minnevekter. Mutasjonssigma 0.12, bias-mutasjon, fire kandidater og to labyrinter beholdes for å isolere endringen i beregningen.

## Kontroll av utvalg og avspilling — 18. oktober 2026

Generasjon 150 i `history-5-normalized-v1` ble rekonstruert fra checkpoint 149, lagret seed, mutasjonsmaske og de to evalueringslabyrintene. Fitness for kandidat 0–3 ble henholdsvis −8.45, −77.625, −33.075 og −4.45. Kandidat 3 ble valgt; samtlige lagrede vekter var identiske med den rekonstruerte kandidaten, og filens hash stemte med modellregisteret. Dette bekrefter koblingen mellom simulatorens score og lagret vinner for denne generasjonen, men sier ikke at treningsmetoden gir god generalisering.

På 64 separate valideringslabyrinter klarte den opprinnelige normaliserte modellen 7 utganger, mens modellen etter 150 generasjoner klarte 1. Den trente modellen valgte bakover i 1251 av 1265 handlinger. To labyrinter per generasjon er utilstrekkelig som bevis på generell fremgang; det generelle API-et velger etter innsendt fitness og har ingen separat valideringsport.

`remote_ai_app --record-all` beholder nå alle kandidat/labyrint-opptak fra hver generasjon. Visningen spiller i rekkefølgen generasjon, kandidat, labyrint, uten å hoppe når treningen går videre. `/api/state` gir `attempt_count`, mens `/api/attempts/<indeks>` henter ett opptak. Visningen merker kandidaten med egen score og om den ble valgt videre. Opptaksdataene inneholder også gjennomsnittlig kandidatfitness. Opptak fra kandidater som ikke ble valgt er ikke vinnercheckpoints. Opptakene ligger i prosessminnet; forsøket med 50 generasjoner ble også eksportert til `.ai-service/random-visible-50-attempts.jsonl`.

## Ny-rute-bonus — 18. oktober 2026

Den deterministiske historikkvarianten belønner nå første besøk på alle gangbare ruter med `exploration_reward=0.2`, fremfor bare første besøk på den skjulte løsningsstien. Gjenbesøk kan ikke utløse framgangsbonus eller landemerkebonus. Tidligere opptak og målinger i dette dokumentet stammer fra reglene før denne endringen; de er ikke regnet om. `path_reward` beholdes for den eldre varianten med lærbart minne.

## Strenge regler — 18. oktober 2026

**Problemet.** Med de gamle reglene valgte trente modeller nesten bare «bak» og pendlet mellom to ruter. Årsaken var ikke en feil i simulator eller avspilling, men poengstrukturen. «Bak» fører nesten alltid til ruta agenten kom fra, som er åpen. Det er dermed den eneste handlingen som er trygg uten å bruke sensorene. Samtidig ga hver veggkontakt −5 uten å avslutte før steg 20, slik at et nett som prøvde seg fram kunne tape opptil −100. Pendling kostet bare rundt −10, og gjenbesøk kostet bare −0,05.

Faste strategier på 200 labyrinter (9×9) med de gamle reglene:

| Strategi | Snittpoeng | Utganger |
| --- | ---: | ---: |
| Alltid frem | −95 | 1 |
| Tilfeldig | −55 | 6 |
| Alltid høyre / venstre | −55 | 0 |
| Alltid bak (pendling) | −50 (median −11) | 0 |
| Tilfeldig uten veggkontakt | +71 | 120 |
| Høyrehåndsregel | +115 | 200 |

Pendling slo altså alle blinde strategier. Mellomtrinnene mellom et utrent nett og en god strategi fikk dårligere poeng enn pendlingen, så seleksjonen fant ikke veien videre.

**Endringen.** Veggkontakt og gjentatt tilstand avslutter straks med −2 (`min_steps=0`), og gjenbesøk koster −0,30. Med disse reglene får alle blinde strategier rundt −2. Pendling gir ikke lenger noen fordel, og hver ny rute agenten klarer før første feil gir mer poeng. De gode strategiene beholder sine poeng (+71 og +113).

Testene ligger i `tests/test_strict_rules.py`. Ny ferskmodell med tilfeldige vekter: `.ai-service/history-5-bits2-strict.json`. Den har samme arkitektur som `history-5-bits2-v1` (fem skjulte lag, `bits2`, normalisering og fryste ubrukte minnevekter):

```sh
python3 -m scripts.create_deep_history_model --source .ai-service/history-5-bits2-v1.json --output .ai-service/history-5-bits2-strict.json --hidden-layers 5 --freeze-unused-memory --normalize-hidden --output-encoding bits2 --seed 7 --min-steps 0 --wall-penalty 2 --revisit-penalty 0.3 --reward-version strict_v3
```

Fire kandidater og to labyrinter per generasjon gir fortsatt mye tilfeldighet i utvalget. Det er ikke endret her.


## Automatisk større labyrinter i API-treningen

API-treneren kontrollerer den valgte modellen hver femte generasjon (`check_every`).
Kontrollen bruker nye labyrinter fra en egen valideringssekvens, og de samme vektene
under hele kontrollen. Poengene her brukes ikke til å velge eller mutere kandidaten.

Modellen må nå utgangen uten kollisjon eller fastlåsing på **20 labyrinter på rad**
(`success_streak`). En feil nullstiller rekken. Rekken starter på nytt ved hver
kontroll, slik at resultater fra forskjellige modeller ikke blandes.

Når kravet er oppfylt, økes begge dimensjonene med 50 %, avrundet opp:
**8×8 → 12×12 → 18×18 → 27×27**. API-treneren utvider antall nivåer etter behov.
Enkeltseire under trening eller høy belønning alene utløser aldri økning.

Den faktiske valgte modellen hentes fra API-et før utvidelsen. Tidligere vekter og
kontrollpunkt beholdes. For nett med normaliserte skjulte lag utvides bare
minneinngangene; nye forbindelser starter på null og er fryst til de får reelt
input. Skjulte lag beholder størrelsen, slik at større lag ikke endrer
normaliseringen av det som allerede er lært. Sensorverdiene normaliseres fortsatt
etter labyrintens størrelse. Det nye nivået får en ny treningsøkt med riktig
inngangsbredde. Lokal gjenopptakingsmodell oppgis i statusfeltet `curriculum_model`.
