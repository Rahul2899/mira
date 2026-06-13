# Autonomous Siting Agent (ASA) — The Complete Deep Explainer

*Read this top to bottom (~30 min) and you will understand every part of the project: what it is, why it exists, how each number is calculated, every design choice, and how to defend it. Written for someone who did not build it and wants to fully own the story.*

---

# PART 1 — THE BIG PICTURE (start here)

## 1.1 What problem are we solving?
AI is exploding, and AI needs data centers. The hidden bottleneck for a new data center is no longer land or money — it's **electricity**. Specifically four questions:
1. **Is there grid capacity?** Can the local power grid physically accept a new 50–2000 MW load, or is it already full (congested)?
2. **What does power cost there?** Electricity is the biggest lifetime cost — a €0.02/kWh difference is €12–16M/year for a 100MW site.
3. **How clean is it?** Google, Microsoft, Amazon all have 24/7 carbon-free commitments. A dirty grid means missing those targets or buying expensive renewables.
4. **Can you connect (fiber)?** Low-latency workloads need to be near internet exchanges.

Today, answering these for one site takes a team of consultants **6 months to 2 years**, and many sites die late because nobody checked grid congestion early. Connection queues in Europe run **3–7 years**.

## 1.2 What did we build?
A **conversational AI agent** that does this reasoning in **seconds**. You describe your data center in plain English ("80MW, cheapest power, but the grid must handle it"), and it:
1. Understands your priorities and turns them into numbers (weights).
2. Scores 46 European regions on the four factors using a transparent math method (TOPSIS).
3. Removes regions that physically can't work (protected land, or grid too small for your size).
4. Hands you a ranked recommendation with the reasoning, a power plan, and a satellite check.

## 1.3 The single most important idea (memorize this)
**The AI never invents numbers.** The Large Language Model (Claude) does only two narrow things it's genuinely good at:
- Turn your sentence into priority weights ("cheapest power" → cost weight 0.7).
- Read the result back to you in plain English.

All the actual math — the part that must be correct and auditable — is done by **deterministic code (TOPSIS)**, not the AI. This means when a judge asks *"is the AI just making up numbers?"*, the answer is **"No. The AI never touches the math. Here is the exact table."** This is our biggest strength and the reason the whole architecture is shaped this way.

---

# PART 2 — THE FOUR FACTORS (what we rank on, and where every number comes from)

We score each region on exactly **four criteria**. Here's each one in plain terms:

### Factor 1 — Cost (`cost_lcoe`, €/kWh) — lower is better
**What it is:** the wholesale price of electricity in that country.
**Where it comes from:** Ember's European electricity price dataset, **2025 (the latest complete year)**. We take the average price for the year and divide by 1000 to get €/kWh.
**Example:** France ≈ €0.067/kWh, London ≈ €0.10/kWh.

### Factor 2 — Clean energy (`green_share_pct`, %) — higher is better
**What it is:** what percentage of the region's electricity comes from clean sources (nuclear + hydro + wind + solar + bioenergy).
**Where it comes from:** Ember's generation-mix dataset, **2025**. We read the "Clean %" figure per country.
**Example:** France 97% (nuclear), Norway ~98% (hydro), Poland ~31% (coal).

### Factor 3 — Grid headroom (`grid_capacity_mw`) — higher is better
**What it is:** how much spare grid capacity exists to connect a new data center. This is the "grid congestion" factor — we measure it as **headroom** (the opposite of congestion). High headroom = low congestion.
**Where it comes from:** PyPSA-Eur, a real model of Europe's power grid. It lists **6,863 actual substations** with their voltage and GPS location. We assign each substation to its nearest region and sum up capacity by voltage class (higher voltage = more capacity). The **usable spare** is taken as **5% of total** — because real grids run near capacity, so only a small fraction is free for new large loads (this is exactly why connection queues exist).
**Example:** Madrid 135,500 MW total → ~6,775 MW spare.

### Factor 4 — Connectivity (`connectivity_score`, 0–100) — higher is better
**What it is:** how close the region is to Europe's major internet exchanges / data-center hubs (where fiber is dense).
**Where it comes from:** proximity to **11 real hubs** (Frankfurt/DE-CIX, London/LINX, Amsterdam/AMS-IX, Paris, Dublin, Madrid, Milan, Warsaw, Stockholm, Copenhagen, Vienna) — the OSM/ITU connectivity signal. Closer = higher score.
**Example:** London 100, a remote region ~30.

### Hard filters (not scored — pass/fail)
Two things eliminate a region *before* ranking:
- **Protected nature areas (Natura 2000):** regions inside a defined protected box (e.g. the Alps near Tyrol) are removed. The agent says "1 site ruled out for Natura 2000."
- **Grid too small for your size:** if your facility's power draw exceeds the region's spare headroom, it's removed. (More in Part 4.)

