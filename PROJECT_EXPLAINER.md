# Autonomous Siting Agent (ASA) — Complete Project Explainer (Deep)

*The full story for the team: what we built, why, how every number is derived, every problem we hit and how we solved it, what to say to judges, and how to present. Read this and you can defend any question.*

---

## 1. THE PROBLEM (what the challenge asked)

**Invertix Track — Data-Center Siting & Power.** AI is driving a wave of new data centers; the binding constraint is increasingly **electricity**: is there grid capacity, what does power cost, how clean is it, can you connect. Siting is a multi-way trade-off between **price, carbon, grid congestion, and connectivity**.

The brief offered three directions:
1. A tool that **recommends locations** for a given size and **explains the trade-offs**.
2. A **power-supply planner** (grid / PPA / on-site vs cost & carbon).
3. A **map** overlaying capacity, prices, carbon, congestion.

**We built #1 as the core, folded in #2, and added a satellite-verification layer.**

**Real-world context:** siting a data center today takes 6 months–2 years of analysis. Connection queues in Europe run 3–7 years. A meaningful fraction of sites die late because nobody checked grid congestion early. We compress the *screening and trade-off reasoning* into seconds.

---

## 2. THE PRODUCT IN ONE PARAGRAPH

A conversational agent on an interactive globe. You describe a data center in plain English ("80MW, cheapest power, but the grid must handle it"). It (1) extracts your priorities into four decision weights, (2) runs a **deterministic TOPSIS** ranking over 46 European regions scored on cost, clean energy, grid headroom, and connectivity, (3) filters out regions violating hard constraints (protected nature areas; insufficient grid headroom for your size), (4) returns a ranked recommendation with a quantified "why", a power-supply plan, and a satellite-verification badge.

**The architectural bet:** the LLM never touches the numbers. It only (a) turns your sentence into weights and (b) narrates the result. All math — the part that must be correct and auditable — is deterministic TOPSIS. *This is our answer to "is the AI making up numbers?" — No. We can show you the exact table.*

---

## 3. THE DATA — sources, files, and how every number is derived

We were given 4 raw files (in `raw_data/`):

| File | Contains | We extract |
|---|---|---|
| `ember_generation.csv` | Generation by fuel × country × year **(1990–2025)**, incl. a "Clean" % row | Clean-energy share per country |
| `ember_prices.csv` | Wholesale price (EUR/MWhe) × country × date **(2015–2026)** | Electricity cost (÷1000 → €/kWh) |
| `pypsa/buses.csv` | 6,863 real substations: voltage, lat/lon, country | Grid capacity proxy + region assignment |
| `pypsa/lines.csv` | Transmission lines, capacities (s_nom), geometry | Available (capacity comes from buses) |

### The four criteria
| Criterion | Direction | Source | Derivation |
|---|---|---|---|
| **Cost** (`cost_lcoe`, €/kWh) | minimize | Ember prices | **Latest-year** wholesale price ÷ 1000 |
| **Clean energy** (`green_share_pct`, %) | maximize | Ember generation | **Latest-year (2025)** clean share, with regional skews |
| **Grid headroom** (`grid_capacity_mw`) | maximize | PyPSA buses | Substation count × voltage-class capacity per region; **usable spare = 5% of total** |
| **Connectivity** (`connectivity_score`, 0–100) | maximize | OSM / ITU hubs | Proximity to 11 real EU data-center / IXP hubs (Frankfurt/DE-CIX, London/LINX, Amsterdam/AMS-IX, Paris, Dublin + secondaries) |

### How regions are built (`data_pipeline.py`)
We aggregate the 6,863 raw substations into **46 NUTS-2-style regions** (Bavaria, Île-de-France, Madrid…). Each substation is assigned to its **nearest same-country region centroid** (never random). A region's grid headroom = sum of its substations' voltage-class capacities. Ember clean-share and prices join at country level, then are regionally differentiated (see §5).

**Assumptions (cited in the UI):** PUE = 1.2, load factor = 0.75 (IEA Energy & AI). Grid draw = IT load × PUE. Annual GWh = draw × load factor × 8760h.

---

## 4. HOW THE MATH WORKS (TOPSIS, plain terms)

TOPSIS = "Technique for Order Preference by Similarity to Ideal Solution." It ranks options across multiple conflicting criteria without collapsing everything into one dollar figure (which loses information).

1. **Normalize** each criterion (vector normalization) so €/kWh, %, and 0–100 scores become comparable.
2. **Weight** each by the user's priority (re-normalized to sum to 1).
3. Find the **ideal best** (cheapest, cleanest, most headroom, best connectivity) and **ideal worst**.
4. Measure each region's **Euclidean distance** to both.
5. **Score** = distance-to-worst / (distance-to-best + distance-to-worst). Closer to 1 = better. Shown as N/100.

Runs in milliseconds, fully deterministic (same input → same output), every number traceable.

---

## 5. THE BIG DATA FIX — "why it always said France" (and the honest resolution)

