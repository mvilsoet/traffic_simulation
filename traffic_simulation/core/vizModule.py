import json
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import os
import boto3
from traffic_simulation.utils import sqsUtility

# Initialize the Dash app
app = dash.Dash(__name__)
app.title = 'Traffic Simulation Visualization'

# Load configuration
config_file = os.path.join(os.path.dirname(__file__), 'config.json')
with open(config_file, 'r') as config_file:
    CONFIG = json.load(config_file)
    QUEUES = CONFIG.get('VIZ_MOD_QUEUES', ['SimulationEvents'])
    MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 10)
    WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 1)
    AWS_REGION = CONFIG.get('AWS_REGION', 'us-east-1')

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=AWS_REGION)

# Initialize SQS client and get queue URLs
queue_urls = sqsUtility.get_queue_urls(QUEUES)
simulation_events_queue_url = queue_urls['SimulationEvents']

# Shared variable to store the latest state
latest_state = {}

# Define the layout
app.layout = html.Div(children=[
    dcc.Graph(id='simulation-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1 * 1000,  # Update every 1 second
        n_intervals=0
    )
])

# Helper function to poll SQS and process StateExported messages
def poll_and_update_state():
    global latest_state  # Use shared variable for latest state

    try:
        messages = sqsUtility.receive_messages(
            simulation_events_queue_url,
            max_number_of_messages=MAX_NUMBER_OF_MESSAGES,
            wait_time_seconds=0  # Poll without blocking
        )

        # Process each message
        for message in messages:
            body = json.loads(message['Body'])
            message_type = body.get('type')

            if message_type == 'StateExported':
                data = body.get('data', {})
                s3_bucket = data.get('s3_bucket')
                s3_key = data.get('s3_key')
                tick_number = data.get('tick_number')

                # Download the sim_state.json from S3
                if s3_bucket and s3_key:
                    try:
                        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                        state_json = response['Body'].read().decode('utf-8')
                        latest_state = json.loads(state_json)  # Update latest state

                        print(f"Updated state for tick {tick_number}")
                    except Exception as e:
                        print(f"Error downloading state from S3: {e}")

            # Delete the message from the queue once it's processed
            sqsUtility.delete_message(simulation_events_queue_url, message['ReceiptHandle'])

    except Exception as e:
        print(f"Error receiving messages: {e}")

# Helper function to create road lines
def create_road_lines(roads_df):
    road_shapes = []
    for _, road in roads_df.iterrows():
        road_shape = {
            'type': 'line',
            'x0': road['start_x'],
            'y0': road['start_y'],
            'x1': road['end_x'],
            'y1': road['end_y'],
            'line': {
                'width': 4,
                'color': 'gray'
            },
            'layer': 'below'
        }
        road_shapes.append(road_shape)
    return road_shapes

# Helper function to create road blockages
def create_road_blockages(roads_df, road_blockages):
    blockage_shapes = []
    for road_id, blocked in road_blockages.items():
        if blocked:
            road = roads_df.loc[roads_df['road_id'] == road_id]
            if not road.empty:
                road = road.iloc[0]
                blockage_shape = {
                    'type': 'line',
                    'x0': road['start_x'],
                    'y0': road['start_y'],
                    'x1': road['end_x'],
                    'y1': road['end_y'],
                    'line': {
                        'width': 6,
                        'color': 'red'
                    },
                    'layer': 'below'
                }
                blockage_shapes.append(blockage_shape)
    return blockage_shapes

# Helper function to create traffic light markers
def create_traffic_light_markers(intersections_df, traffic_lights):
    traffic_light_markers = []
    for intersection_id, state in traffic_lights.items():
        intersection = intersections_df.loc[intersections_df['intersection_id'] == intersection_id]
        if not intersection.empty:
            intersection = intersection.iloc[0]
            color = {'green': 'green', 'yellow': 'yellow', 'red': 'red'}.get(state, 'gray')
            marker = go.Scatter(
                x=[intersection['x']],
                y=[intersection['y']],
                mode='markers',
                marker=dict(
                    size=20,
                    color=color,
                    symbol='circle'
                ),
                name=f'Traffic Light {intersection_id}'
            )
            traffic_light_markers.append(marker)
    return traffic_light_markers

# Callback to update the graph
@app.callback(
    Output('simulation-graph', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_graph(n):
    # Call the function to poll SQS and update the latest state
    poll_and_update_state()

    # If no state is available, display a placeholder graph
    if not latest_state:
        fig = go.Figure()
        fig.update_layout(title='Waiting for simulation data...')
        return fig

    # Extract data from the latest state
    state = latest_state
    vehicles = state.get('vehicles', {})
    traffic_lights = state.get('traffic_lights', {})
    road_blockages = state.get('road_blockages', {})
    intersections = state.get('intersections', {})
    roads = state.get('roads', {})

    # Prepare the figure
    fig = go.Figure()

    # Convert roads to DataFrame and plot them
    if roads:
        roads_df = pd.DataFrame.from_dict(roads, orient='index').reset_index()
        roads_df.rename(columns={'index': 'road_id'}, inplace=True)

        # Add road lines
        road_shapes = create_road_lines(roads_df)
        fig.update_layout(shapes=road_shapes)

        # Add road blockages
        if road_blockages:
            blockage_shapes = create_road_blockages(roads_df, road_blockages)
            fig.update_layout(shapes=fig.layout.shapes + tuple(blockage_shapes))

    # Add traffic lights
    if traffic_lights and intersections:
        intersections_df = pd.DataFrame.from_dict(intersections, orient='index').reset_index()
        intersections_df.rename(columns={'index': 'intersection_id'}, inplace=True)
        traffic_light_markers = create_traffic_light_markers(intersections_df, traffic_lights)
        for marker in traffic_light_markers:
            fig.add_trace(marker)

    # Add vehicle positions
    if vehicles and roads:
        vehicles_df = pd.DataFrame.from_dict(vehicles, orient='index').reset_index()
        vehicles_df.rename(columns={'index': 'vehicle_id'}, inplace=True)

        vehicle_positions = []
        for _, vehicle in vehicles_df.iterrows():
            road_id = vehicle['road']
            road = roads_df.loc[roads_df['road_id'] == road_id]
            if not road.empty:
                road = road.iloc[0]
                t = vehicle['position'] / road['length'] if 'length' in road and road['length'] > 0 else 0.5
                x = road['start_x'] + t * (road['end_x'] - road['start_x'])
                y = road['start_y'] + t * (road['end_y'] - road['start_y'])
                vehicle_positions.append({'vehicle_id': vehicle['vehicle_id'], 'x': x, 'y': y})

        if vehicle_positions:
            vehicle_positions_df = pd.DataFrame(vehicle_positions)
            fig.add_trace(go.Scatter(
                x=vehicle_positions_df['x'],
                y=vehicle_positions_df['y'],
                mode='markers',
                marker=dict(size=10, color='blue', symbol='triangle-up'),
                name='Vehicles',
                hovertext=vehicle_positions_df['vehicle_id']
            ))

    # Finalize the layout of the graph
    fig.update_layout(
        title='Traffic Simulation Visualization',
        xaxis_title='X Coordinate',
        yaxis_title='Y Coordinate',
        xaxis=dict(scaleanchor='y', scaleratio=1),
        yaxis=dict(scaleanchor='x', scaleratio=1),
        showlegend=True,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    return fig

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
