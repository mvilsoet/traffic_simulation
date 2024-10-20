import pandas as pd
import boto3
import os
import json

def generate_initial_state():
    # Define intersections
    intersections = pd.DataFrame({
        'intersection_id': ['A', 'B', 'C', 'D', 'E', 'F'],
        'x': [0, 1, 2, 0, 1, 2],
        'y': [0, 0, 0, 1, 1, 1]
    })

    # Define roads
    roads = pd.DataFrame({
        'road_id': ['A-B', 'B-C', 'D-E', 'E-F', 'A-D', 'B-E', 'C-F', 'A-E', 'B-D', 'C-E'],
        'start': ['A', 'B', 'D', 'E', 'A', 'B', 'C', 'A', 'B', 'C'],
        'end': ['B', 'C', 'E', 'F', 'D', 'E', 'F', 'E', 'D', 'E'],
        'length': [1.0, 1.0, 1.0, 1.0, 1.0, 1.41, 1.41, 1.41, 1.41, 1.41],
        'speed_limit': [50, 50, 50, 50, 50, 40, 40, 40, 40, 40]
    })

    # Merge to get start coordinates
    roads = roads.merge(
        intersections.rename(columns={'intersection_id': 'start', 'x': 'start_x', 'y': 'start_y'}),
        on='start', how='left'
    )

    # Merge to get end coordinates
    roads = roads.merge(
        intersections.rename(columns={'intersection_id': 'end', 'x': 'end_x', 'y': 'end_y'}),
        on='end', how='left'
    )

    # Define traffic lights
    traffic_lights = pd.DataFrame({
        'intersection_id': ['A', 'B', 'C', 'D', 'E', 'F'],
        'state': ['green', 'red', 'yellow', 'green', 'red', 'yellow']
    })

    # Define vehicles
    vehicles = pd.DataFrame({
        'vehicle_id': [f'vehicle_{i}' for i in range(20)],
        'road': ['A-B', 'B-C', 'D-E', 'E-F', 'A-D', 'B-E', 'C-F', 'A-E', 'B-D', 'C-E',
                 'A-B', 'B-C', 'D-E', 'E-F', 'A-D', 'B-E', 'C-F', 'A-E', 'B-D', 'C-E'],
        'position': [0.0] * 20,
        'speed': [20] * 20
    })

    # Define road blockages
    road_blockages = pd.DataFrame({
        'road_id': roads['road_id'],
        'blocked': [False] * len(roads)
    })

    # List of DataFrames and corresponding file names
    dataframes = {
        'intersections.parquet': intersections,
        'roads.parquet': roads,
        'traffic_lights.parquet': traffic_lights,
        'vehicles.parquet': vehicles,
        'road_blockages.parquet': road_blockages
    }

    # Save each DataFrame to a separate Parquet file
    for file_name, df in dataframes.items():
        df.to_parquet(file_name)

    print("Initial state Parquet files generated locally.")

    # Initialize S3 client
    s3 = boto3.client('s3')

    # Upload files to S3 and delete local copies
    bucket_name = 'trafficsimulation'
    s3_links = {}
    for file_name in dataframes.keys():
        try:
            s3.upload_file(file_name, bucket_name, file_name)
            os.remove(file_name)
            print(f"Uploaded and deleted local file: {file_name}")
            s3_link = f"s3://{bucket_name}/{file_name}"
            s3_links[file_name] = s3_link
            print(f"S3 Link: {s3_link}")
        except Exception as e:
            print(f"Error uploading {file_name}: {e}")

    print(f"All Parquet files uploaded to S3 bucket '{bucket_name}' and local files deleted.")

    print("S3 Links to Parquet files:")
    print(json.dumps(s3_links, indent=4))


if __name__ == "__main__":
    generate_initial_state()
