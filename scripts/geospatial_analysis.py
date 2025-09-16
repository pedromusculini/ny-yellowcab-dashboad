import geopandas as gpd
import folium
from sklearn.cluster import DBSCAN
import pandas as pd

def geospatial_analysis(df, geojson_path='data/nyc_boroughs.geojson'):
    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['pickup_longitude'], df['pickup_latitude']))

    # Map to boroughs using GeoJSON
    boroughs = gpd.read_file(geojson_path)
    gdf_borough = gpd.sjoin(gdf, boroughs, how='left', predicate='within')
    borough_metrics = gdf_borough.groupby('borough').agg({'trip_id': 'count', 'total_amount': 'sum'})

    # Clustering for hotspots
    coords = df[['pickup_latitude', 'pickup_longitude']].values
    db = DBSCAN(eps=0.01, min_samples=100).fit(coords)
    df['cluster'] = db.labels_

    # Generate interactive map
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=11)
    # Add points or clusters to the map
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row['pickup_latitude'], row['pickup_longitude']],
            radius=2,
            color='red' if row['cluster'] != -1 else 'blue',
            fill=True,
            fill_opacity=0.6
        ).add_to(m)
    m.save('docs/pickup_dropoff_map.html')

    # Save metrics by borough
    borough_metrics.to_csv('docs/borough_metrics.csv')

if __name__ == "__main__":
    # Example: Load official Parquet file
    import glob
    parquet_files = glob.glob('data/yellow_tripdata_*.parquet')
    if parquet_files:
        df = pd.read_parquet(parquet_files[0])
        # Create trip_id if not exists
        if 'trip_id' not in df.columns:
            df['trip_id'] = df.index + 1
        geospatial_analysis(df)
    else:
        print('No official Parquet files found in data/.')
