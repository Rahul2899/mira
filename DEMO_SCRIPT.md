# ASA — Demo Script

## Opening (30s) — the problem
"Siting a data center is a 6-month-to-2-year analysis. The binding constraint is increasingly electricity: is there grid capacity, what does power cost, how clean is it, can you connect. Four forces pulling in different directions. We compressed that reasoning into seconds."

## Demo 1 (90s) — recommend + explain the trade-off
1. Type: **"80MW data center, cheapest power, but the grid must handle it, carbon secondary."**
2. While it thinks, narrate: "The agent just extracted four priority weights and is running TOPSIS — the same multi-criteria method used in real procurement — over 46 European regions."
3. Result appears: point at the **score**, then the **TOP-3 COMPARED bars** ("this is the trade-off, visually"), then **HOW TO POWER IT**.

## Demo 2 (45s) — SIZE is the binding constraint (rehearsed, verified)
Keep the same priorities, change only the size via the slider. Verified results:
- **40 MW** (48 MW draw) -> fits everywhere, 0 regions ruled out
- **800 MW** (960 MW draw) -> 4 regions too small
- **2000 MW** (2400 MW draw) -> **25 regions eliminated** on grid capacity alone
- **5000 MW** (6000 MW draw) -> **43 of 46 eliminated**, winner flips to Oslo (only the largest grids survive)

Say: "A small edge site fits almost anywhere. A gigawatt campus eliminates most of Europe on grid headroom alone — that's the constraint the brief calls out, and you can watch it reshape the answer in real time."

## Demo 3 (30s) — flip priorities, agent reasons differently
Fastest path: use the three preset chips, which give three DIFFERENT countries:
- **"Greenest & cheapest, 100MW"** -> Île-de-France (France leads on clean + cheap)
- **"2GW campus, biggest grid"** -> Madrid (Spain has the largest grid)
- **"Next to internet exchange, 80MW"** -> London (LINX connectivity)
Say: "Same data, same math — different priorities, different answer, and it explains why."
INSURANCE if a judge asks "does it always say France?": push the COST slider to max live -> it flips to Helsinki (€0.043, genuinely cheapest in full-year 2025 data). France winning balanced briefs is the honest answer — French nuclear is cheapest AND cleanest right now.

## Closing (40s) — why this wins
"Invertix said the industry doesn't need more dashboards — it needs systems that decide. This hands you a decision-ready recommendation, and because the ranking is deterministic TOPSIS — not an LLM guessing numbers — every recommendation is defensible in an investment committee."

## Q&A ready
- "Is the data real?" -> Ember prices + clean share (country level, regionally adjusted); PyPSA-Eur grid; OSM/ITU data-center hubs for connectivity; IEA PUE 1.2 / load factor 0.75. All cited in the card footer.
- "How do you know grid headroom?" -> substation density × voltage class today; [if EE authed] satellite-verified via AlphaEarth embeddings — show the SATELLITE-VERIFIED line.
- "Does the LLM make up numbers?" -> No. It extracts weights and narrates; all numbers come from the deterministic engine. Expand AGENT MEMO to show it references only real figures.
- "How does it scale?" -> The engine is region-count agnostic; extend to all NUTS-2 + live feeds. With AlphaEarth, any 10m patch on Earth.

## Roadmap line (AlphaEarth)
"Today grid headroom is a substation-density proxy. We've wired in Google DeepMind's AlphaEarth satellite embeddings to measure real infrastructure density from orbit — connecting the siting challenge to the open satellite track. [If authed: it's live, here.] [If not: here's where it plugs in.]"
