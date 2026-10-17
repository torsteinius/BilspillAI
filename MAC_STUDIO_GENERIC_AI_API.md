# Oppdrag til ChatGPT på Mac Studio om et generelt AI API

## Korrigert mål fra brukeren

Utvid den eksisterende AI-tjenesten med en generell API-variant hvor appene sender data inn, får nettverksoutput tilbake og lar Studio håndtere vekter og trening på GPU.

MacBook skal nå kjøre labyrintmotor, sensorer, bevegelse, belønning og visning. Studio skal kjøre AI-delen. Tjenesten skal også kunne brukes av bilspillet og fremtidige apper uten å kjenne deres spilleregler.

Behold eksisterende `/training-runs` for valgfri kjøring av hele labyrintforsøk på Studio. Ikke erstatt eller stopp eksisterende jobber uten å kontrollere status og behov. Legg til generelle endepunkter ved siden av disse. Ikke gjør labyrintadapteren til en obligatorisk avhengighet for det nye API-et.

Dette dokumentet er en implementeringsbestilling. Endepunktene nedenfor er forslag som må bygges og testes; de finnes ikke nødvendigvis allerede.

## Obligatorisk isolering og to kjøremåter

AI-delen skal trekkes ut i en egen katalog og kunne brukes av mange forskjellige programmer. Dette er et arkitekturkrav, ikke bare et nytt endepunkt i labyrintserveren.

Foreslått struktur, tilpasset eksisterende kode etter inspeksjon:

```text
ai_engine/
  pyproject.toml
  src/ai_engine/
    models/          # Nettverkstyper og vekter
    backends/        # MLX og eksplisitt valgt enhet
    training/        # Generelle treningsalgoritmer
    registry/        # Modellversjoner og persistens
    api/             # Generelt HTTP-API
    client/          # Klient som kan brukes fra andre programmer
  tests/
  README.md

ai_service/          # Kompatibilitet og valgfrie jobber på Studio
  adapters/          # Kobler spill til AI-delen utenfor ai_engine

games/
  maze/              # Miljø, belønning og visning
  car/
```

Pakken skal kunne installeres og testes alene, med dokumenterte avhengigheter. Klienten på MacBook skal ikke kreve MLX bare for å sende HTTP-forespørsler. GPU-avhengigheter hører til server/backend-installasjonen. Runtime-data og modellager skal ha konfigurerbar plassering, uten hardkodede bruker- eller iCloud-stier.

Avhengighetsretningen er én vei: spill og jobbadaptere bruker ai_engine. ai_engine skal ikke importere games, kjenne labyrintregler eller kreve spillfiler for å starte. app_id er generell metadata for eierskap og organisering, ikke en hardkodet liste over kjente spill. En klient må kunne registrere et nettverk for en helt annen oppgave og bruke inferens/trening uten endring i AI-tjenestens kode, så lenge nettverkstype og treningsmetode støttes.

Begge kjøremåter skal beholdes:

1. **Delt kjøring:** app/simulering på MacBook eller Mac Mini, AI på Studio gjennom det generelle API-et.
2. **Samlet kjøring på Studio:** en separat jobb kjører appens simulering på Studio og bruker den samme AI-kjernen. Den kan bruke det offentlige Python-grensesnittet direkte for å unngå lokal HTTP-kostnad. Modellformat, algoritmer, versjonering og resultater skal være de samme; ikke lag en ekstra kopi av treningslogikken.

Det eksisterende spillspesifikke jobb-API-et kan fungere som et kompatibilitetslag over disse adapterne. Det skal ikke være det generelle AI-API-et sin kjerne. Under migreringen må eksisterende importveier og checkpointformater fortsatt fungere eller få dokumentert, testet migrering. Bruk kompatibilitetsmoduler når det er nødvendig, fremfor å bryte spillene i én stor flytting.

Test isoleringen ved å installere AI-pakken i et rent miljø uten games og kjøre registrering, inferens og en liten syntetisk treningsoppgave. Test deretter begge kjøremåtene med samme modell og kontrollert input. Isoleringen skal gjøre en senere flytting til eget Git-repo mulig, men opprett ikke et nytt repo bare for å oppfylle katalogkravet.

## Måling av tiden på Studio

API-svar skal kunne inkludere request_id, batchstørrelse, backend, checkpointversjon og separate tidsmålinger for køventing, modellberegning og total behandling på Studio. MacBook måler i tillegg samlet tid fra forespørsel til svar med sin lokale monotone klokke.