### Useful assumptions (cited, from IEA)
- **PUE = 1.2** (Power Usage Effectiveness): a 100 MW IT load actually pulls 120 MW from the grid (cooling overhead).
- **Load factor = 0.75:** AI workloads run at ~75% utilization.
- These convert "data center size" into real grid draw and annual energy.

---

# PART 3 — THE MATH: HOW TOPSIS WORKS (in plain words)

TOPSIS = "Technique for Order Preference by Similarity to Ideal Solution." It's a standard method (used in real engineering/procurement) for ranking options across multiple conflicting goals. Here's the whole thing in 5 steps:

1. **Normalize.** Cost is in €/kWh, clean is in %, headroom in MW — different units. We mathematically rescale every column so they're comparable (each column gets unit length).

2. **Apply your weights.** Multiply each factor by how much you care about it. "Cheapest power" → cost gets weight 0.7, the rest small. Weights are scaled to sum to 1.

3. **Find the ideal best and ideal worst.** The "ideal best" is an imaginary perfect region: cheapest cost, highest clean, most headroom, best connectivity. The "ideal worst" is the opposite.

4. **Measure distance to each.** For every real region, compute how far it sits from the ideal best, and from the ideal worst (straight-line / Euclidean distance in the weighted space).

5. **Score.** Score = (distance to worst) ÷ (distance to best + distance to worst). A region close to the ideal best and far from the worst scores near 1. We show it as **N out of 100**.

**Why TOPSIS and not "just add up a score"?** Because it handles *trade-offs* without collapsing everything into one dollar figure (which hides information). It's deterministic (same input → same output every time) and fully auditable. That's exactly what an explainability-focused judge wants.

---

# PART 4 — THE SIZE CONSTRAINT (why "for a given size" is real)

The brief says electricity is the *binding constraint by size*. We made size genuinely change the answer:

1. You say "2000 MW." The agent extracts that.
2. Grid draw = 2000 × PUE 1.2 = **2,400 MW** actual draw.
3. Any region whose spare headroom (5% of its grid) is **less than 2,400 MW** is **filtered out** before ranking.

**Verified behavior** (same priorities, only size changes):
| Size | Grid draw | Regions ruled out |
|------|-----------|-------------------|
| 40 MW | 48 MW | 0 (fits everywhere) |
| 500 MW | 600 MW | 1 |
| 2,000 MW | 2,400 MW | 25 |
| 5,000 MW | 6,000 MW | 43 of 46 |
| 20,000 MW | 24,000 MW | all → clean error message |

This is the strongest live demo moment: a small edge site fits anywhere; a gigawatt campus eliminates most of Europe on grid capacity alone — and you watch it happen.

---

# PART 5 — HOW TO POWER IT (the supply plan)

Once a region is chosen, we give a power-supply recommendation based on its clean %:
- **≥85% clean:** "Grid is already clean enough for a 24/7 carbon-free target — minimal extra procurement."
- **55–85% clean:** "Sign a renewable PPA (power purchase agreement) of ~X MW to close the gap to 90% clean."
- **<55% clean:** "Grid is carbon-heavy — pair with a PPA + on-site solar/storage."

Shown with the grid draw (MW), annual consumption (GWh/year), and clean % — all quantified. This answers the brief's second bullet ("plan a supply mix of grid, PPA, on-site").

---

# PART 6 — THE SATELLITE LAYER (AlphaEarth) — what it is and where it fits

**Important: AlphaEarth does NOT choose the winner. It verifies the winner.**

- **What it is:** Google DeepMind's AlphaEarth Foundations — a model that turns satellite imagery into a 64-number "fingerprint" for every 10m×10m patch of Earth. Free, in Google Earth Engine.
- **What we do with it:** after TOPSIS picks the winning region, we pull its satellite fingerprint and compute how similar it is (cosine similarity) to **Frankfurt** — a known dense data-center hub. That gives a 0–100 "looks like real infrastructure" score, shown as HIGH / MODERATE / LOW.
- **Why:** our grid and connectivity numbers are proxies. AlphaEarth lets us say "we independently checked from orbit that this region really looks like established infrastructure." It's a **credibility cross-check**.
- **Honest limit:** the embedding encodes terrain + land cover, not literally "this is a substation." So it's *similarity to a known hub*, not a precise grid measurement. Present it as a confidence cross-check, not detection.
- **Strategic value:** it closes the "is your data real?" gap AND connects both Invertix tracks (the siting challenge + the open satellite track). If Earth Engine fails, the line just hides — the core demo is unaffected.

---

# PART 7 — THE INTERFACE (what's on screen and why)

