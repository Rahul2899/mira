import os
import re
from pathlib import Path
import pandas as pd
import numpy as np
import satellite

FRANKFURT_X, FRANKFURT_Y = 8.6821, 50.1109

CRITERIA = {'cost_lcoe': False, 'grid_capacity_mw': True, 'green_share_pct': True, 'connectivity_score': True}
FACTOR_COLS = ['wind_pct', 'solar_pct', 'hydro_pct', 'nuclear_pct', 'gas_pct', 'coal_pct', 'co2_intensity', 'political_stability']
WEIGHT_KEYS = ['weight_cost', 'weight_grid', 'weight_green', 'weight_connectivity']

COUNTRY_NAMES = {
    'AT': 'Austria', 'BE': 'Belgium', 'CH': 'Switzerland', 'CZ': 'Czechia', 'DE': 'Germany',
    'DK': 'Denmark', 'ES': 'Spain', 'FI': 'Finland', 'FR': 'France', 'GB': 'United Kingdom',
    'GR': 'Greece', 'HU': 'Hungary', 'IE': 'Ireland', 'IT': 'Italy', 'LT': 'Lithuania',
    'LV': 'Latvia', 'NL': 'Netherlands', 'NO': 'Norway', 'PL': 'Poland', 'PT': 'Portugal',
    'RO': 'Romania', 'SE': 'Sweden',
}

DATA_PATH = os.environ.get("ASA_REGION_DATA")
REGION_PATHS = [
    Path(DATA_PATH) if DATA_PATH else None,
    Path(__file__).with_name("data") / "processed_region_data.csv",
    Path(__file__).with_name("processed_region_data.csv"),
    Path.home() / "Downloads" / "processed_region_data.csv",
]
region_csv = next((p for p in REGION_PATHS if p and p.exists()), None)
if region_csv is None:
    raise FileNotFoundError(
        "No region data found. Run `python data_pipeline.py` to generate "
        "data/processed_region_data.csv, or set ASA_REGION_DATA to its path."
    )
base_df = pd.read_csv(region_csv)
REGION_MODE = 'region_name' in base_df.columns


def site_label(bus_id, country):
    name = COUNTRY_NAMES.get(country, country)
    voltage = str(bus_id).rsplit('-', 1)[-1]
    ref = re.search(r'\d{4,}', str(bus_id))
    kind = f"{voltage} kV substation" if voltage.isdigit() else "grid substation"
    return f"{name} — {kind} #{ref.group()[-5:]}" if ref else f"{name} — {kind}"


PUE = 1.2
LOAD_FACTOR = 0.75
HOURS_PER_YEAR = 8760
HEADROOM_FRACTION = 0.05

# Major European data-center / internet-exchange hubs (lon, lat, market weight).
# FLAP-D primary markets carry the most fibre and interconnection; secondary hubs less.
# Source proxy: OpenStreetMap data-center clusters + known IXP locations (DE-CIX, AMS-IX, LINX...).
DC_HUBS = [
    (8.68, 50.11, 1.0),   # Frankfurt (DE-CIX)
    (-0.13, 51.51, 1.0),  # London (LINX)
    (4.90, 52.37, 1.0),   # Amsterdam (AMS-IX)
    (2.35, 48.86, 0.9),   # Paris
    (-6.27, 53.34, 0.8),  # Dublin
    (-3.70, 40.42, 0.6),  # Madrid
    (9.19, 45.46, 0.6),   # Milan
    (21.01, 52.23, 0.5),  # Warsaw
    (18.07, 59.33, 0.5),  # Stockholm
    (12.57, 55.68, 0.5),  # Copenhagen
    (16.37, 48.21, 0.4),  # Vienna
]


def connectivity_from_hubs(x, y):
    score = np.zeros(len(x))
    for hx, hy, weight in DC_HUBS:
        dist = np.sqrt((x - hx) ** 2 + (y - hy) ** 2)
        score = np.maximum(score, weight * (100 - dist * 9))
    return np.clip(score, 8, 100)


def supply_plan(grid_draw_mw, green_pct):
    annual_gwh = round(grid_draw_mw * LOAD_FACTOR * HOURS_PER_YEAR / 1000)
    if green_pct >= 85:
        ppa = "Grid power is already clean enough to meet a 24/7 carbon-free target with minimal extra procurement."
    elif green_pct >= 55:
        ppa = f"Sign a renewable PPA for roughly {round(grid_draw_mw * (0.9 - green_pct / 100))} MW of wind or solar to close the gap to a 90% clean supply."
    else:
        ppa = f"The local grid is carbon-heavy; pair the connection with a {round(grid_draw_mw * 0.6)} MW renewable PPA plus on-site solar and storage to hit a credible clean-energy target."
    return {
        "grid_draw_mw": round(grid_draw_mw),
        "annual_consumption_gwh": annual_gwh,
        "grid_share_pct": round(green_pct),
        "recommendation": ppa,
    }