MLX evaluerer operasjoner utsatt. Beregningstiden må derfor omfatte eksplisitt evaluering/synkronisering; ikke mål bare hvor fort GPU-arbeid legges i kø. Kall dette beregningsveggtid hvis målingen også inkluderer dispatch eller synkronisering. Bruk betegnelsen ren GPU-kjernetid bare dersom den faktisk måles med egnet profileringsverktøy. Mål initialisering/oppvarming separat fra normal drift.

Forskjellen mellom klienttid og rapportert servertid er et anslag på transport og arbeid utenfor den målte serverdelen, ikke ren nettverkslatens. Klokkene på maskinene trenger ikke være synkronisert når hver varighet måles lokalt. Bruk målingene til å sammenligne nettverksstørrelser og batchstørrelser i begge kjøremåter.

## Ansvarsdeling

MacBook eier miljøtilstand, labyrintgenerering, sensorer, deterministisk besøkshistorikk, handlingsvalg fra output, belønning og avslutning av forsøk. MacBook sender ferdig normaliserte inputvektorer. Koordinater og kart er ikke nødvendige for AI-tjenesten.

Studio eier nettverksregister, versjonerte vekter, GPU-inferens, kandidatpopulasjoner, utvalg, mutasjon og andre eksplisitt støttede treningsalgoritmer. For fremtidig gradientbasert trening skal også tap, gradienter og optimizer kjøres der.

Appen og AI-tjenesten kommuniserer i batcher. En batch kan inneholde mange uavhengige boter, labyrinter og kandidater. Behold vekter på Studio mellom forespørsler. Ikke overfør vektene for hvert spillsteg.

Ikke flytt spillmotoren til Studio for å omgå nettverksforsinkelse i denne varianten. Flere lokale miljøer og større batcher er tillatt. Den gamle varianten med fjernsimulering kan fortsatt tilbys separat.

## Nåværende kode og modell

Finn faktisk prosjektmappe og les lokale instruksjoner først. På Studio er prosjektet tidligere rapportert under:

`~/Library/Mobile Documents/com~apple~CloudDocs/Documents/GitHub/BilspillAI`

Relevant kode:

- `ai_service/server.py`: eksisterende register og treningsjobber.
- `ai_service/client.py`: eksisterende Python-klient.
- `ai/network.py`: tett tanh-nett og evolusjonstrening.
- `ai/mlx_backend.py`: batchet nettverksberegning på GPU.
- `games/maze/training.py`: dagens klient-/spillspesifikke evaluering og progresjon.
- `games/maze/history.py`: deterministisk historikk på app-siden.

`maze-history-v1` er allerede registrert. Finn siste gyldige checkpoint og aktive jobber via faktisk register; ikke anta generasjon eller filnavn fra eldre dokumenter. Lag en separat modell-ID, for eksempel `maze-history-api-v1`, som kopi av siste ferdige checkpoint til utprøving av det generelle API-et. Bevar originalen og dens jobber.

Dagens labyrintnett bruker tett tanh, normalt fire output i rekkefølgen frem, tilbake, høyre, venstre. Ved 8 × 8 var arkitekturen `[296,223,150,77,4]`. Les arkitekturen fra filen. Input begynner med åtte aktuelle følerverdier og fortsetter med registrerte målinger fra tidligere steder. Dette formatet bygges av appen, ikke av AI-serveren.

## Modellregister

Støtt registrering/import av en generell modell med:

- `network_id` og `app_id`.
- `network_type`, i første versjon `dense_tanh`.
- Faktisk `architecture`, dtype og checkpointversjon.
- Navngitt input-/outputskjema som metadata, ikke spillkode.
- Eksplisitt tillatte treningsmetoder, først `evolution`.
- Backend `mlx-gpu` og en tydelig status for tilgjengelig Metal-enhet.

Gjenbruk registeret der det passer. Ukjent nettverkstype eller treningsmetode skal gi en forståelig feil. Ikke lov LSTM, RL eller supervised-trening før hver metode faktisk er implementert.

## Generell inferens

Foreslått endepunkt:

`POST /v1/networks/{network_id}/predict`

Eksempel med to inputvektorer, forkortet her for lesbarhet:

```json
{
  "checkpoint_id": "en-bestemt-versjon",
  "inputs": [[0.2, 0.4], [0.7, 0.1]],
  "request_id": "predict-001"
}
```

