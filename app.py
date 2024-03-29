# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd

import numpy as np
from urllib.request import urlopen
import json
import geopandas as gpd
import datetime

from pages import (
    resilience,
)

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}],
    url_base_pathname='/proximity-conversation/',
)
server = app.server

app.config.suppress_callback_exceptions = True

app.title = 'X-minute city'

# Describe the layout/ UI of the app
app.layout = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-content")]
)

# Update page
@app.callback(Output("page-content", "children"),
                [Input("url", "pathname")])
def display_page(pathname):
        return resilience.create_layout(app)


#####
# resilience
#####
# mapbox token
mapbox_access_token = open(".mapbox_token").read()

# Load data
df_dist = pd.read_csv('./data/duration.csv',dtype={"gid": str})
df_dist['duration'] = df_dist['duration']/60
df_dist['duration'] = df_dist['duration'].replace(np.inf, 999)

destinations = pd.read_csv('./data/destinations.csv')

mode_dict = {'walking':'walk','cycling':'bike','driving':'drive'}

# Update access map
@app.callback(
    Output("map", "figure"),
    [
        Input("amenity-select", "value"),
        Input("mode-select", "value"),
        Input("city-select", "value"),
        Input("time-select", "value"),
    ],
)
def update_map(
    amenity_select, mode_select, city_select, max_time
):
    x_range = None
    # subset the desination df
    dff_dest = destinations[(destinations.dest_type==amenity_select) & (destinations.city==city_select)]
    dff_dist = df_dist[(df_dist['dest_type']==amenity_select) & (df_dist['mode']==mode_select) & (df_dist.city==city_select)]
    # Find which one has been triggered
    ctx = dash.callback_context

    prop_id = ""
    prop_type = ""
    if ctx.triggered:
        splitted = ctx.triggered[0]["prop_id"].split(".")
        prop_id = splitted[0]
        prop_type = splitted[1]

    if prop_id == 'time-select' and prop_type == "value":
        if max_time:
            x_range = [0, max_time]

    return resilience.generate_map(amenity_select, dff_dist, dff_dest, mode_select, city_select, x_range=x_range)


@app.callback(
    Output("output", "children"),
    [
        Input("amenity-select", "value"),
        Input("mode-select", "value"),
        Input("city-select", "value"),
        Input("time-select", "value"),
        ],
)
def update_output(
    amenity_select, mode_select, city_select, max_time
):
    dff_dist = df_dist[(df_dist['dest_type']==amenity_select) & (df_dist['mode']==mode_select) & (df_dist.city==city_select)]
    total_pop = dff_dist['population'].sum()
    pop_within = dff_dist.loc[dff_dist.duration <= max_time, 'population'].sum()
    percentage = pop_within/total_pop*100
    if max_time:
        if amenity_select=='downtown':
            return '{:.1f} % of {} residents are within a {}-minute {} of {}'.format(percentage, city_select.capitalize(), max_time, mode_dict[mode_select], amenity_select)
        else:
            return '{:.1f} % of {} residents are within a {}-minute {} of a {}'.format(percentage, city_select.capitalize(), max_time, mode_dict[mode_select], amenity_select.replace('_',' '))
    else:
        return ''


if __name__ == "__main__":
    # app.run_server(debug=True,port=9008)
    app.run_server(port=9008)
