from hktk.data_objects import RecordList
from dash import Dash, html
from dash.development.base_component import Component


def get_report_body(app: Dash, records: RecordList) -> Component:
    return html.Div('Report goes here')
