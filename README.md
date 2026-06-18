# mira

**An AI agent that recommends where to build a data center in Europe — and how to power it.**

### ▶ [**Live demo — mira-f3ml.onrender.com**](https://mira-f3ml.onrender.com/)

> Hosted on a free tier — the first request may take ~30s to wake from idle.

---

Describe a data center in plain language — *"80 MW, lowest cost, but the grid must handle it"* — and mira returns a ranked, explained siting recommendation across 46 European regions, scored on cost, clean-energy share, grid headroom, and connectivity, with a power-supply plan for each pick.

An AI agent only **reads your brief and narrates the answer**. Every number comes from a deterministic scoring engine (TOPSIS), so the results are transparent and reproducible.

> Built as a weekend hackathon prototype, not a production system.

---

## What it does

- **Ranks 46 European regions** on four weighted criteria you control.
- **Reads plain-English briefs** — priorities and facility size are extracted from free text.
- **Treats size as a real constraint** — a region is ruled out if its spare grid headroom can't supply the facility's power draw.
- **Plans the power supply** — grid / PPA / on-site guidance from the local energy mix.
- **Interactive Europe map** with a suitability heat map and the top-3 candidates.

---

## Quick start

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open <http://localhost:8000>. The processed dataset is bundled, so the slider-driven ranking works fully offline with no external services. The natural-language endpoint additionally needs an AWS Bedrock connection (see below); without it, mira falls back to a keyword parser and the ranking is identical.

---

## API

| Endpoint | Body | Notes |
|----------|------|-------|
| `POST /optimize_site` | four weights in `[0,1]`, optional `size_mw` | Deterministic, no AI. |
| `POST /ask_agent` | `{ "prompt": "..." }` | Natural-language path. |

```bash
curl -X POST http://localhost:8000/optimize_site \
  -H "Content-Type: application/json" \
  -d '{"weight_cost":0.5,"weight_green":0.2,"weight_grid":0.2,"weight_connectivity":0.1,"size_mw":200}'
```

---

## AI agent (optional)

`/ask_agent` calls **AWS Bedrock** (Anthropic Claude, `eu.anthropic.claude-sonnet-4-6`, region `eu-central-1`). It needs Bedrock model access and AWS credentials via the standard boto3 chain:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
# optional: export BEDROCK_MODEL_ID=...
```

Never commit credentials — pass them as environment variables or an IAM role. The region is pinned in `agent.py` (the `eu.` inference profile is only valid in `eu-central-1`).

---

## Layout

```
main.py            FastAPI app: /optimize_site (deterministic) + /ask_agent (AI)
topsis.py          TOPSIS ranking engine
agent.py           Bedrock agent — weight extraction and narration
satellite.py       Optional satellite cross-check
static/index.html  Single-file frontend (Europe map + result dossier)
data/              Processed region dataset (bundled)
docs/              Architecture notes
```

## Data sources

[Ember](https://ember-energy.org) (prices & generation mix) · [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) (grid model) · OpenStreetMap / ITU (network hubs) · [IEA Energy & AI](https://www.iea.org) (PUE & load factors).

## License

MIT
