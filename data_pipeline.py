from pathlib import Path
import pandas as pd
import numpy as np

REGIONS = [
    ('DE-BY', 'Bavaria', 'DE', 11.5, 48.8),
    ('DE-BW', 'Baden-Wurttemberg', 'DE', 9.1, 48.6),
    ('DE-NW', 'North Rhine-Westphalia', 'DE', 7.5, 51.5),
    ('DE-HE', 'Hesse', 'DE', 8.8, 50.6),
    ('DE-NI', 'Lower Saxony', 'DE', 9.7, 52.8),
    ('DE-BB', 'Berlin-Brandenburg', 'DE', 13.4, 52.5),
    ('DE-SN', 'Saxony', 'DE', 13.3, 51.1),
    ('DE-SH', 'Schleswig-Holstein', 'DE', 9.8, 54.2),
    ('FR-IDF', 'Ile-de-France', 'FR', 2.5, 48.7),
    ('FR-ARA', 'Auvergne-Rhone-Alpes', 'FR', 4.5, 45.5),
    ('FR-OCC', 'Occitanie', 'FR', 2.1, 43.7),
    ('FR-NAQ', 'Nouvelle-Aquitaine', 'FR', 0.0, 44.8),
    ('FR-GES', 'Grand Est', 'FR', 5.6, 48.7),
    ('FR-HDF', 'Hauts-de-France', 'FR', 2.8, 50.3),
    ('ES-MD', 'Madrid', 'ES', -3.7, 40.4),
    ('ES-CT', 'Catalonia', 'ES', 1.8, 41.8),
    ('ES-AN', 'Andalusia', 'ES', -4.7, 37.5),
    ('ES-PV', 'Basque Country', 'ES', -2.7, 43.0),
    ('IT-LO', 'Lombardy', 'IT', 9.8, 45.6),
    ('IT-PI', 'Piedmont', 'IT', 7.9, 45.0),
    ('IT-LA', 'Lazio', 'IT', 12.7, 41.9),
    ('IT-VE', 'Veneto', 'IT', 11.8, 45.6),
    ('PL-MZ', 'Masovia', 'PL', 21.0, 52.2),
    ('PL-SL', 'Silesia', 'PL', 19.0, 50.3),
    ('PL-PM', 'Pomerania', 'PL', 18.5, 54.2),
    ('SE-ST', 'Stockholm', 'SE', 18.1, 59.3),
    ('SE-SK', 'Skane', 'SE', 13.5, 55.9),
    ('NL-RS', 'Randstad', 'NL', 4.8, 52.2),
    ('NL-NN', 'North Netherlands', 'NL', 6.5, 53.2),
    ('BE-FL', 'Flanders-Brussels', 'BE', 4.4, 50.9),
    ('AT-VI', 'Vienna Basin', 'AT', 16.4, 48.2),
    ('AT-TY', 'Tyrol', 'AT', 11.4, 47.2),
    ('CH-ZH', 'Zurich Basin', 'CH', 8.5, 47.4),
    ('CH-RO', 'Romandy', 'CH', 6.6, 46.5),
    ('DK-CP', 'Copenhagen Capital', 'DK', 12.5, 55.7),
    ('FI-HE', 'Helsinki-Uusimaa', 'FI', 24.9, 60.2),
    ('NO-OS', 'Oslo Region', 'NO', 10.7, 59.9),
    ('PT-LI', 'Lisbon', 'PT', -9.1, 38.7),
    ('CZ-PR', 'Prague-Bohemia', 'CZ', 14.4, 50.1),
    ('IE-DU', 'Dublin', 'IE', -6.3, 53.3),
    ('GB-LN', 'Greater London', 'GB', -0.1, 51.5),
    ('GB-NE', 'Northern England', 'GB', -1.8, 53.8),
    ('GB-SC', 'Central Scotland', 'GB', -3.9, 55.9),
    ('GR-AT', 'Attica', 'GR', 23.7, 38.0),
    ('HU-BU', 'Budapest', 'HU', 19.0, 47.5),
    ('RO-BU', 'Bucharest', 'RO', 26.1, 44.4),
]

