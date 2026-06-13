# mira

**An AI agent that recommends where to build a data center in Europe — and how to power it.**

### ▶ [**Live demo — mira-f3ml.onrender.com**](https://mira-f3ml.onrender.com/)

> The hosted app may take ~30 seconds to wake from idle on the first request.

---

Describe a data center in plain language (*"80 MW, lowest cost, but the grid must handle
it"*) and mira returns a ranked, explained siting recommendation across 46 European regions,
scored on cost, clean-energy share, grid headroom, and connectivity — with a power-supply
plan and an optional satellite cross-check.

The language model — Anthropic Claude, served through **Amazon Bedrock** — is used only to
interpret the request and narrate the answer. Every number is produced by a deterministic
scoring engine (TOPSIS), so results are transparent, reproducible, and auditable.

---

## Features

- **Region ranking** across 46 European regions on four weighted criteria.
- **Natural-language input** — priorities are extracted from a free-text brief.
- **Size as a constraint** — a region is excluded if its spare grid headroom cannot support
  the facility's power draw.
- **Power-supply planning** — grid / PPA / on-site guidance based on the local energy mix.
- **Interactive 3D globe** — country-level suitability heat map and the top-3 candidates.
- **Optional satellite verification** via Google DeepMind's AlphaEarth embeddings.

---

## Quick start

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open <http://localhost:8000>. The processed dataset is included
(`data/processed_region_data.csv`), so the application runs without any external services.
The slider-driven `/optimize_site` path works fully offline.

---

## Configuration

mira runs with no configuration. Two optional capabilities can be enabled.

### Conversational agent — AWS Bedrock (`/ask_agent`)

The natural-language endpoint runs on **Amazon Bedrock**. `agent.py` creates a
`bedrock-runtime` client (via `boto3`) and calls the **Converse API** with tool-use: the
model (Anthropic Claude) extracts the four priority weights and an optional facility size
from the brief, the deterministic engine runs, and the model narrates the result.

| Setting | Value | Override |
|---------|-------|----------|
| Service | Amazon Bedrock Runtime (Converse API, tool-use) | — |
| Model | `eu.anthropic.claude-sonnet-4-6` (an EU inference profile) | `BEDROCK_MODEL_ID` env var |
| Region | `eu-central-1` | set in `agent.py` |

**Requirements:**

1. An AWS account with **Bedrock model access** granted for the Claude model in
   `eu-central-1` (request it once in the Bedrock console → *Model access*).
2. AWS credentials available through the standard boto3 chain — environment variables,
   a shared profile, or an IAM role:

   ```bash
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   # optional: export BEDROCK_MODEL_ID=eu.anthropic.claude-sonnet-4-6
   ```

> The region is pinned to `eu-central-1` because the `eu.` inference profile is only valid
> there. Do not rely on `AWS_REGION` to change it.

If Bedrock is unreachable, `agent.py` falls back to a keyword-based weight extractor
(`run_local`). The deterministic ranking is identical either way; only the natural-language
narration differs. The `/optimize_site` endpoint never uses Bedrock.

### Satellite verification — Google Earth Engine

```bash
pip install earthengine-api
earthengine authenticate
export EE_PROJECT=your-earth-engine-project-id
```

Without it, the satellite badge is simply hidden and the ranking is unaffected.

---

## Project structure

```
main.py              FastAPI app: /optimize_site (deterministic) and /ask_agent (LLM)
topsis.py            TOPSIS ranking engine
agent.py             AWS Bedrock agent — weight extraction and narration
satellite.py         Optional AlphaEarth verification
data_pipeline.py     Builds data/processed_region_data.csv from raw sources
static/index.html    Single-file frontend (globe.gl, heat map, dossier)
data/                Processed region dataset
docs/ARCHITECTURE.md Detailed design notes
```

---

## API

| Endpoint | Description |
|----------|-------------|
| `POST /optimize_site` | Deterministic ranking. Body: four weights in `[0,1]` and optional `size_mw`. |
| `POST /ask_agent` | Natural-language path. Body: `{ "prompt": "..." }`. |

Example:

```bash
curl -X POST http://localhost:8000/optimize_site \
  -H "Content-Type: application/json" \
  -d '{"weight_cost":0.5,"weight_green":0.2,"weight_grid":0.2,"weight_connectivity":0.1,"size_mw":200}'
```

---

## Rebuilding the dataset

The processed dataset is committed, so this is only needed if the raw inputs change. Place
the raw files under `raw_data/` and run:

```
raw_data/pypsa/buses.csv
raw_data/ember_generation.csv
raw_data/ember_prices.csv
```

```bash
python data_pipeline.py
```

---

## Data sources

- [Ember](https://ember-energy.org) — European electricity prices and generation mix.
- [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) — European transmission grid model.
- OpenStreetMap / ITU — internet-exchange and data-center hub locations.
- [IEA Energy & AI](https://www.iea.org) — PUE and load-factor reference values.
- [Google DeepMind AlphaEarth](https://deepmind.google) — satellite embeddings.

---

## Tech stack

Python · FastAPI · pandas / NumPy · AWS Bedrock · Google Earth Engine · globe.gl

## License

MIT