**Left side — the globe (the "where"):**
- A 3D Earth, framed on Europe.
- **Country heat map:** each country's landmass is colored **red (poor) → green (good)** by how suitable it is for the current priorities. The legend says "Suitable data center location." This is the at-a-glance "good vs bad territory" view.
- **Top-3 region pins:** the winner (big gold pill) and runners-up (numbered), placed on their real coordinates. Click one to zoom in.

**Right side — the dossier (the "why"):**
- **Recommendation + score** out of 100, with a one-line quantified "why."
- **Top-3 compared:** four bars (cost, grid, clean, connectivity) for all three finalists — the trade-off made visible.
- **Satellite-verified** badge.
- **How to power it:** grid draw, annual GWh, clean %, supply plan.
- **Ruled out before ranking:** how many regions removed and why.
- **Adjust & re-rank:** four sliders + a size box — a judge can change priorities live and watch the answer change instantly (this re-runs the deterministic engine, no AI call).
- **Agent memo:** short bullet points of the full reasoning (collapsed by default).

---

# PART 8 — THE STACK (the technology)

- **Backend (Python):**
  - `topsis.py` — the deterministic ranking engine (pandas/numpy).
  - `agent.py` — the AWS Bedrock agent (Claude Sonnet via the Converse API with forced tool-use).
  - `main.py` — FastAPI web server with two endpoints: `/ask_agent` (the LLM path) and `/optimize_site` (the direct slider path).
  - `satellite.py` — Google Earth Engine + AlphaEarth.
  - `data_pipeline.py` — builds the 46-region dataset from the raw files (run once).
- **Frontend:** a single `static/index.html` — globe.gl (3D globe), Chart.js, all assets self-hosted (no internet dependency at the venue except the one Bedrock call).
- **Data:** `processed_region_data.csv` — 46 regions, all 2025 data.

**We did NOT train a machine-learning model.** We deliberately used **strong, transparent mathematics (TOPSIS)** instead. This is a feature, not a gap: it's auditable and explainable, where an ML black box would not be. The only AI is the off-the-shelf LLM doing language tasks.

---

# PART 9 — THE JOURNEY (every problem we hit and how we solved it — this shows rigor)

**(a) "It always recommended France."** Two causes: (1) early on, the Bedrock connection was misconfigured (wrong model ID + region), so every request silently fell back to one saved France answer — fixed by using a live model pinned to the EU region; (2) the data was being **averaged across all years (1990–2025)**, which buried countries that recently went green and inflated France. We fixed it to use **2025 only**, and added regional differentiation so regions within a country differ. France still leads *balanced* briefs — but that's now the **honest, correct** answer (French nuclear genuinely is cheapest + cleanest). Strong single priorities flip it: cost→Finland, grid→Spain, connectivity→UK.

**(b) Country → region.** A whole country is too coarse to call a "site"; 6,863 raw substations are too granular. We aggregated to **46 NUTS-2-style regions** — the unit a real executive reasons about.

**(c) The globe fought us for many rounds.** Labels collided, a flat map and a dark globe were tried, and we returned to the **light day-earth globe** with a country heat map. (We removed connection arcs at the end because they were misleading — the three sites are alternatives, not a network.)

**(d) Vague prompts crashed the agent.** "Best place for a 5-year vision?" made the LLM chat instead of running the math → crash. Fixed by **forcing the tool call** so every prompt always produces a ranking.

**(e) Data freshness.** We caught that prices were using a partial 2026 (only 6 months, seasonally skewed) and pinned everything to the last complete year, **2025**.

---

# PART 10 — HONEST LIMITATIONS (know these; judges respect honesty)
- Grid headroom and connectivity are **proxies** (satellite-verified, but not live grid-operator data).
- **46 hand-curated regions**, not all of Europe (every major market is covered).
- Regional clean/cost differences are **documented assumptions**, not measured per-region.
- The satellite score is **similarity to a known hub**, not a literal substation count.
- France leading balanced briefs reflects **real nuclear economics** — defend it, don't apologize.

In a production version: live grid-operator congestion feeds, full NUTS-3 coverage, and AlphaEarth detection extended to every 10m patch. **The architecture doesn't change — only the data volume.**

---

# PART 11 — THE ONE-PARAGRAPH SUMMARY (if you only remember one thing)
We built an autonomous agent that turns a plain-English data-center brief into a ranked, explained European siting recommendation in seconds. It uses an LLM only for language (understanding the brief, narrating the answer) and **deterministic TOPSIS math** for every number — so it's transparent and defensible, not a black box. It models the four real trade-offs (cost, carbon, grid congestion, connectivity), enforces real constraints (protected land, grid capacity vs. facility size), plans the power supply, and cross-checks the winner with Google DeepMind's AlphaEarth satellite data. It's exactly what Invertix said the industry needs: not another dashboard, but a system that decides — and can defend the decision.