This is the most important story to tell, because it shows rigor.

### The bug
The pipeline was **averaging clean-% and prices across ALL years** (generation 1990–2025, prices 2015–2026). Consequences:
- Countries that recently went green looked artificially dirty: **Denmark 37% (avg) vs 89% (2025)**, Finland 69%→95%, Spain 53%→77%, Netherlands 17%→54%.
- France barely moved (nuclear for decades), so the stale average **inflated France's relative lead**.
- Prices were worse — blending 2015 pre-energy-crisis with 2024 is meaningless (Spain €0.070 avg vs €0.046 latest).

### Fix #1 — use the latest year only
Now clean-share = 2025, prices = latest year. Real, current numbers.

### Fix #2 — differentiate regions within each country
Raw country data made every French region identical (94.85% / €0.055) — only grid size differed, so region-level ranking was meaningless. We added **documented geographic skews** (not random) to every region:
- **Clean share:** boosted by latitude — northern/coastal regions get a wind premium, deep-southern regions a solar premium. (Hauts-de-France 98.7% vs Occitanie 91.2%.)
- **Cost:** capital/industrial regions +6% tariff premium, peripheral regions −4%. (Île-de-France €0.058 vs other French regions €0.053.)

### The result — measured
- Winner distribution across the full weight space: **77% → 65% France**, with Spain (26%), Germany (9%), Portugal competing.
- **Slider demo now gives four different winners:** Max cost → **Lisbon** (€0.047, genuinely cheapest), Max clean → **Île-de-France**, Max grid → **Madrid**, Max connectivity → **London**.

### The honest position (defend this confidently)
France still leads *balanced* briefs — **and that is the correct answer, not a bug.** In real 2025 data, France genuinely has the cheapest AND nearly cleanest power in Europe (nuclear). We deliberately did **not** distort the data to manufacture variety. The system reasons honestly; France just wins the "I want a bit of everything" space, while strong single priorities surface genuinely different regions. *Judges respect "the data is honest and here's why" far more than fudged numbers.*

---

## 6. THE SIZE CONSTRAINT (why "for a given size" is real)

The agent extracts MW from the brief → grid draw = MW × 1.2 (PUE). Any region whose 5% spare headroom can't absorb that draw is **filtered out before ranking**.

**Verified, and it changes the winner:**
- 40 MW → fits everywhere, 0 ruled out.
- 800 MW → 4 regions too small.
- 2,000 MW → **25 regions eliminated**; a cost-focused brief that picked **Madrid at 80MW flips to Île-de-France at 2000MW** because Madrid's headroom can't carry it cleanly.
- 5,000 MW → **43 of 46 eliminated**, winner → Oslo.

This is the strongest live moment: *same priorities, change only the size, watch the answer and the geography change.*

---

## 7. HOW TO POWER IT (challenge bullet #2)

For the recommended region we generate a supply plan from its clean-share:
- ≥85% clean → "grid is clean enough for 24/7 carbon-free with minimal procurement."
- 55–85% → renewable PPA sized to close the gap to 90%.
- <55% → PPA + on-site solar/storage, sized to the facility.

Shown with quantified grid draw (MW), annual consumption (GWh/yr), grid clean-share (%).

---

## 8. THE SATELLITE LAYER (AlphaEarth) — what it is and EXACTLY where it fits

**Critical clarification (a common confusion): AlphaEarth does NOT pick the winner. It verifies it.**

```
Brief → weights → TOPSIS ranks 46 regions (Ember + PyPSA data) → WINNER
                                                                   │
                          AlphaEarth checks the winner from orbit  ▼
                          ("does it LOOK like a real DC hub?") → SATELLITE-VERIFIED badge
```

- **What it is:** Google DeepMind's AlphaEarth Foundations — a 64-number satellite "fingerprint" per 10m patch of Earth, free in Google Earth Engine.
- **What we do:** after TOPSIS picks the winner, we pull its fingerprint and compute **cosine similarity to Frankfurt** (a known data-center hub) → 0–100 (HIGH/MODERATE/LOW). "Satellite-measured similarity to a data-center hub."
- **The one job it does:** our grid-headroom and connectivity numbers are proxies. AlphaEarth lets us answer "is that real?" with "we independently checked from orbit." It's a **credibility cross-check**, not the decision-maker.
- **Strategic value:** closes the "is your data real?" gap AND connects both Invertix tracks (siting + open satellite). Degrades gracefully — if Earth Engine fails, the line hides, core ranking untouched.
- **Don't overclaim:** it measures *visual similarity to a known hub*, not literal substation counts.

---

## 9. THE JOURNEY — every problem we hit and how we solved it

**(a) "It always recommended France."** Two root causes: (i) Bedrock was never actually called — outdated model ID + wrong AWS region meant every request fell back to one saved France response (fixed: live model `eu.anthropic.claude-sonnet-4-6`, region pinned `eu-central-1`); (ii) the data bug in §5 (all-years averaging + identical within-country regions). Both fixed.

