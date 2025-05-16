import dash
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import itertools
import os
import requests
import io

url = "https://drive.google.com/uc?export=download&id=1Tin9XoeDG_0iGazpn5n7vnfw0mHnlynq"
response = requests.get(url)
description=pd.read_csv(io.BytesIO(response.content))

url = "https://drive.google.com/uc?export=download&id=1Ijbh2EUBGmYQK5-ejdipHK6rVcEodiDZ"
response = requests.get(url)
data = pd.read_feather(io.BytesIO(response.content))

data['createdAt'] = pd.to_datetime(data['createdAt'])
desc_map = dict(zip(description["Topic Number"], description["Description"]))

# Initialize the Dash app
app = Dash(__name__)
server = app.server

# Function to generate color mapping with cycling
def generate_color_mapping(column_data, palette):
    unique_values = sorted(column_data.dropna().unique())
    return {value: color for value, color in zip(unique_values, itertools.cycle(palette))}

# Precompute consistent color mapping for clusters
color_mapping = {
    'Topic Number': generate_color_mapping(data['Topic Number'], px.colors.qualitative.Alphabet),
}

# Layout for the Dash app
app.layout = html.Div([
    dcc.Graph(id='cluster-plot', style={'height': '60vh', 'width': '90vh', 'margin': '0px', 'padding' : '0px'}),

    html.Div([
        html.Label("Filter by Date:", style={'margin': '0px', 'padding' : '0px', 'fontFamily': 'Arial, sans-serif'}),
        dcc.Slider(
            id='date-slider',
            min=data['createdAt'].min().timestamp(),
            max=data['createdAt'].max().timestamp(),
            value=data['createdAt'].max().timestamp(),
            marks={int(dt.timestamp()): { 'label': dt.strftime('%Y-%m-%d'), 'style': {'fontSize': '14px', 'color': '#333', 'fontSize': '14px', 'fontFamily': 'Arial, sans-serif'} } for dt in pd.date_range(data['createdAt'].min(), data['createdAt'].max(), freq='MS')},
            step=86400         # One day in seconds
        )
    ], style={'margin': '0px', 'width': '90vh'}),

    html.Div(id='hover-description', style={'margin': '10px', 'width': '90vh', 'fontFamily': 'Arial, sans-serif', 'whiteSpace': 'pre-wrap'})
])

@app.callback(
    Output('cluster-plot', 'figure'),
    Input('date-slider', 'value'),
    State('cluster-plot', 'figure')
)

def update_plot(date_slider_value, current_figure):

    ctx = dash.callback_context
    triggered = ctx.triggered[0]['prop_id']

    # Convert slider value to datetime
    date_filter = pd.to_datetime(date_slider_value, unit='s').tz_localize('UTC')

    x_range = None
    y_range = None

    # Retain the axis ranges if the slider triggered the callback
    if triggered == 'date-slider.value' and current_figure:
        x_range = current_figure['layout']['xaxis'].get('range', None)
        y_range = current_figure['layout']['yaxis'].get('range', None)

    filtered_data = data[data['createdAt'] <= date_filter]

    fig = px.scatter(
        filtered_data, x='x', y='y', color='Topic Number', size='marker_size', render_mode='webgl',
        hover_data={'Topic Number': True, 'Topic Label': True, 'Toxicity': True, 'Number of Posts': True, 'createdAt': False, 'marker_size':False, 'x': False, 'y':False},
        custom_data=['Topic Number'],
        title=f'157 Topics of U.S. Immigration Posts on X<br>(April 17th to October 27th, 2023)',
        color_discrete_map=color_mapping['Topic Number'],
        category_orders={
            'Topic Number': sorted(
                filtered_data['Topic Number'].dropna().astype(str).unique(),
                key=lambda x: int(x.split(' ')[-1])
            )
        }
    )
    fig.update_layout(
        xaxis=dict(
            title='',  # Remove x-axis title
            showgrid=False,  # Remove x-axis gridlines
            showticklabels=False  # Remove x-axis ticks
        ),
        yaxis=dict(
            title='',  # Remove y-axis title
            showgrid=False,  # Remove y-axis gridlines
            showticklabels=False  # Remove y-axis ticks
        ),
        plot_bgcolor='white',  # Remove plot background color
        paper_bgcolor='white'  # Remove figure background color
    )

    fig.update_traces(marker=dict(line=dict(width=0)))
        
    # Apply the retained axis ranges to the figure
    if x_range and y_range:
        fig.update_layout(xaxis_range=x_range, yaxis_range=y_range)

    return fig

@app.callback(
    Output('hover-description', 'children'),
    Input('cluster-plot', 'hoverData'),
    prevent_initial_call=True
)
def display_hover_description(hoverData):
    # If there's no hover, show a default prompt
    if not hoverData:
        return "Hover over a point to see its description."
    
    point = hoverData['points'][0]
    cdata = point.get('customdata', [])

    # Extract each cluster ID from customdata
    cls2_val= cdata[0]

    desc = desc_map.get(cls2_val, "No description found".format(cls2_val))
    return f"{desc}"

# Run the Dash app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)