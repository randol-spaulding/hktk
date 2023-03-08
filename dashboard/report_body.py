from hktk.data_objects import RecordList
from dash import Dash, html
from dash.development.base_component import Component


def get_report_body(app: Dash, records: RecordList, sleep_feature: str) -> Component:
    return html.Div(f'Report for {sleep_feature} goes here')