def run_topsis_optimization(weights_dict, top_n=3, size_mw=None):
    df = base_df.copy()
    grid_draw = size_mw * PUE if size_mw else None

    df['connectivity_score'] = connectivity_from_hubs(df['x'].values, df['y'].values)

    if REGION_MODE:
        df['label'] = df['region_name']
        df['ref'] = df['region_id']
    else:
        df['label'] = [site_label(b, c) for b, c in zip(df['bus_id'], df['country'])]
        df['ref'] = df['bus_id'].astype(str)
    df['country'] = df['country'].map(COUNTRY_NAMES).fillna(df['country'])

    protected = df['x'].between(10.0, 12.5) & df['y'].between(46.0, 48.0)
    filtered_out = [{
        "region": r['label'],
        "reason": f"Zoning violation: location ({round(r['x'], 2)}, {round(r['y'], 2)}) lies inside a protected Natura 2000 area."
    } for _, r in df[protected].head(3).iterrows()]

    df['headroom_mw'] = df['grid_capacity_mw'] * HEADROOM_FRACTION
    undersized = pd.Series(False, index=df.index)
    if grid_draw:
        undersized = df['headroom_mw'] < grid_draw
        for _, r in df[~protected & undersized].sort_values('headroom_mw', ascending=False).head(3).iterrows():
            filtered_out.append({
                "region": r['label'],
                "reason": f"Insufficient grid headroom: about {r['headroom_mw']:.0f} MW of spare capacity cannot host this facility's {grid_draw:.0f} MW draw."
            })

    df = df[~protected & ~undersized & (df['grid_capacity_mw'] >= 20)].reset_index(drop=True)
    if df.empty:
        return {"error": f"No region has enough grid headroom for a {size_mw:.0f} MW facility (≈{grid_draw:.0f} MW draw)."
                if grid_draw else "Zero candidate locations met constraints."}

    matrix = df[list(CRITERIA)].values
    norm = matrix / np.sqrt((matrix ** 2).sum(axis=0))

    weights = np.array([weights_dict.get(k, 0.25) for k in WEIGHT_KEYS])
    if weights.sum() == 0:
        weights = np.ones(4)
    weighted = norm * (weights / weights.sum())

    maximize = np.array(list(CRITERIA.values()))
    mins, maxs = matrix.min(axis=0), matrix.max(axis=0)
    profile = (matrix - mins) / np.where(maxs > mins, maxs - mins, 1)
    profile = np.where(maximize, profile, 1 - profile)
    ideal_best = np.where(maximize, weighted.max(axis=0), weighted.min(axis=0))
    ideal_worst = np.where(maximize, weighted.min(axis=0), weighted.max(axis=0))

    d_best = np.sqrt(((weighted - ideal_best) ** 2).sum(axis=1))
    d_worst = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))
    scores = np.nan_to_num(d_worst / (d_best + d_worst))

    df['topsis_score'] = scores
    top = df.sort_values('topsis_score', ascending=False).drop_duplicates('country').index[:top_n]
    ranking = [{
        "region": df.at[i, 'label'],
        "region_id": df.at[i, 'ref'],
        "country": df.at[i, 'country'],
        "lat": float(df.at[i, 'y']),
        "lon": float(df.at[i, 'x']),
        "score": round(float(scores[i]), 4),
        "substations": int(df.at[i, 'substation_count']) if 'substation_count' in df.columns else None,
        "spare_headroom_mw": round(float(df.at[i, 'headroom_mw'])),
        "raw": {c: round(float(df.at[i, c]), 4) for c in CRITERIA},
        "normalized_weighted": {c: round(float(weighted[i, j]), 4) for j, c in enumerate(CRITERIA)},
        "profile": {c: round(float(profile[i, j]), 4) for j, c in enumerate(CRITERIA)},
        "supply_plan": supply_plan(grid_draw, df.at[i, 'green_share_pct']) if grid_draw else None,
        "factors": {f: float(df.at[i, f]) for f in FACTOR_COLS if f in df.columns},
    } for i in top]

    if ranking and satellite.available():
        ranking[0]["satellite"] = {
            "infra_score": satellite.infra_score(ranking[0]["lat"], ranking[0]["lon"]),
            "source": "AlphaEarth embeddings (64-dim, 10 m, 2024)",
        }

    # every candidate region's score for the globe heat map (good=green, bad=red)
    inv_names = {v: k for k, v in COUNTRY_NAMES.items()}
    heatmap = [{"lat": float(df.at[i, 'y']), "lon": float(df.at[i, 'x']),
                "region": df.at[i, 'label'].split(' — ')[0],
                "country": inv_names.get(df.at[i, 'country'], df.at[i, 'country']),
                "score": round(float(scores[i]), 3)}
               for i in df.index]

    return {
        "meta_total_environmental_filtered": int(protected.sum()),
        "meta_undersized_filtered": int(undersized.sum()),
        "facility": {"size_mw": size_mw, "grid_draw_mw": round(grid_draw)} if grid_draw else None,
        "heatmap": heatmap,
        "weights_applied": {k: round(float(w), 3) for k, w in zip(WEIGHT_KEYS, weights / weights.sum())},
        "assumptions": {"pue": PUE, "load_factor": LOAD_FACTOR, "source": "IEA Energy & AI reference values"},
        "data_sources": "PyPSA-Eur grid · Ember prices & clean share · OSM/ITU data-center hubs · IEA PUE",
        "filtered_out": filtered_out,
        "ranking": ranking,
    }
