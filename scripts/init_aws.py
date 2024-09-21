# generate_initial_state.py

import pandas as pd
import boto3
import os
import json

def generate_initial_state():
    # Define intersections
    intersections = pd.DataFrame({
        'intersection_id': ['A', 'B', 'C'],
        'x': [0, 1, 0],
        'y': [0, 0, 1]
    })

    # Define roads
    roads = pd.DataFrame({
        'road_id': ['A-B', 'A-C', 'B-C'],
        'start': ['A', 'A', 'B'],
        'end': ['B', 'C', 'C'],
        'length': [1.0, 1.0, 1.41],
        'speed_limit': [50, 50, 40]
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
        'intersection_id': ['A', 'B', 'C'],
        'state': ['green', 'red', 'yellow']
    })

    # Define vehicles
    vehicles = pd.DataFrame({
        'vehicle_id': [f'vehicle_{i}' for i in range(10)],
        'road': ['A-B', 'A-C', 'B-C', 'A-B', 'A-C', 'B-C', 'A-B', 'A-C', 'B-C', 'A-B'],
        'position': [0.0] * 10,
        'speed': [20] * 10
    })

    # Define road blockages
    road_blockages = pd.DataFrame({
        'road_id': ['A-B', 'A-C', 'B-C'],
        'blocked': [False, False, False]
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
    bucket_name = 'your-bucket-name'  # Replace with your actual bucket name
    s3_links = {}
    for file_name in dataframes.keys():
        try:
            s3.upload_file(file_name, bucket_name, file_name)
            os.remove(file_name)
            print(f"Uploaded and deleted local file: {file_name}")
            # Generate S3 link (assuming public access or appropriate permissions)
            s3_link = f"s3://{bucket_name}/{file_name}"
            s3_links[file_name] = s3_link
            print(f"S3 Link: {s3_link}")
        except Exception as e:
            print(f"Error uploading {file_name}: {e}")

    print(f"All Parquet files uploaded to S3 bucket '{bucket_name}' and local files deleted.")

    # Optionally, you can save the S3 links to a config file or print them out
    print("S3 Links to Parquet files:")
    print(json.dumps(s3_links, indent=4))

def initialize_sqs_queues():
    # Load configuration from config.json
    config_file = os.path.join(os.path.dirname(__file__), '../config/config.json')
    with open(config_file, 'r') as config_file:
        CONFIG = json.load(config_file)
        QUEUES = CONFIG.get('QUEUES', [])
        AWS_REGION = CONFIG['aws']['region']

    # Initialize SQS client
    sqs = boto3.client('sqs', region_name=AWS_REGION)

    # Create SQS queues
    for queue_name in QUEUES:
        try:
            if 'fifo' in queue_name.lower():
                # Create FIFO queue
                response = sqs.create_queue(
                    QueueName=queue_name,
                    Attributes={
                        'FifoQueue': 'true',
                        'ContentBasedDeduplication': 'true'
                    }
                )
            else:
                # Create standard queue
                response = sqs.create_queue(QueueName=queue_name)
            print(f"Queue '{queue_name}' created successfully.")
        except sqs.exceptions.QueueNameExists:
            print(f"Queue '{queue_name}' already exists.")
        except Exception as e:
            print(f"Error creating queue '{queue_name}': {e}")

if __name__ == "__main__":
    generate_initial_state()
    initialize_sqs_queues()