Eksemplet viser strukturen, ikke gyldig inputbredde for labyrintmodellen. Hver rad skal ha nøyaktig modellens inputbredde.

Svar:

```json
{
  "network_id": "maze-history-api-v1",
  "checkpoint_id": "en-bestemt-versjon",
  "backend": "mlx-gpu",
  "outputs": [[0.8, -0.1, 0.2, -0.4], [0.1, 0.7, -0.3, 0.2]]
}
```

Valider endelige tall, batchstørrelse, dimensjoner og valgt versjon. Returner én outputrad per inputrad. Appen velger handlingen. En episode bør bruke samme checkpointversjon hele veien; en ny modell skal ikke byttes inn midt i episoden uten eksplisitt valg.

## Trening for dagens nettverk

Dagens modell bruker evolusjon med utvalg og mutasjon, ikke backpropagation. En løs belønningsverdi er derfor ikke nok til å beskrive hele treningsprotokollen. Bygg en konkret ask/tell-protokoll hvor Studio holder kandidatene og MacBook evaluerer dem.

### Opprett en økt

`POST /v1/evolution/sessions`

```json
{
  "network_id": "maze-history-api-v1",
  "base_checkpoint_id": "en-bestemt-versjon",
  "population_size": 36,
  "elite_count": 6,
  "mutation_sigma": 0.12,
  "seed": 42,
  "request_id": "session-001"
}
```

Parameterverdiene er eksempler fra nåværende oppsett. Kontroller dagens kode og gjør dem konfigurerbare. Returner `session_id`, versjon og innstillinger. En aktiv økt skal ha eksklusiv skriverett til sin modellgren, eller bruke tydelig versjonskontroll.

### Lag kandidater

`POST /v1/evolution/sessions/{session_id}/ask`

Returner `generation_id`, kandidat-ID-er og den gjeldende vinnerens ID. Kandidatvektene blir på Studio. Gjentatt forespørsel med samme request-ID skal returnere samme kandidater.

MacBook velger et felles nytt sett labyrinter for generasjonen. Både den gamle vinneren og alle kandidatene må evalueres på nøyaktig samme sett, slik dagens trening gjør. Resultater fra forskjellige labyrintsett må ikke konkurrere direkte.

### Beregn handlinger for kandidatene

`POST /v1/evolution/sessions/{session_id}/predict`

```json
{
  "generation_id": "generation-001",
  "items": [
    {"candidate_id": "candidate-001", "sample_id": "maze-001", "input": [0.2, 0.4]},
    {"candidate_id": "candidate-002", "sample_id": "maze-001", "input": [0.7, 0.1]}
  ]
}
```

Også her er input forkortet for lesbarhet. Returner output sammen med de samme kandidat- og sample-ID-ene. Gruppeberegn på GPU; ikke kall Python-nettverket separat for hvert individ. Avsluttede lokale episoder kan utelates fra neste batch. Ikke krev like lang episode for alle kandidater.

MacBook bruker output, flytter bottene, beregner nye observasjoner og sender neste batch. Hele sekvensen for hver bot er avhengig av forrige steg, men mange boter kjøres samtidig.

### Send resultatene og oppdater vektene

`POST /v1/evolution/sessions/{session_id}/tell`

Send `generation_id`, `evaluation_set_id`, en endelig fitness-score per kandidat og vinneren, samt unik `request_id`. Fitness er i dag gjennomsnittlig totalbelønning over samme labyrintsett. Studio validerer at alle forventede resultater finnes, velger beste modell, utfører utvalg og mutasjon og lagrer et checkpoint.

Returner ny checkpoint-ID, valgt kandidat, score, generasjon og treningsmålinger. En retry må ikke mutere eller øke generasjonen to ganger. Avvis utdaterte generation-ID-er og delvise resultater. Kandidat-ID-er gjelder bare innen sin økt og generasjon.

Resultater og checkpoint kan hentes tilbake av appen. Det betyr ikke at alle vektene må overføres etter hvert steg. Tilby en separat nedlasting/eksport av vekter.

## GPU som eksplisitt krav

Bruk MLX på Studio med eksplisitt GPU-enhet for inferens. Feil tydelig ved utilgjengelig Metal; ikke bytt lydløst til CPU. Legg til et statusendepunkt som viser faktisk backend og at en GPU-probeberegning har lykkes.

