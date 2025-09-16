import streamlit as st
import pandas as pd
import plotly.express as px
import geopandas as gpd
import pyarrow.parquet as pq
import folium
from streamlit_folium import folium_static
import datetime

st.set_page_config(page_title="NYC Taxi Geospatial Dashboard", layout="wide")
st.image("nyc_taxi_logo.png", width=120)
st.title("NYC Taxi Geospatial Dashboard")

# Load all Parquet files dynamically
import glob
parquet_files = glob.glob('data/yellow_tripdata_*.parquet')
available_months = []
for file in parquet_files:
    fname = file.split('/')[-1].replace('.parquet', '')
    parts = fname.split('_')[-1].split('-')
    if len(parts) == 2:
        available_months.append((int(parts[0]), int(parts[1]), file))
available_months = sorted(available_months)

years = sorted(list(set([y for y, m, f in available_months])))
months_by_year = {y: sorted([m for y2, m, f in available_months if y2 == y]) for y in years}


st.sidebar.header("Select Year and Month")
year = st.sidebar.selectbox("Year", years)
month = st.sidebar.selectbox("Month", months_by_year[year])
weekday_options = ['All', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
weekday = st.sidebar.selectbox("Weekday", weekday_options)
sample_size = st.sidebar.slider("Sample size (rows)", min_value=1000, max_value=50000, value=10000, step=1000)

@st.cache_data(show_spinner=False)
def load_parquet(file):
    # Detect columns in Parquet
    table = pq.read_table(file, columns=None)
    cols = table.schema.names
    # Select only essential columns
    needed = []
    missing = []
    if 'tpep_pickup_datetime' in cols:
        needed.append('tpep_pickup_datetime')
    else:
        missing.append('tpep_pickup_datetime')
    if 'PULocationID' in cols:
        needed.append('PULocationID')
    else:
        missing.append('PULocationID')
    if 'total_amount' in cols:
        needed.append('total_amount')
    else:
        missing.append('total_amount')
    # Always include tip_amount if present
    if 'tip_amount' in cols and 'tip_amount' not in needed:
        needed.append('tip_amount')
    if missing:
        st.error(f"The selected Parquet file is missing required columns: {', '.join(missing)}. Columns found: {', '.join(cols)}")
        st.stop()
    # Always keep pickup datetime
    pickup_col = None
    # Prefer official column name
    if 'tpep_pickup_datetime' in cols:
        pickup_col = 'tpep_pickup_datetime'
        if pickup_col not in needed:
            needed.append(pickup_col)
    else:
        for c in needed:
            if 'pickup' in c and 'datetime' in c:
                pickup_col = c
                break
        if pickup_col is None:
            pickup_col = cols[0]
            needed.append(pickup_col)
    # Read only needed columns
    df = pd.read_parquet(file, columns=needed)
    if len(df) > sample_size:
        df = df.sample(sample_size, random_state=42)
    df[pickup_col] = pd.to_datetime(df[pickup_col])
    return df, pickup_col

selected_file = [f for y, m, f in available_months if y == year and m == month][0]
try:
    df, pickup_col = load_parquet(selected_file)
except Exception as e:
    st.error('Could not load official Parquet data. Please check the selected file.')
    st.stop()

# Load boroughs and zone lookup
gdf_boroughs = gpd.read_file('data/nyc_boroughs.geojson')
zone_lookup = pd.read_csv('data/taxi_zone_lookup.csv')

filtered = df.copy()
if weekday != 'All':
    filtered = filtered[filtered[pickup_col].dt.day_name() == weekday]

# Map PULocationID to zone and borough
if 'PULocationID' in filtered.columns:
    filtered = filtered.merge(zone_lookup, left_on='PULocationID', right_on='LocationID', how='left')

st.subheader("Trip Metrics")
st.write(f"Total trips: {len(filtered)}")
st.write(f"Total revenue: ${filtered['total_amount'].sum():,.2f}")

# Tips summary
if 'tip_amount' in filtered.columns:
    total_tips = filtered['tip_amount'].sum()
    avg_tips = filtered['tip_amount'].mean()
    num_tips = (filtered['tip_amount'] > 0).sum()
    st.write(f"Total tips: ${total_tips:,.2f}")
    st.write(f"Average tip: ${avg_tips:,.2f}")
    st.write(f"Number of trips with tips: {num_tips}")
    st.subheader("Tips Distribution")
    fig_tips = px.histogram(
        filtered,
        x='tip_amount',
        nbins=40,
        title='Distribution of Tips',
        labels={'tip_amount':'Tip Amount (USD)', 'count':'Number of Trips'}
    )
    st.plotly_chart(fig_tips, use_container_width=True)
else:
    st.info("No tip_amount column found in the selected data.")

fig_hour = px.bar(filtered, x=filtered[pickup_col].dt.hour, title='Trips by Hour', labels={'x':'Hour', 'y':'Trip Count'})
st.plotly_chart(fig_hour, use_container_width=True)


st.subheader("Pickup Locations Map")
if not filtered.empty:
    sample = filtered.copy()
    if len(sample) > 2000:
        sample = sample.sample(2000, random_state=42)
    # Use zone centroid from GeoJSON for each pickup
    zone_centroids = gdf_boroughs.set_index('borough').geometry.centroid
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=11)
    folium.GeoJson(
        gdf_boroughs,
        name="NYC Boroughs",
        style_function=lambda x: {
            'fillColor': '#ffff00',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.2
        },
        tooltip=folium.GeoJsonTooltip(fields=['borough'], aliases=['Borough:'])
    ).add_to(m)
    for _, row in sample.iterrows():
        # Get centroid for borough
        if pd.notnull(row['Borough']):
            centroid = zone_centroids.get(row['Borough'])
            if centroid is not None:
                folium.CircleMarker(
                    location=[centroid.y, centroid.x],
                    radius=3,
                    color='blue',
                    fill=True,
                    fill_opacity=0.6
                ).add_to(m)
    folium_static(m, width=900, height=500)
else:
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=11)
    folium.GeoJson(
        gdf_boroughs,
        name="NYC Boroughs",
        style_function=lambda x: {
            'fillColor': '#ffff00',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.2
        },
        tooltip=folium.GeoJsonTooltip(fields=['borough'], aliases=['Borough:'])
    ).add_to(m)
    folium_static(m, width=900, height=500)
    st.info("No trips for selected filters.")

st.set_page_config(page_title="Dashboard Táxi NYC", layout="wide")
st.title("Dashboard Geoespacial - Táxi NYC")
st.subheader("Métricas por Bairro")
# Definir métricas por bairro
if not filtered.empty and 'Borough' in filtered.columns and 'total_amount' in filtered.columns:
    metrics = filtered.groupby('Borough').agg(
        trip_count=('tpep_pickup_datetime', 'count'),
        total_revenue=('total_amount', 'sum')
    ).reset_index()
    st.dataframe(metrics)
else:
    st.info("Dados de métricas por bairro não disponíveis.")
# Assegure que fig_count, fig_revenue, html_map estejam definidos antes de usar
# st.plotly_chart(fig_count, use_container_width=True)
# st.plotly_chart(fig_revenue, use_container_width=True)
# st.subheader("Mapa Interativo de Embarques/Desembarques")
# st.components.v1.html(html_map, height=600)

