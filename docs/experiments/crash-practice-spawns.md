# Øvingsstarter før veggkrasj

Endring 71, 8. november 2026. Målet er flere forsøk på innkjøringer der bilen
tidligere har feilet, slik at den kan lære å forberede styring og bremsing.

## Hvordan punktene oppstår

Ved et faktisk veggkrasj lagres treffstedet på veikanten og bilens posisjon,
høyde, retning og fart ti billengder tidligere langs den kjørte banen.
Billengden følger bilens fysiske kollisjonsdiameter: 14 banenheter, altså
140 enheters faktisk tredimensjonal kjørelengde. Historikken interpoleres
til denne avstanden; den måles ikke som en rett linje fra veggen.

Krasj før bilen har kjørt 140 enheter, eller med et utrygt innkjøringspunkt,
lager ikke et kunstig punkt. Nærliggende krasj på samme veistrekning og i
samme retning samles til ett punkt. Dette nullstiller aldri forsøksgrensen.

## Hvordan punktene brukes

- Ved et nytt treningsoppdrag trekkes en lagret start med sannsynlighet 10 %.
  Resten bruker vanlige tilfeldige starter. Mangler et ledig, egnet punkt,
  brukes også en tilfeldig start.
- Hvert punkt får maksimalt 20 **fullførte** forsøk, uansett om forsøket
  ender med krasj eller når steggrensen. Pågående forsøk reserverer plass i
  kvoten, slik at flere biler samlet ikke kan overskride 20.
- Banegeometri, høyde og kjøreretning holdes adskilt. Bilen gjenopptar den
  lagrede retningen og relative farten, innenfor gjeldende fartsgrenser.
  Hele gruppen beholder felles kjøreretning.
- Etter hvert avsluttet oppdrag får bilen en ny start. Tidligere videreføring
  av overlevende biler er slått av i denne serien for å gi samme trekning
  også etter turer som når steggrensen.
- Punkter og tellere lagres i SQLite mellom generasjoner og prosessbytter.
  Ufullførte reservasjoner frigjøres når den forrige treneren er stoppet og
  en ny prosess starter. Faste evalueringer bruker fortsatt sine egne starter.

I kartet er veikanttreffet et kryss og øvingsstarten en ring, knyttet sammen
med stiplet linje. Telleren viser fullførte forsøk av 20. Punktinformasjonen
viser også pågående forsøk, retning og høyde. Grå punkter er ferdig brukt
eller tilhører motsatt retning. Kartet viser opptil 128 nyere punkter per bane;
databasen beholder hele historikken.

## Kontroller før videre trening

Modellen fra generasjon 31 kjørte egne oppdagelsesturer med samme
utforskingsstøy som treningen. Dette ga minst to ekte punkter per retning
på hver av de seks banene: 24 innledende punkter, alle med ubrukt kvote.
Disse turene trente ikke modellen.

En isolert kortprøve på en kopi av databasen gjennomførte 12 lagrede starter,
to på hver bane. Alle 12 ble fullført og telt, og ingen reservasjoner ble
hengende igjen. Her var andelen midlertidig satt til 100 % for å prøve hele
kjeden; ordinær trening bruker 10 %. Dette er en funksjonskontroll, ikke
en måling av bedre læring.

Alle **186 V2-tester består**, inkludert avstandshistorikk, lagring og
gjenåpning, 20 samtidige reservasjoner, grensen etter gjentatte krasj,
bane- og retningsskille, omtrent 10 % trekning, og en komplett
trenersyklus fra oppdagelse til fullført repetisjon. JavaScript i visningen
er syntakskontrollert med Node.

Oppstarten og det videre treningsløpet er registrert i
`crash-practice-spawns.json`. Den nye prosessen bruker
`--crash-spawn-share .1 --crash-spawn-db .ai-service/car-wall-crash-practice.sqlite`.
Belønning, sensorer, nettverksarkitektur og faste evalueringsstarter er
uendret. Et prosessbytte viderefører modellvektene, mens Adam og baseline
starter på nytt én gang og deretter beholdes mellom baner og generasjoner.

Byttet er planlagt automatisk etter at generasjon 32 er ferdig evaluert og
registrert, med første nye generasjon 33. Dermed beholdes arbeidet i den
pågående generasjonen. Oppstartsstatus lagres lokalt i
`.ai-service/car-crash-practice-activation.json`, og samme treningsvisning
på port 50386 kobles til den nye kjøringen.

Eventuell læringsgevinst må vurderes med videre faste kontrollresultater
per bane, inkludert kjørelengde og belønning selv om turene ender i krasj.
