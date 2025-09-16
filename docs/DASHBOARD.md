
## Interactive Dashboard

To view the NYC taxi geospatial dashboard:

1. Run the following command in the terminal:

    streamlit run scripts/dashboard.py

2. The dashboard will automatically open in your default web browser.

### Features
- View metrics by borough (trip count, revenue)
- Interactive charts (Plotly)
- Interactive pickup/dropoff map (Folium)
- NYC boroughs visualization via GeoJSON

Make sure the files `docs/borough_metrics.csv`, `docs/pickup_dropoff_map.html`, and `data/nyc_boroughs.geojson` are present.
