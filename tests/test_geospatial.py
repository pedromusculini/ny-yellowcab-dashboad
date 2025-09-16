import sys
import os
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.geospatial_analysis import geospatial_analysis

def test_borough_assignment():
    # Example data
    df = pd.DataFrame({
        'pickup_longitude': [-73.9857, -73.9524],
        'pickup_latitude': [40.7484, 40.7769],
        'trip_id': [1, 2],
        'total_amount': [10.5, 20.0]
    })
    # Assuming the GeoJSON file exists at data/nyc_boroughs.geojson
    geojson_path = 'data/nyc_boroughs.geojson'
    geospatial_analysis(df, geojson_path)
    assert os.path.exists('docs/borough_metrics.csv')
    metrics = pd.read_csv('docs/borough_metrics.csv')
    assert 'borough' in metrics.columns
    assert 'trip_id' in metrics.columns
    assert 'total_amount' in metrics.columns

def test_clustering():
    # Example data for clustering
    df = pd.DataFrame({
        'pickup_longitude': [-73.9857]*101 + [-73.9524]*101,
        'pickup_latitude': [40.7484]*101 + [40.7769]*101,
        'trip_id': list(range(202)),
        'total_amount': [10.5]*202
    })
    geojson_path = 'data/nyc_boroughs.geojson'
    geospatial_analysis(df, geojson_path)
    # Check if 'cluster' column was created
    assert 'cluster' in df.columns
