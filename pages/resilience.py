import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from utils import Header, make_dash_table, build_graph_title
import pandas as pd

import numpy as np
from urllib.request import urlopen
import json
import geopandas as gpd
import datetime

# mapbox token
mapbox_access_token = open(".mapbox_token").read()

# Load data
df_dist = pd.read_csv('./data/duration.csv',dtype={"gid": str})
df_dist['duration'] = df_dist['duration']/60
df_dist['duration'] = df_dist['duration'].replace(np.inf, 999)

amenities = np.unique(df_dist.dest_type)

destinations = pd.read_csv('./data/destinations.csv')

mode_dict = {'walking':'walk','cycling':'bike','driving':'drive'}

# Assign color to legend
colors = ['#008fd5']*len(amenities)#, '#fc4f30', '#e5ae38', '#6d904f', '#8b8b8b', '#810f7c']
colormap = {}
for ind, amenity in enumerate(amenities):
    colormap[amenity] = colors[ind]

pl_deep=[[0.0, 'rgb(253, 253, 204)'],
         [0.1, 'rgb(201, 235, 177)'],
         [0.2, 'rgb(145, 216, 163)'],
         [0.3, 'rgb(102, 194, 163)'],
         [0.4, 'rgb(81, 168, 162)'],
         [0.5, 'rgb(72, 141, 157)'],
         [0.6, 'rgb(64, 117, 152)'],
         [0.7, 'rgb(61, 90, 146)'],
         [0.8, 'rgb(65, 64, 123)'],
         [0.9, 'rgb(55, 44, 80)'],
         [1.0, 'rgb(39, 26, 44)']]


def generate_ecdf_plot(amenity_select, dff_dist,mode_select, x_range=None):
    """
    :param amenity_select: the amenity of interest.
    :return: Figure object
    """
    amenity = amenity_select
    if x_range is None:
        x_range = [dff_dist.duration.min(), dff_dist.duration.max()]


    layout = dict(
        xaxis=dict(
            title="duration (min)".upper(),
            range=(0,60),
            # fixedrange=True,
            titlefont=dict(size=12)
            ),
        yaxis=dict(
            title="% of residents".upper(),
            range=(0,100),
            fixedrange=True,
            titlefont=dict(size=12)
            ),
        font=dict(size=13),
        dragmode="select",
        paper_bgcolor = 'rgba(255,255,255,1)',
		plot_bgcolor = 'rgba(0,0,0,0)',
        bargap=0.05,
        showlegend=False,
        margin=dict(l=40, r=0, t=10, b=30),
        transition = {'duration': 500},
        hovermode="closest",
        # height= 300
    )
    data = []
    # add the cdf for that amenity
    counts, bin_edges = np.histogram(dff_dist.duration, bins=100, density = True)#, weights=df.W.values)
    dx = bin_edges[1] - bin_edges[0]
    new_trace = go.Scatter(
            x=bin_edges, y=np.cumsum(counts)*dx*100,
            opacity=1,
            line=dict(color=colormap[amenity],),
            customdata=[amenity.lower().replace('_',' ')]*len(dff_dist),
            text=[mode_dict[mode_select]]*len(dff_dist),
            hovertemplate = "%{y:.0f}% of residents live within %{x:.1f}min %{text} of a %{customdata} <br>" + "<extra></extra>",
            hoverlabel = dict(font_size=20),
            )

    data.append(new_trace)

    # histogram
    counts, bin_edges = np.histogram(dff_dist.duration, bins=25, density=True)#, weights=df.W.values)
    multiplier = 60/np.max(counts) # 300 if amenity=='supermarket' else 150
    opacity = []
    for i in bin_edges:
        if i >= x_range[0] and i <= x_range[1]:
            opacity.append(0.6)
        else:
            opacity.append(0.1)
    new_trace = go.Bar(
            x=bin_edges, y=counts*multiplier,
            marker_opacity=opacity,
            marker_color=colormap[amenity],
            hoverinfo="skip", hovertemplate="",)
    data.append(new_trace)


    data.append(new_trace)


    return {"data": data, "layout": layout}


