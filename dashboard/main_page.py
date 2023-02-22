from hktk.filereader import XMLStringLoader, XMLLoader
from dashboard.report_body import get_report_body
from dash import Dash, html, dcc, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
import uuid
import base64
import os


def get_layout(app: Dash, cache_dir: str) -> Component:
    session_id = uuid.uuid4()
    default_data_store = {'session_id': session_id.hex, 'cache_dir': cache_dir, 'hk_types': None}
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
                  State('session-store', 'data'),
                  State('selector-div', 'style'))
    def update_settings(contents, data_store, selector_div_style):
        if contents is not None:
            content_type, content_string = contents.split(',')
            contents = base64.b64decode(content_string)
            loader = XMLStringLoader(contents)

            filename = os.path.join(data_store.get('cache_dir'), data_store.get('session_id') + '.xml')
            loader.save(filename)

            data_store['hk_types'] = list(loader.get_record_type_summary())
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
        filename = os.path.join(data_store.get('cache_dir'), data_store.get('session_id') + '.xml')
        loader = XMLLoader(filename)
        records = loader.get_all_records_by_type(hk_types)

        layout = get_report_body(app, records)

        return layout