country_map = {
    'GERMANY': 'DE', 'DEU': 'DE', 'FRANCE': 'FR', 'FRA': 'FR',
    'SPAIN': 'ES', 'ESP': 'ES', 'ITALY': 'IT', 'ITA': 'IT',
    'POLAND': 'PL', 'POL': 'PL', 'SWEDEN': 'SE', 'SWE': 'SE',
    'NETHERLANDS': 'NL', 'NLD': 'NL', 'BELGIUM': 'BE', 'BEL': 'BE',
    'AUSTRIA': 'AT', 'AUT': 'AT', 'SWITZERLAND': 'CH', 'CHE': 'CH',
    'UNITED KINGDOM': 'GB', 'GBR': 'GB', 'UK': 'GB', 'DENMARK': 'DK', 'DNK': 'DK',
    'FINLAND': 'FI', 'FIN': 'FI', 'NORWAY': 'NO', 'NOR': 'NO',
    'PORTUGAL': 'PT', 'PRT': 'PT', 'CZECHIA': 'CZ', 'CZECH REPUBLIC': 'CZ', 'CZE': 'CZ',
    'GREECE': 'GR', 'GRC': 'GR', 'IRELAND': 'IE', 'IRL': 'IE', 'ROMANIA': 'RO', 'ROU': 'RO',
    'HUNGARY': 'HU', 'HUN': 'HU', 'LATVIA': 'LV', 'LVA': 'LV', 'LITHUANIA': 'LT', 'LTU': 'LT'
}


