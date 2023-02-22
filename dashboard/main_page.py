from hktk.filereader import XMLStringLoader
from dashboard.report_body import get_report_body
from dash import Dash, html, dcc, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
import uuid
import base64
from lxml import etree as ET


def get_layout(app: Dash) -> Component:
    session_id = uuid.uuid4()
    default_data_store = {'session_id': session_id.hex, 'content': None, 'hk_types': None}
    layout = html.Div(id='content', children=[
        dcc.Store(id='session-store', storage_type='session', data=default_data_store),
        html.H1('HealthKit ToolKit Dashboard'),
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
                dcc.Dropdown(id='hk-type-dropdown', multi=True),
                dcc.DatePickerRange(id='date-picker'),
                html.Button(id='submit-button', children='Submit')
            ])
        ]),
        dcc.Loading([
            html.Div(id='report-output')
        ])
    ])
    register_callbacks(app)
    return layout


def register_callbacks(app: Dash):
    @app.callback(Output('hk-type-dropdown', 'options'),
                  Output('selector-div', 'style'),
                  Output('session-store', 'data'),
                  Input('upload-file', 'contents'),
                  State('upload-file', 'filename'),
                  State('upload-file', 'last_modified'),
                  State('session-store', 'data'),
                  State('selector-div', 'style'))
    def update_settings(contents, filename, last_modified, data_store, selector_div_style):
        if contents is not None:
            content_type, content_string = contents.split(',')
            contents = base64.b64decode(content_string)
            loader = XMLStringLoader(contents)
            records = loader.get_all_records()

            data_store['content'] = content_string
            data_store['hk_types'] = list(records.hk_types)
            selector_div_style['display'] = 'block'
            return data_store['hk_types'], selector_div_style, data_store
        raise PreventUpdate()

    @app.callback(
        Output('report-output', 'children'),
        Input('submit-button', 'n_clicks'),
        State('session-store', 'data'),
        State('hk-type-dropdown', 'value'),
        State('date-picker', 'start_date'),
        State('date-picker', 'end_date')
    )
    def get_report(n_clicks, data_store, hk_types, start_date, end_date) -> Component:
        if n_clicks is None:
            raise PreventUpdate()
        contents = data_store['content']
        contents = base64.b64decode(contents)

        loader = XMLStringLoader(contents)
        records = loader.get_all_records_by_type(hk_types)

        layout = get_report_body(app, records)

        return layout
