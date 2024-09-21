# visualization.py

import json
import time
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
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
        fig = px.scatter(title='Waiting for simulation data...')
        return fig

    try:
        # Read the simulation state from the JSON file
        with open(state_file, 'r') as f:
            state = json.load(f)
    except json.JSONDecodeError:
        # If the file is being written to and is incomplete, skip this update
        fig = px.scatter(title='Loading simulation data...')
        return fig

    # Extract data from the state
    vehicles = state.get('vehicles', {})
    traffic_lights = state.get('traffic_lights', {})
    road_blockages = state.get('road_blockages', {})
    intersections = state.get('intersections', {})
    roads = state.get('roads', {})

    # Prepare data for plotting
    vehicle_df = pd.DataFrame.from_dict(vehicles, orient='index').reset_index()
    vehicle_df.rename(columns={'index': 'vehicle_id'}, inplace=True)

    # For simplicity, we'll plot vehicles on a scatter plot
    # Assume positions are along the x-axis for demonstration purposes
    if not vehicle_df.empty:
        # For demonstration, assign y=0 to all vehicles
        vehicle_df['y'] = 0

        fig = px.scatter(
            vehicle_df,
            x='position',
            y='y',
            color='road',
            hover_name='vehicle_id',
            title='Vehicle Positions',
            labels={'position': 'Position on Road', 'y': ''}
        )
        fig.update_yaxes(visible=False)
    else:
        fig = px.scatter(title='No Vehicle Data Available')

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
