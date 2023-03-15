from hktk.filereader import XMLStringLoader, XMLLoader
from dashboard.report_body import get_report_body
from dash import Dash, html, dcc, Input, Output, State, dash_table
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from plotly import graph_objects as go
import uuid
import base64
import os
from datetime import datetime, date as dt_date
import pytz
import json
from sklearn.linear_model import LinearRegression
import numpy as np


sleep_type_options = [{'label': 'Total sleep duration', 'value': 'duration'},
                      {'label': 'REM duration', 'value': 'REM_duration'},
                      {'label': 'REM percentage', 'value': 'REM_percent'},
                      {'label': 'Core duration', 'value': 'Core_duration'},
                      {'label': 'Core percentage', 'value': 'Core_percent'},
                      {'label': 'Deep duration', 'value': 'Deep_duration'},
                      {'label': 'Deep percentage', 'value': 'Deep_percent'},
                      {'label': 'Wake duration', 'value': 'Awake_duration'},
                      {'label': 'Wake percentage', 'value': 'Awake_percent'}]

def get_layout(app: Dash, cache_dir: str) -> Component:
    # session_id = uuid.uuid4()
    print(cache_dir)
    default_data_store = {'session_id': 'export', 'cache_dir': cache_dir, 'hk_types': None}

    layout = html.Div(id='content', children=[
        dcc.Store(id='session-store', storage_type='session', data=default_data_store),
        dcc.Store(id='feature-store', storage_type='session', data=None),
        html.H1('Sleep Analysis Dashboard'),
        dcc.Upload(
            id='upload-file',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select File')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=False
        ),
        dcc.Loading([
            html.Div(id='selector-div', style={'display': 'none'}, children=[
                dcc.Dropdown(id='sleep-type-dropdown', options=sleep_type_options, multi=False),
                dcc.DatePickerRange(id='date-picker'),
                html.Button(id='submit-button', children='Submit')
            ])
        ],),
        dcc.Loading([
            html.Div(id='report-output', children=[
                html.Div(id='table-div', children=[
                    dash_table.DataTable(id='selector-table', data=None,
                                         columns=[{'name': 'Field', 'id': 'field'}, {'name': 'Score', 'id': 'score'}],
                                         style_table={'overflowX': 'auto'})
                ], style={'display': 'inline-block', 'width': '50%', 'float': 'left'}),
                html.Div(id='graph-div', children=[
                    dcc.Graph(id='graph')
                ], style={'display': 'inline-block', 'width': '50%', 'float': 'right'})
            ], style={'display': 'none'})
        ])
    ])
    register_callbacks(app)
    return layout


def register_callbacks(app: Dash):
    @app.callback(Output('selector-div', 'style'),
                  Output('session-store', 'data'),
                  Input('upload-file', 'contents'),
                  State('session-store', 'data'),
                  State('selector-div', 'style'))
    def update_settings(contents, data_store, selector_div_style):
        if contents is not None:
            # content_type, content_string = contents.split(',')
            # contents = base64.b64decode(content_string)

            filename = os.path.join(data_store.get('cache_dir'), data_store.get('session_id') + '.xml')
            print(filename)
            loader = XMLLoader(filename)
            # loader.save(filename)

            data_store['hk_types'] = list(loader.get_record_type_summary())
            selector_div_style['display'] = 'block'
            return selector_div_style, data_store
        raise PreventUpdate()

    @app.callback(
        Output('selector-table', 'data'),
        Output('feature-store', 'data'),
        Output('report-output', 'style'),
        Input('submit-button', 'n_clicks'),
        State('session-store', 'data'),
        State('sleep-type-dropdown', 'value'),
        State('date-picker', 'start_date'),
        State('date-picker', 'end_date')
    )
    def get_report(n_clicks, data_store, sleep_feature, start_date, end_date) -> tuple[list[dict], dict, dict]:
        if n_clicks is None:
            raise PreventUpdate()

        cache_dir = data_store.get('cache_dir')
        if os.path.exists(os.path.join(cache_dir, sleep_feature + '.json')):
            with open(os.path.join(cache_dir, sleep_feature + '.json'), 'r') as file:
                ret = json.load(file)
            table_data = ret.pop('table_data')
            return table_data, ret, {'display': 'block'}

        filename = os.path.join(cache_dir, data_store.get('session_id') + '.xml')
        loader = XMLLoader(filename)
        start_date = start_date if start_date is not None else datetime(2022, 10, 31, 12, 0, 0).isoformat()
        end_date = end_date if end_date is not None else datetime.now().isoformat()

        localizer = pytz.timezone('America/Los_Angeles').localize
        start_date, end_date = datetime.fromisoformat(start_date), datetime.fromisoformat(end_date)
        start_date, end_date = localizer(start_date), localizer(end_date)
        records = loader.get_all_records_in_time_range(start_date, end_date)

        table_data, x, y, dates = get_report_body(records, sleep_feature)

        with open(os.path.join(cache_dir, sleep_feature + '.json'), 'w') as file:
            json.dump({'table_data': table_data, 'x': x, 'y': y, 'dates': dates}, file)

        return table_data, {'x': x, 'y': y, 'dates': dates}, {'display': 'block'}

    @app.callback(
        Output('graph', 'figure'),
        State('feature-store', 'data'),
        State('selector-table', 'data'),
        State('sleep-type-dropdown', 'value'),
        Input('selector-table', 'active_cell')
    )
    def update_graph(feature_data, table_data, dd_state, active_cell):
        if active_cell is None:
            raise PreventUpdate()
        fx, fy, fdates = feature_data['x'], feature_data['y'], feature_data.get('dates', [])
        feature_name = table_data[active_cell['row']]['field']
        fy = fy[feature_name]
        x, y, dates = [], [], []
        for ind, value in fy:
            x.append(fx[ind])
            dates.append(fdates[ind])
            y.append(value)
        graph = go.Scatter(x=y, y=x, mode='markers', name='Data',
                           hovertext=dates)

        m, s = np.mean(y), np.std(y)
        xn, yn = [], []
        for xv, yv in zip(x, y):
            if abs((yv-m)/s) < 3:
                xn.append(xv)
                yn.append(yv)
        lr = LinearRegression()
        lr.fit(np.expand_dims(yn, -1), np.expand_dims(xn, -1))
        m0, m1 = min(yn), max(yn)
        y0, y1 = lr.predict(np.expand_dims([m0], -1)), lr.predict(np.expand_dims([m1], -1))
        y0, y1 = np.squeeze(y0), np.squeeze(y1)

        fig = go.Figure(data=graph)
        fig.add_trace(go.Scatter(x=[m0, m1], y=[y0, y1], mode='lines', name='Trendline'))

        fig.update_layout(xaxis_title=' '.join(feature_name.split('_')), yaxis_title=dd_state)
        return fig