Eksisterende nettverksberegning bruker allerede MLX, mens `NeuralNetwork.train` muterer Python-lister på CPU. Skill disse faktaene i status og dokumentasjon. I den generelle evolusjonsadapteren bør kandidatvekter og mutasjon bygges som MLX-arrayer på GPU, med utvalg fra de returnerte fitness-verdiene. Kontrollflyt, HTTP og filskriving kan fortsatt kjøre på CPU. Bevar vektenes layout og evalueringsreglene ved konvertering; ikke lov bitidentiske tilfeldige mutasjoner mellom Python og MLX.

Ikke forstørr nettverket eller endre belønning som del av API-arbeidet. Mål inferenstid, endepunkttid og batchstørrelse hver for seg. GPU-prosent eller antall kjerner er ikke en tilstrekkelig ytelsestest.

## Klient og bruk fra MacBook

Utvid Python-klienten med register/import, vanlig batch-predict, opprett økt, ask, kandidat-predict, tell, status og checkpointnedlasting.

Lever et lite generelt eksempel som sender gyldige inputdata og får output. Lever deretter en labyrintadapter på MacBook som:

1. Laster samme regler og observasjonsformat som checkpointet.
2. Oppretter labyrinter og lokale episoder for kandidater og gjeldende vinner.
3. Sender alle aktive observasjoner samlet til Studio.
4. Behandler handlinger, sensorer, historikk og belønning lokalt.
5. Sender samlet fitness når evalueringen er ferdig.
6. Viser lokale opptak, for eksempel ett forsøk per 100. generasjon.

Kryssdetektoren og deterministisk historikk kan beholdes lokalt som i dagens spillkode. Skill dette fra det trenbare beslutningsnettet som ligger på Studio. Fryst detektor kan senere få egen nettverks-ID dersom den også skal flyttes.

Appen skal ha valgbare backends, eksempelvis lokal og remote-ai. Behold de eksisterende trenings- og replay-mulighetene. Labyrintprogresjon og utvidelse av nettverk må håndteres eksplisitt; første versjon kan låse dagens labyrintstørrelse for en avgrenset test fremfor å endre inputbredde i en aktiv økt. Oppgi denne begrensningen.

## Tilkobling og drift

Tjenesten kjører på Studio `127.0.0.1:8780`. MacBook har en automatisk SSH-tunnel som eksponerer samme lokale port. Studio er sist kjent som `192.168.86.33`, bruker `torsteinlunde`. MacBook-nøkkelen er begrenset til tunnelen og gir ikke generell fjernkommando-tilgang.

Behold lokal binding og denne tunnelen. Ingen offentlig publisering er nødvendig. Tjenesten må kjøre vedvarende på Studio, og status må gjøre det tydelig om selve API-et eller treningsarbeidet har stoppet. Ikke endre MacBookens SSH-oppsett som del av dette oppdraget.

Lagre modellversjoner og øktstatus på Studio. Ved klientbrudd behold siste fullførte generasjon og definer om ufullstendige evalueringer kan fortsettes eller må kjøres på nytt. Persistens må ikke bare være en statusrad som sier running når prosessen er borte.

## Akseptansetester og levering

- En generell predict-forespørsel kjører uten import av labyrintmotoren i den generelle adapteren.
- Output fra importerte vekter samsvarer med lokal referanse innen en dokumentert flyttallstoleranse.
- Batchede kandidatberegninger samsvarer med individuell referanseberegning.
- GPU er eksplisitt valgt og manglende GPU gir feil.
- En liten lokal labyrinttest på MacBook kan gjennomføre ask, predict og tell med Studio. Ingen labyrintsimulering foregår på Studio i denne testen.
- En train-/tell-operasjon oppdaterer modellversjonen korrekt og lager et lastbart checkpoint.
- Retry gir ikke doble generasjoner, og ugyldige kandidat-ID-er eller dimensjoner avvises.
- Den eksisterende varianten med hele treningsjobber på Studio fungerer fortsatt.
- API og klient er dokumentert med faktiske, kjørbare eksempler og tydelig liste over støttede metoder.

Start med inferens og én liten evolusjonsgenerasjon. Ikke start en lang treningsjobb som del av første integrasjonstest. Lever hvilke filer og kommandoer som skal brukes på MacBook, slik at ChatGPT der kan koble den eksisterende appen til det nye API-et.
