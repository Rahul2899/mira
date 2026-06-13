# Architecture

This document describes how the Autonomous Siting Agent works internally: the data,
the scoring engine, the agent layer, the constraints, and the optional satellite
verification.

## Overview

The system answers a single question: *given a data-center brief in natural language,
which European region is the best place to build, and why?*

It separates two concerns deliberately:

- **Language** is handled by a Large Language Model (Claude, via AWS Bedrock). The LLM
  reads the user's brief and produces structured priority weights, then narrates the
  final result.
- **Numbers** are handled by a deterministic engine (TOPSIS). It performs every
  calculation and produces the ranking. Given the same inputs it always returns the same
  output.

The LLM never computes or invents a number. This keeps the recommendation transparent and
reproducible — the scoring can be inspected and audited independently of the language model.

```
brief ──▶ LLM: extract weights ──▶ TOPSIS engine ──▶ ranking ──▶ LLM: narrate ──▶ result
                                         │
                              (hard filters, supply plan,
                               optional satellite check)
```

## Data model

Each of 46 European regions is scored on four criteria:

| Field | Direction | Source |
|-------|-----------|--------|
| `cost_lcoe` (€/kWh) | minimize | Ember European electricity prices (2025) |
| `green_share_pct` (%) | maximize | Ember generation mix (2025) |
| `grid_capacity_mw` | maximize | PyPSA-Eur substations, aggregated per region |
| `connectivity_score` (0–100) | maximize | Proximity to 11 internet-exchange hubs |

Regions are built by `data_pipeline.py`, which assigns each of ~6,863 PyPSA substations to
its nearest same-country region centroid, sums grid capacity by voltage class, joins the
Ember country-level figures, and applies documented regional adjustments (e.g. higher wind
share at northern latitudes). The output is `data/processed_region_data.csv`.

Additional shown-but-not-ranked factors (wind, solar, hydro, nuclear share, CO₂ intensity,
a governance index) are also extracted for context.

## The scoring engine (TOPSIS)

`topsis.py` implements the Technique for Order Preference by Similarity to Ideal Solution:

1. **Normalize** each criterion column (vector normalization) so different units compare.
2. **Weight** each column by the user's priority, normalized to sum to 1.
3. **Ideal points** — compute the best and worst achievable value per criterion.
4. **Distances** — Euclidean distance of each region to the ideal-best and ideal-worst.
5. **Score** = distance-to-worst / (distance-to-best + distance-to-worst), in [0, 1].

The result is returned as a ranked list (one region per country), each entry carrying the
raw values, the per-criterion 0–1 profile (for the comparison chart), and a supply plan.

## Hard constraints

Two filters remove regions *before* ranking:

- **Protected areas** — regions whose coordinates fall inside a defined Natura 2000 box are
  excluded.
- **Grid headroom vs. facility size** — if the facility's grid draw exceeds a region's
  spare headroom, the region is removed. Grid draw is `size_mw × PUE (1.2)`. Spare headroom
  is taken as 5% of total installed capacity (grids operate near capacity; available
  headroom for new large loads is small). If no region qualifies, the API returns an error
  rather than an unviable recommendation.

Effect: a 40 MW site fits almost anywhere; a 2 GW campus eliminates ~25 regions; a 5 GW
campus eliminates 43 of 46.

## Power-supply plan

For the recommended region, `supply_plan()` derives a recommendation from the clean-energy
share:

- ≥ 85% clean → grid is sufficient for a 24/7 carbon-free target.
- 55–85% → size a renewable PPA to close the gap.
- below that → PPA plus on-site generation/storage.

It also reports the grid draw (MW) and annual consumption (GWh/yr), using IEA reference
values (PUE 1.2, load factor 0.75).

## The agent layer

`agent.py` calls AWS Bedrock with a tool definition for `optimize_site`. The system prompt
instructs the model to extract four weights and an optional size from the brief. The tool is
forced on the first turn, so every brief — however vague — produces a ranking. The model
then narrates the result as short bullet points referencing only the values returned by the
engine.

If Bedrock is unavailable, `run_local()` provides a keyword-based weight extractor as a
fallback; the deterministic ranking is identical.

## Satellite verification (optional)

`satellite.py` is an optional layer using Google Earth Engine and Google DeepMind's
AlphaEarth annual embeddings (a 64-dimensional vector per 10 m of Earth). For the recommended
region it computes the cosine similarity of the region's embedding to a reference hub
(Frankfurt) — a measure of how closely the region resembles established infrastructure from
orbit. It cross-checks the grid/connectivity proxies; it does not affect the ranking. If
Earth Engine is unavailable, the layer is skipped and the UI badge is hidden.

## API

- `POST /optimize_site` — deterministic. Body: four weights in [0,1] plus optional
  `size_mw`. Returns the ranking, heat-map scores, filtered regions, and supply plan.
- `POST /ask_agent` — the LLM path. Body: `{ "prompt": "..." }`. Returns `{ memo,
  raw_result, source }` where `source` is `live` (Bedrock) or `offline` (fallback).

## Frontend

`static/index.html` is a single self-contained file. It renders a 3D globe (globe.gl) with a
country-level suitability heat map, internet-exchange markers, and the top-3 regions, plus a
dossier panel (score, comparison chart, supply plan, satellite badge, adjustable
weight/size sliders). All vendor assets are committed under `static/vendor/` so the frontend
runs without external network access.

## Limitations

- Grid headroom and connectivity are proxies, not live grid-operator data.
- The region set is 46 hand-curated regions, not full NUTS coverage.
- Regional cost/clean adjustments are documented assumptions.
- The satellite score is similarity to a reference hub, not infrastructure detection.

These are addressable in a production version by substituting live data feeds and extending
region coverage; the engine and architecture are unchanged.