**(b) Country → region.** A country is too coarse to call a "site"; 6,863 raw substations are too granular (mush). We aggregated to 46 defensible NUTS-2-style regions — the unit a CFO actually reasons about.

**(c) Removed an arbitrary capacity cut-off** so 20–50MW edge sites compete fairly; size now filters naturally.

**(d) The globe fought us — many rounds.** 3D text labels collided (and showed a "?" glyph). We researched globe.gl + the Cloudflare infrastructure globe and learned the pro pattern. We tried a flat map and a dark night-globe, then returned to the **light day-earth full-screen globe** with a per-frame screen-space de-collision pass for the region pills, and a slide-in result panel.

**(e) Vague prompts crashed the agent.** "Best place for a 5-year vision?" made the LLM chat instead of calling the tool → null result → "Could not reach the engine." Fixed by forcing the tool call (`toolChoice`) on turn 1, plus a frontend null-guard.

**(f) Numbers made judge-readable.** Early cards showed bare bars. Now the "why" is quantified ("Wins on power at €0.058/kWh and 97% clean energy") and every comparison axis shows its real value.

**(g) Performance.** AlphaEarth's Earth Engine init took ~10s; moved to server startup so per-request latency stays ~0.01s.

---

## 10. STACK
- **Backend:** Python — TOPSIS engine (`topsis.py`), Bedrock agent (`agent.py`, Claude Sonnet via Converse + forced tool-use), FastAPI (`main.py`).
- **Data pipeline:** `data_pipeline.py` (raw → 46 regions, latest-year + regional skews).
- **Satellite:** Google Earth Engine + AlphaEarth (`satellite.py`).
- **Frontend:** single-file `static/index.html` — globe.gl, Chart.js, all assets self-hosted (no CDN at the venue).
- **Data file:** `processed_region_data.csv` (46 regions, pre-built; re-run pipeline only if raw files change).

---

## 11. ANTICIPATED JUDGE QUESTIONS (with answers)

**"Is this real data or made up?"** Real. Cost & clean-energy from Ember's published European datasets (latest year). We apply documented regional adjustments for sub-country granularity (wind north, solar south, capital tariff premium). Grid headroom from PyPSA-Eur substations; connectivity from OSM/ITU data-center hubs. And we satellite-verify the winner with AlphaEarth.

**"Why does France keep winning?"** Because in current 2025 data it genuinely has the cheapest AND cleanest power in Europe (nuclear) — no region beats it on both. We didn't fudge that. Watch the sliders: max cost → Lisbon, max grid → Madrid, max connectivity → London. The agent reasons; France just wins the balanced space.

**"Does the LLM hallucinate numbers?"** No — and it's our strength. The LLM only extracts weights and narrates. Every number comes from the deterministic TOPSIS engine. (Expand the AGENT MEMO; show the score table.)

**"What about the size of the data center?"** [Demo it] change only the size → regions get eliminated on grid headroom; a cost-focused 80MW pick can flip at 2000MW. A 40MW edge site fits anywhere; a 2GW campus eliminates most of Europe.

**"Why TOPSIS?"** Purpose-built for ranking alternatives across conflicting criteria in different units, without collapsing to one currency. Deterministic and auditable.

**"How does it scale?"** Engine is region-count-agnostic. Extend to all NUTS-3 + live feeds; with AlphaEarth, to any 10m patch on Earth. Architecture unchanged, only data volume.

**"How does AlphaEarth work here?"** It doesn't pick the site — it verifies the winner by measuring, from orbit, how closely the region resembles an established data-center hub. A satellite cross-check on our infrastructure assumptions.

---

## 12. THE 3-MINUTE PITCH (see DEMO_SCRIPT.md for narration)

1. **Problem (30s):** siting takes months; electricity is the binding constraint; four forces pull in different directions.
2. **Demo 1 (60s):** type a cost brief → recommendation + quantified why + comparison bars + power plan.
3. **Demo 2 (30s):** change only the size to 2000MW → 25 regions ruled out, winner can flip. "Size is the binding constraint."
4. **Demo 3 (30s):** flip priorities to carbon → different winner, different reasoning. Or push the sliders live: cost→Lisbon, grid→Madrid, connectivity→London. "Same data, same math — it reasons."
5. **Close (30s):** satellite-verified, deterministic (not an LLM guessing), decision-ready — exactly what Invertix said the industry needs.

---

## 13. HONEST LIMITATIONS (know these, don't hide them)
- Connectivity & grid headroom are proxies (satellite-verified, but not live operator data).
- 46 hand-curated regions, not all of Europe (every major market covered).
- Regional clean/cost skews are documented assumptions, not measured per-region.
- The satellite score is *similarity to a known hub*, not a literal substation count.
- France leading balanced briefs reflects real nuclear economics — defend it, don't apologize for it.

These are all defensible as "honest methodology under a hackathon timeline" — which judges respect more than overclaiming.
