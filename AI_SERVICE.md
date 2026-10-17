# Lokal AI-tjeneste

Start kun på Studio (tjenesten binder seg til `127.0.0.1`):

```sh
.venv-studio/bin/python -m ai_service.server --port 8780
```

Første import kopierer og validerer den faktiske `deterministic_history_v1.json` og den fryste kryssdetektoren til `.ai-service/`. Originalfilene endres aldri.

```sh
curl -X POST http://127.0.0.1:8780/networks -H 'Content-Type: application/json' -d '{"network_id":"maze-history-v1"}'
curl -X POST http://127.0.0.1:8780/training-runs -H 'Content-Type: application/json' -d '{"network_id":"maze-history-v1","additional_generations":2,"request_id":"example-001"}'
```

Bruk `GET /training-runs/<run_id>` for status, `POST /training-runs/<run_id>/stop` for kontrollert stopp ved neste generasjonsgrense, og `GET /training-runs/<run_id>/recording` for siste opptak. Samme `request_id` returnerer den opprinnelige kjøringen. Én GPU-jobb kan kjøre om gangen.

Fra en annen Mac lager du en tunnel (erstatt bruker og Studio-navn):

```sh
ssh -N -L 8780:127.0.0.1:8780 bruker@studio-navn.local
```

Deretter brukes `ai_service.client.Client()` mot standardadressen. En API-omstart markerer en aktiv kjøring som `failed`; klienten kan da starte en ny kjøring fra det lagrede run-checkpointet etter at dette er gjort til aktiv modell manuelt. Runtime-data i `.ai-service/` skal ikke versjoneres.
