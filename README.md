# Autonomous Siting Agent (ASA)

**Where to build the next data center — and how to power it.**

An AI agent for the Invertix "Data-Center Siting & Power" challenge. Describe a data
center in plain English ("80MW, cheapest power, but the grid must handle it") and the
agent returns a ranked, explained European siting recommendation in seconds — with a
power-supply plan and a satellite cross-check.

The key idea: **the LLM never touches the numbers.** It only turns your sentence into
priority weights and narrates the result. Every calculation is done by a deterministic,
auditable **TOPSIS** engine — so the recommendation can be defended in front of any
investment committee.

---

## What it does

- **Recommends locations** for a given data-center size, ranking 46 European regions on
  four criteria: **cost, clean energy, grid headroom, connectivity**.
- **Explains the trade-off** with a quantified "why" and a side-by-side comparison.
- **Treats size as a real constraint** — a facility whose grid draw exceeds a region's
  spare headroom is filtered out (a 2 GW campus eliminates ~25 regions; 5 GW eliminates 43).
- **Plans how to power it** — grid / PPA / on-site, based on the local clean-energy share.
- **Verifies from orbit** — cross-checks the winner against Google DeepMind's AlphaEarth
  satellite embeddings (optional layer).

---

## Quick start

```bash
# 1. install
pip install -r requirements.txt

# 2. run the server
uvicorn main:app --reload --port 8000

# 3. open the UI
open http://localhost:8000
```

The processed region dataset is committed at `data/processed_region_data.csv`, so the app
runs out of the box. The slider/`/optimize_site` path works with no external services.

### Live agent (optional)
The conversational `/ask_agent` path uses **AWS Bedrock** (Claude). Configure AWS
credentials in your environment; the model/region are set in `agent.py`
(`eu.anthropic.claude-sonnet-4-6`, `eu-central-1`). If Bedrock is unavailable, the agent
falls back to a keyword-based weight extractor — the deterministic ranking is identical.

### Satellite layer (optional)
The "satellite-verified" badge uses Google Earth Engine + AlphaEarth. To enable:
`pip install earthengine-api`, register an Earth Engine project, run
`earthengine authenticate`, and set `EE_PROJECT` to your project ID. If unavailable, the
badge simply hides — the core app is unaffected.

---

## Project layout

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app — `POST /optimize_site` (deterministic) and `POST /ask_agent` (LLM). |
| `topsis.py` | The deterministic TOPSIS ranking engine. |
| `agent.py` | AWS Bedrock agent — extracts weights, narrates the memo. |
| `satellite.py` | Optional AlphaEarth (Google Earth Engine) verification. |
| `data_pipeline.py` | Builds `data/processed_region_data.csv` from the raw sources. |
| `static/index.html` | Single-file frontend — 3D globe (globe.gl), heat map, dossier. |
| `data/` | Processed region dataset (committed). |

## Rebuilding the dataset

The processed file is committed, so this is only needed if the raw inputs change. Place
the raw files under `raw_data/` (`raw_data/pypsa/buses.csv`, `raw_data/ember_generation.csv`,
`raw_data/ember_prices.csv`) and run:

```bash
python data_pipeline.py
```

## Data sources

- **Ember** — European electricity prices & generation mix (2025).
- **PyPSA-Eur** — European transmission grid (substations).
- **OpenStreetMap / ITU** — internet-exchange / data-center hubs (connectivity proxy).
- **IEA Energy & AI** — PUE (1.2) and load-factor (0.75) reference values.
- **Google DeepMind AlphaEarth** — satellite embeddings (verification layer).

## Tech

Python · FastAPI · pandas/numpy · AWS Bedrock (Claude) · Google Earth Engine · globe.gl

---

*Built for the Invertix × Vireo × TUM.ai energy/AI hackathon.*