def generate_map(amenity, dff_dist, dff_dest, mode_select, city_select, x_range=None):
    """
    Generate map showing the duration to services and the locations of them
    :param amenity: the service of interest.
    :param dff_dest: the lat and lons of the service.
    :param x_range: duration range to highlight.
    :return: Plotly figure object.
    """
    dff_dist = dff_dist.reset_index()

    if city_select == 'hamilton':
        coord = [-37.786110, 175.277281]
        block_data = 'https://raw.githubusercontent.com/urutau-nz/dash-x-minute-city/master/data/block_ham.geojson'
    else:
        coord = [-43.529975, 172.619671]
        block_data = 'https://raw.githubusercontent.com/urutau-nz/dash-x-minute-city/master/data/block_chc.geojson'

    # block data


    layout = go.Layout(
        clickmode="none",
        dragmode="zoom",
        showlegend=True,
        autosize=True,
        hovermode="closest",
        margin=dict(l=0, r=0, t=0, b=0),
        # height= 561,
        mapbox=go.layout.Mapbox(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=go.layout.mapbox.Center(lat = coord[0], lon = coord[1]),
            pitch=0,
            zoom=10.5,
            style="basic", #"dark", #
        ),
        legend=dict(
            bgcolor="#1f2c56",
            orientation="h",
            font=dict(color="white"),
            x=0,
            y=0,
            yanchor="top",
        ),
    )

    if x_range:
        # get the indices of the values within the specified range
        idx = dff_dist.index[dff_dist['duration'].between(x_range[0],x_range[1], inclusive=True)].tolist()
    else:
        idx = dff_dist.index.tolist()

    data = []
    # choropleth map showing the duration at the block level
    data.append(go.Choroplethmapbox(
        geojson = block_data,
        locations = dff_dist['id_orig'].tolist(),
        z = dff_dist['duration'].tolist(),
        colorscale = pl_deep,
        colorbar = dict(thickness=20, ticklen=3), zmin=0, zmax=60,
        marker_line_width=0, marker_opacity=0.7,
        visible=True,
        text =[mode_dict[mode_select]]*len(dff_dist),
        hovertemplate="%{z:.1f}min %{text} <br>" +
                        "<extra></extra>",
        selectedpoints=idx,
    ))

    data.append(go.Scattermapbox(
        lat=dff_dest["lat"],
        lon=dff_dest["lon"],
        mode="markers",
        marker={"color": [colormap[amenity]]*len(dff_dest), "size": 9},
        name=amenity.replace('_',' '),
        hoverinfo="skip", hovertemplate="",
    ))

    return {"data": data, "layout": layout}


def create_layout(app):
    # Page layouts
    return html.Div(
        [
            html.Div(
                [
                    # City and transport mode selection
                    html.Div(
                        [
                            html.Div(
                                [
                                    # html.H6(
                                    #     [
                                    #         "Pick your city"
                                    #     ],
                                    #     className="subtitle padded",
                                    # ),
                                    dcc.RadioItems(
                                        id="city-select",
                                        options=[
                                            {"label": i, "value": i.lower()}
                                            for i in ['Christchurch','Hamilton']
                                        ],
                                        value='hamilton',
                                        labelStyle={'display': 'inline-block'},
                                    ),
                                ],
                                className=" six columns",
                            ),
                            html.Div(
                                [
                                    # html.H6(
                                    #     [
                                    #         "Pick your transport mode"
                                    #     ],
                                    #     className="subtitle padded",
                                    # ),
                                    dcc.RadioItems(
                                        id="mode-select",
                                        options=[
                                            {"label": i, "value": i.lower()}
                                            for i in ['Walking','Cycling', 'Driving']
                                        ],
                                        value='walking',
                                        labelStyle={'display': 'inline-block'},
                                    ),
                                ],
                                className=" six columns",
                            ),
                        ],
                        className="row ",
                    ),
                    # Row 4
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        [
                                            "Pick your destination"
                                        ],
                                        className="subtitle padded",
                                    ),
                                    html.Div(
                                        [
                                            dcc.Dropdown(
                                                id="amenity-select",
                                                options=[
                                                    {"label": i.upper().replace('_',' '), "value": i}
                                                    for i in amenities
                                                ],
                                                value=amenities[7],
                                            ),
                                        ],
                                        # style={"overflow-x": "auto"},
                                    ),
                                ],
                                className=" twelve columns",
                            )
                        ],
                        className="row ",
                    ),
                    # Row 2
                    html.Div(
                        [
                            html.Div(

                                id="map-container",
                                    children=[
                                        # html.H6("This map shows how long it would take for people to get to their nearest amenity."),
                                        dcc.Graph(
                                            id="map",
                                            figure={
                                                "layout": {
                                                }
                                            },
                                            config={"scrollZoom": True, "displayModeBar": True,
                                                    "modeBarButtonsToRemove":["lasso2d","select2d"],
                                            },
                                        ),
                                    ],
                                className="twelve columns",
                            )
                        ],
                        className="row ",
                    ),
                    # Time and percent people
                    html.Div(
                        [
                            html.Div(
                                [
                                    # html.H6(
                                    #     [
                                    #         "Enter a maximum travel time (minutes)"
                                    #     ],
                                    #     className="subtitle padded",
                                    # ),
                                    dcc.Input(
                                        id="time-select",
                                        type='number',
                                        placeholder="Input travel time (min)",
                                        # labelStyle={'display': 'inline-block'},
                                    ),
                                ],
                                className=" six columns",
                            ),
                            html.Div(
                                [
                                    html.Div(id="output"),
                                ],
                                className=" six columns",
                            ),
                        ],
                        className="row ",
                    ),
                ],
                className="sub_page",
            ),
        ],
        className="page",
    )