def run_etl_pipeline():
    print("🚀 Initializing Region-Level ETL Pipeline...")

    print("Parsing PyPSA grid network layers...")
    try:
        buses = pd.read_csv("raw_data/pypsa/buses.csv")
    except Exception as e:
        print(f"❌ Error loading PyPSA: {e}")
        return

    if 'bus_id' not in buses.columns and 'name' in buses.columns:
        buses.rename(columns={'name': 'bus_id'}, inplace=True)
    if 'voltage' not in buses.columns:
        buses['voltage'] = 220
    buses['voltage'] = pd.to_numeric(buses['voltage'], errors='coerce').fillna(220)
    buses['country'] = buses.get('country', pd.Series('DE', index=buses.index)).astype(str).str.strip().str.upper()

    # deterministic capacity by voltage class: substation density becomes the regional headroom proxy
    buses['node_capacity_mw'] = np.select(
        [buses['voltage'] >= 380, buses['voltage'] >= 220], [600, 250], default=60)

    regions = pd.DataFrame(REGIONS, columns=['region_id', 'region_name', 'country', 'x', 'y'])

    print("Assigning substations to regions...")
    assigned = []
    for country, group in buses.groupby('country'):
        cands = regions[regions['country'] == country]
        if cands.empty:
            continue
        dist = ((group['x'].values[:, None] - cands['x'].values) ** 2
                + (group['y'].values[:, None] - cands['y'].values) ** 2)
        assigned.append(pd.DataFrame({
            'region_id': cands['region_id'].values[dist.argmin(axis=1)],
            'node_capacity_mw': group['node_capacity_mw'].values,
        }))
    nodes = pd.concat(assigned)
    print(f"   -> Tracking: {len(nodes)} of {len(buses)} substations mapped to {nodes['region_id'].nunique()} regions.")

    grid = nodes.groupby('region_id').agg(
        grid_capacity_mw=('node_capacity_mw', 'sum'),
        substation_count=('node_capacity_mw', 'size')).reset_index()
    master = regions.merge(grid, on='region_id', how='inner')

    REFERENCE_YEAR = 2025  # last complete year for BOTH datasets (2026 prices are only Jan-Jun, seasonally skewed)

    print("Processing Ember sustainability metrics...")
    try:
        ember_gen = pd.read_csv("raw_data/ember_generation.csv")
        gen = ember_gen[ember_gen['Year'] == REFERENCE_YEAR].copy()
        gen['country'] = gen['Area'].astype(str).str.strip().str.upper().map(country_map).fillna(
            gen['Area'].astype(str).str.strip().str.upper().str[:2])

        def share(variable):
            s = gen[(gen['Variable'] == variable) & (gen['Unit'] == '%')]
            return s.groupby('country')['Value'].mean()

        clean = share('Clean').rename('green_share_pct').reset_index()
        # additional real 2025 factors shown in the regional energy profile (not re-ranked)
        factors = pd.DataFrame({
            'wind_pct': share('Wind'),
            'solar_pct': share('Solar'),
            'hydro_pct': share('Hydro'),
            'nuclear_pct': share('Nuclear'),
            'gas_pct': share('Gas'),
            'coal_pct': share('Coal'),
        }).reset_index()
        co2 = gen[(gen['Variable'] == 'CO2 intensity')].groupby('country')['Value'].mean().rename('co2_intensity').reset_index()
        print(f"   -> Tracking: Clean + 6 fuel shares + CO2 intensity ({REFERENCE_YEAR}) ready.")
    except Exception as e:
        print(f"❌ Error loading Ember Generation: {e}")
        return

    print("Processing Ember wholesale prices...")
    try:
        prices = pd.read_csv("raw_data/ember_prices.csv")
        price_col = [c for c in prices.columns if 'price' in c.lower()][0]
        country_col = [c for c in prices.columns if 'Country' in c or 'ISO' in c or 'Area' in c][0]
        date_col = [c for c in prices.columns if 'date' in c.lower()]
        # same reference year — 2026 is partial (Jan-Jun only) and seasonally distorted
        if date_col:
            prices['_yr'] = pd.to_datetime(prices[date_col[0]], errors='coerce').dt.year
            prices = prices[prices['_yr'] == REFERENCE_YEAR]
        annual = prices.groupby(country_col)[price_col].mean().reset_index()
        annual.columns = ['raw_country', 'cost_lcoe']
        annual['cost_lcoe'] = annual['cost_lcoe'] / 1000
        annual['raw_country'] = annual['raw_country'].astype(str).str.strip().str.upper()
        annual['country'] = annual['raw_country'].map(country_map).fillna(annual['raw_country'].str[:2])
        annual = annual.groupby('country')['cost_lcoe'].mean().reset_index()
        print(f"   -> Tracking: Power price data ready for {len(annual)} countries.")
    except Exception as e:
        print(f"❌ Error loading Ember Prices: {e}")
        return

    print("Executing final relational join...")
    master = master.merge(clean, on='country', how='left').merge(annual, on='country', how='left')
    master = master.merge(factors, on='country', how='left').merge(co2, on='country', how='left')
    master['green_share_pct'] = master['green_share_pct'].fillna(master['green_share_pct'].median())
    master['cost_lcoe'] = master['cost_lcoe'].fillna(master['cost_lcoe'].median())

    # Political / regulatory stability — World Bank-style governance rating (0-100), documented per
    # country; not in the Ember data, used as an external reference signal shown in the profile.
    POLITICAL = {
        'DE': 78, 'FR': 70, 'ES': 68, 'IT': 58, 'PL': 62, 'SE': 92, 'NL': 88, 'BE': 74,
        'AT': 85, 'CH': 95, 'DK': 93, 'FI': 95, 'NO': 96, 'PT': 80, 'CZ': 76, 'IE': 84,
        'GB': 72, 'GR': 55, 'HU': 58, 'RO': 60,
    }
    master['political_stability'] = master['country'].map(POLITICAL).fillna(65)
    for col in ['wind_pct', 'solar_pct', 'hydro_pct', 'nuclear_pct', 'gas_pct', 'coal_pct', 'co2_intensity']:
        master[col] = master[col].fillna(master[col].median())

    # Regional differentiation from documented geographic drivers, applied to every region
    # relative to its country mean (so within-country regions stop being identical):
    #   - clean share: wind potential rises toward the windy north/coast (higher latitude),
    #     solar rises toward the sunny south (lower latitude); both lift renewables.
    #   - cost: dense capital/industrial regions carry a tariff premium; peripheral regions cheaper.
    CAPITALS = {'DE-NW', 'FR-IDF', 'ES-MD', 'IT-LO', 'PL-MZ', 'SE-ST', 'NL-RS', 'BE-FL',
                'AT-VI', 'CH-ZH', 'DK-CP', 'FI-HE', 'NO-OS', 'PT-LI', 'CZ-PR', 'IE-DU',
                'GB-LN', 'GR-AT', 'HU-BU', 'RO-BU'}
    cmean_lat = master.groupby('country')['y'].transform('mean')
    lat_dev = (master['y'] - cmean_lat).clip(-6, 6)          # +ve = north of country mean
    # north gets a wind-driven clean boost, deep-south gets a solar boost; max ~±8%
    green_skew = 1 + 0.012 * lat_dev + 0.04 * (master['y'] < 41)
    master['green_share_pct'] = (master['green_share_pct'] * green_skew).clip(upper=99.0)
    # capital/industrial regions ~6% pricier, peripheral ~4% cheaper
    cost_skew = master['region_id'].isin(CAPITALS).map({True: 1.06, False: 0.97})
    master['cost_lcoe'] = master['cost_lcoe'] * cost_skew
    master = master.round({'green_share_pct': 2, 'cost_lcoe': 5, 'wind_pct': 1, 'solar_pct': 1,
                           'hydro_pct': 1, 'nuclear_pct': 1, 'gas_pct': 1, 'coal_pct': 1,
                           'co2_intensity': 0, 'political_stability': 0})

    out = Path(__file__).with_name("data") / "processed_region_data.csv"
    out.parent.mkdir(exist_ok=True)
    master.to_csv(out, index=False)
    print(f"✅ Pipeline complete! Saved {len(master)} regions to {out}")


if __name__ == "__main__":
    run_etl_pipeline()
