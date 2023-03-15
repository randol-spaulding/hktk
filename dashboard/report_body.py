from hktk.data_objects import RecordList, SleepStageRecordList
from dash import Dash, html, dash_table, Input, Output, State, dcc
from dash.exceptions import PreventUpdate
from dash.development.base_component import Component
from datetime import datetime, timedelta, date as dt_date
from collections import defaultdict
from sklearn.linear_model import LinearRegression
import numpy as np
import tqdm


def get_report_body(records: RecordList, sleep_feature: str) \
        -> tuple[list[dict], list[float], dict[str, list[float]], list[str]]:

    sleep_records = records.get_type_subset('HKCategoryTypeIdentifierSleepAnalysis')
    sleep_blocks: list[SleepStageRecordList] = sleep_records.split_by_sleep_blocks()

    x_features, y_features = [], defaultdict(list)

    all_hk_types = list(records.hk_types)
    next_records = records.get_type_subset(all_hk_types)
    next_records.sort_by_date()
    prev_end = None
    dates = []
    print('Collecting data')
    for i in tqdm.trange(len(sleep_blocks)):
        sleep_block = sleep_blocks[i]
        start, end = sleep_block.datetime_range()
        if prev_end is None:
            td = timedelta(hours=18)
        else:
            td = timedelta(hours=min(24, (start-prev_end).total_seconds()/3600))
        next_records = next_records[start - td:]
        before_records = next_records.get_subset_by_date_range(start - td, start, True)
        # after_records = records[end:end + timedelta(hours=18)]

        feature_summary = sleep_block.get_feature_summary()
        x_features.append(float(feature_summary[sleep_feature]))
        dates.append(start.date())

        for hk_type, record_list in before_records.split_by_types().items():
            name = record_list.hk_simplified_name
            for feature_name, feature_value in record_list.get_feature_summary().items():
                if feature_value is None:
                    continue
                try:
                    value = float(feature_value)
                except:
                    continue
                y_features[f'{name}_{feature_name}'].append([i, value])
        prev_end = end

    scores = {}
    print('Scoring all data')
    for feature_id, feature_list in y_features.items():
        x, y = [], []
        for index, value in feature_list:
            x.append(x_features[index])
            y.append(value)

        if len(x) < 7:
            print(f'Skipping {feature_id}')
            continue
        x, y = np.array(x), np.array(y)
        x, y = (x - np.mean(x))/np.std(x), (y - np.mean(y))/np.std(y)
        xn, yn, unique = [], [], set()
        for xv, yv in zip(x, y):
            if abs(yv) < 3:
                xn.append(xv)
                yn.append(yv)
                unique.add(yv)
        if len(unique) <= 2:
            scores[feature_id] = 0
            continue
        xn, yn = np.expand_dims(xn, -1), np.expand_dims(yn, -1)

        lr = LinearRegression()
        try:
            lr.fit(yn, xn)
        except ValueError:
            print(f'Error with {feature_id}')
            continue
        r_squared = lr.score(yn, xn)
        scores[feature_id] = float(np.squeeze(
            1/np.sqrt(2) * np.sqrt(
                r_squared ** 2 + (2*np.arctan(lr.coef_)/np.pi) ** 2
            )
        ))

    table_data = []
    for field_name in sorted(scores, key=lambda k: scores[k], reverse=True):
        table_data.append({'field': field_name, 'score': scores[field_name]})
    dates = [date.isoformat() for date in dates]
    return table_data, x_features, y_features, dates
