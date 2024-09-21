# visualization.py

import json
import time
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import os

# Initialize the Dash app
app = dash.Dash(__name__)
app.title = 'Traffic Simulation Visualization'

# Define the layout
app.layout = html.Div(children=[
    html.H1(children='Traffic Simulation Visualization'),
    dcc.Graph(id='simulation-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1*1000,  # Update every 1 second
        n_intervals=0
    )
])

def create_road_lines(roads_df):
    """Create line shapes for roads."""
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
            }
        }
        road_shapes.append(road_shape)
    return road_shapes

def create_road_blockages(roads_df, road_blockages):
    """Modify road shapes to indicate blockages."""
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
                    }
                }
                blockage_shapes.append(blockage_shape)
    return blockage_shapes

def create_traffic_light_markers(intersections_df, traffic_lights):
    """Create markers for traffic lights."""
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
    # Path to the simulation state file
    state_file = 'sim_state.json'

    # Check if the state file exists
    if not os.path.exists(state_file):
        # If the file doesn't exist yet, return an empty figure
        fig = go.Figure()
        fig.update_layout(title='Waiting for simulation data...')
        return fig

    try:
        # Read the simulation state from the JSON file
        with open(state_file, 'r') as f:
            state = json.load(f)
    except json.JSONDecodeError:
        # If the file is being written to and is incomplete, skip this update
        fig = go.Figure()
        fig.update_layout(title='Loading simulation data...')
        return fig

    # Extract data from the state
    vehicles = state.get('vehicles', {})
    traffic_lights = state.get('traffic_lights', {})
    road_blockages = state.get('road_blockages', {})
    intersections = state.get('intersections', {})
    roads = state.get('roads', {})

    # Convert data to DataFrames
    vehicles_df = pd.DataFrame.from_dict(vehicles, orient='index').reset_index()
    vehicles_df.rename(columns={'index': 'vehicle_id'}, inplace=True)

    roads_df = pd.DataFrame.from_dict(roads, orient='index').reset_index()
    roads_df.rename(columns={'index': 'road_id'}, inplace=True)

    intersections_df = pd.DataFrame.from_dict(intersections, orient='index').reset_index()
    intersections_df.rename(columns={'index': 'intersection_id'}, inplace=True)

    # Prepare the figure
    fig = go.Figure()

    # Add road lines
    if not roads_df.empty:
        road_shapes = create_road_lines(roads_df)
        fig.update_layout(shapes=road_shapes)

    # Add road blockages
    if road_blockages:
        blockage_shapes = create_road_blockages(roads_df, road_blockages)
        # Append blockage shapes to the existing shapes
        fig.update_layout(shapes=fig.layout.shapes + tuple(blockage_shapes))

    # Add traffic lights
    if traffic_lights:
        traffic_light_markers = create_traffic_light_markers(intersections_df, traffic_lights)
        for marker in traffic_light_markers:
            fig.add_trace(marker)

    # Add vehicles
    if not vehicles_df.empty:
        # Map vehicle positions to x and y coordinates on the roads
        vehicle_positions = []
        for _, vehicle in vehicles_df.iterrows():
            road_id = vehicle['road']
            road = roads_df.loc[roads_df['road_id'] == road_id]
            if not road.empty:
                road = road.iloc[0]
                # Calculate vehicle position along the road
                t = vehicle['position'] / road['length']
                t = max(0, min(t, 1))  # Ensure t is between 0 and 1
                x = road['start_x'] + t * (road['end_x'] - road['start_x'])
                y = road['start_y'] + t * (road['end_y'] - road['start_y'])
                vehicle_positions.append({'vehicle_id': vehicle['vehicle_id'], 'x': x, 'y': y})
        vehicle_positions_df = pd.DataFrame(vehicle_positions)

        fig.add_trace(go.Scatter(
            x=vehicle_positions_df['x'],
            y=vehicle_positions_df['y'],
            mode='markers',
            marker=dict(size=10, color='blue', symbol='car'),
            name='Vehicles',
            hovertext=vehicle_positions_df['vehicle_id']
        ))

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
