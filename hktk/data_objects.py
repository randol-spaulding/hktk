from hktk.typing import RecordListType, DType, SupportsContains
from hktk.exceptions import MalformedHealthKitDataException
from collections import UserList, defaultdict, OrderedDict
from dataclasses import dataclass, field
from typing import Union, List, Callable, Iterable, Optional, TypeVar, Literal, Hashable
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from datetime import date as dt_date
import importlib
from functools import lru_cache
import numpy as np

record_lists = defaultdict(lambda: None)


@lru_cache(maxsize=1)
def get_record_types():
    return importlib.import_module('hktk.meta').RecordTypes


def infer_record_list_type(hk_type: str):
    record_types = get_record_types()
    return record_types[hk_type]


def register(record_list_type):
    record_lists[record_list_type.__name__] = record_list_type
    return record_list_type


@dataclass
class Record:
    type: str = field()
    creationDate: datetime = field()
    startDate: datetime = field()
    endDate: datetime = field()
    value: Union[str, None] = field(default=None)
    sourceName: str = field(repr=False, default=None)
    sourceVersion: str = field(repr=False, default=None)
    unit: str = field(default=None, repr=False)
    device: str = field(default=None, repr=False)

    @property
    def interval(self) -> timedelta:
        return self.endDate - self.startDate


@register
class RecordList(UserList, List[Record]):

    @property
    def hk_types(self) -> set[str]:
        return set(record.type for record in self)

    def datetime_range(self) -> Union[None, tuple[datetime, datetime]]:
        if len(self) == 0:
            return None
        default_tz = timezone(timedelta(0))
        min_datetime, max_datetime = datetime.max.replace(tzinfo=default_tz), datetime.min.replace(tzinfo=default_tz)
        for record in self:
            min_datetime, max_datetime = min(record.startDate, min_datetime), max(record.endDate, max_datetime)
        return min_datetime, max_datetime

    def __getitem__(self, item: Union[int, slice]):
        if isinstance(item, int):
            return super().__getitem__(item)
        elif isinstance(item, slice):
            if isinstance(item.start, datetime) or isinstance(item.stop, datetime):
                start, stop = item.start, item.stop
                if not (isinstance(start, datetime) and isinstance(stop, datetime)):
                    min_datetime, max_datetime = self.datetime_range()
                    start = start if isinstance(start, datetime) else min_datetime
                    stop = stop if isinstance(stop, datetime) else max_datetime
                def filter_fn(record: Record) -> bool:
                    return start <= record.startDate and record.endDate <= stop
                return self.filter(filter_fn)
            else:
                return super().__getitem__(item)
        else:
            raise KeyError(f'Invalid key "{item}" with type "{type(item)}"')

    def sort_by_date(self, date_type: Literal['startDate', 'endDate', 'creationDate'] = 'startDate'):
        self.sort(key=lambda record: getattr(record, date_type))

    def get_subset_by_date_range(self, start: datetime, end: datetime, already_sorted: bool = False) -> 'RecordList':
        if already_sorted:
            ret = type(self)()
            for record in self:
                if record.startDate < start:
                    continue
                if record.startDate > end:
                    break
                ret.append(record)
            return ret
        return self[start:end]

    def group_by(self: RecordListType, grouping_func: Callable[[Record], Hashable]) -> dict[Hashable, RecordListType]:
        groups = defaultdict(type(self))
        for record in self:
            group = grouping_func(record)
            groups[group].append(record)
        return groups

    def filter(self: RecordListType, func: Callable[[any], bool]) -> RecordListType:
        filtered_list = type(self)()
        for item in self:
            if func(item):
                filtered_list.append(item)
        return filtered_list

    def get_type_subset(self: RecordListType, record_type: Union[str, SupportsContains]) -> RecordListType:
        if isinstance(record_type, str):
            cls_type = infer_record_list_type(record_type).analytic_cls
            return cls_type(self.filter(lambda record: record.type in record_type))
        return self.filter(lambda record: record.type in record_type)

    def split_by_types(self: RecordListType) -> dict[str, RecordListType]:
        ret = {}
        for record in self:
            cls_type = infer_record_list_type(record.type).analytic_cls
            if cls_type is InvalidTypeRecordList:
                continue
            ret.setdefault(record.type, cls_type()).append(record)
        return ret

    def split_by_date(self: RecordListType) -> dict[dt_date, RecordListType]:
        ret = defaultdict(type(self))
        for record in self:
            ret[record.startDate.date()].append(record)
        return ret

    def split_by_value(self: RecordListType) -> dict[Union[str, None], RecordListType]:
        ret = defaultdict(type(self))
        for record in self:
            ret[record.value].append(record)
        return ret

    def get_date_summary(self) -> dict[str, set[dt_date]]:
        date_summary = defaultdict(set)
        for record in self:
            date_summary[record.type].add(record.startDate.date())
        return date_summary

    def get_average_sampling_period(self) -> float:
        if len(self.hk_types) != 1 or len(self) <= 1:
            raise NotImplementedError('Can only analyze sampling rate of singular-type RecordLists with'
                                      'more than one value')
        self.sort_by_date()
        S, prev_t = 0, self[0].startDate
        for record in self[1:]:
            S += (record.startDate - prev_t).total_seconds()
            prev_t = record.startDate
        return S/(len(self)-1)


class AnalyticRecordList(RecordList, ABC):

    def __init__(self, initlist=None):
        super().__init__(initlist)
        if len(self.hk_types) > 1:
            raise ValueError(f'AnalyticRecordList classes and subclasses are for single-type records')

    @property
    def hk_type(self) -> str | None:
        hk_types = self.hk_types
        return list(hk_types)[0] if len(hk_types) > 0 else None

    @property
    def record_type(self):
        return infer_record_list_type(self.hk_type)

    @property
    def hk_simplified_name(self) -> str:
        return infer_record_list_type(self.hk_type).name

    @property
    def unit(self) -> str:
        unit = set(record.unit for record in self)
        if len(unit) == 1:
            return unit.pop()
        elif len(unit) > 1:
            raise MalformedHealthKitDataException(f'Records of type {self.hk_types} has multiple units: {unit}')
        return ''

    def split_by_types(self):
        raise AttributeError('AnalyticRecordList classes and subclasses are for single-type records')

    @abstractmethod
    def get_features(self) -> list[float]:
        pass

    @abstractmethod
    def get_feature_summary(self) -> dict[str, float]:
        pass


@dataclass
class StatisticSummary:
    mean: float = field(default=None)
    variance: float = field(default=None)
    min: Union[int, float] = field(default=None)
    max: Union[int, float] = field(default=None)
    unit: str = field(default=None)

    def to_vector(self) -> list[float]:
        return [self.mean, self.std, self.min, self.max]

    @property
    def std(self) -> float:
        return self.variance ** 0.5 if self.variance is not None else None

    def to_dict(self) -> dict[str, float]:
        ret = {'mean': self.mean, 'std': self.std, 'min': self.min, 'max': self.max}
        return {f'{k}_{self.unit}': v for k, v in ret.items()}


@register
class ArrayTypeRecordList(AnalyticRecordList):

    def get_array(self, dtype: DType = float) -> tuple[list[datetime], list[DType]]:
        times, values = [], []
        for record in self:
            times.append(record.startDate)
            values.append(dtype(record.value))
        return times, values

    def get_statistics(self, dtype: DType = float) -> StatisticSummary:
        num_records = len(self)
        if num_records == 0:
            return StatisticSummary()
        elif num_records == 1:
            value = dtype(self[0].value)
            return StatisticSummary(mean=value, variance=None, min=value, max=value, unit=self.unit)
        self.sort_by_date()
        prev_time = self[0].startDate
        vals, dts = [[dtype(self[0].value)]], []
        min_value, max_value = float('inf'), -float('inf')
        for record_num, record in enumerate(self[1:]):
            time, value = record.startDate, dtype(record.value)
            min_value, max_value = min(min_value, value), max(max_value, value)
            if time == prev_time:
                vals[-1].append(value)
                continue
            vals.append([value])
            dt = (time - prev_time).total_seconds()
            dts.append(dt)
            prev_time = time
        if len(dts) == 0:  # edge case where all samples happen simultaneously
            mean = float(np.mean(vals))
            variance = float(np.var(vals))
            return StatisticSummary(mean=mean, variance=variance, min=min_value, max=max_value, unit=self.unit)
        vals = [sum(time_vals)/len(time_vals) for time_vals in vals]
        S, S2, T = 0, 0, 0
        for i in range(len(dts)):
            T += dts[i]
            S += dts[i] * (vals[i+1] + vals[i])/2
            S2 = dts[i] * (vals[i+1]**2 + vals[i]**2)/2
        mean = S / T
        variance = S2 / T - mean ** 2
        return StatisticSummary(mean=mean, variance=variance, min=min_value, max=max_value, unit=self.unit)

    def get_features(self) -> list[float]:
        return self.get_statistics().to_vector()

    def get_feature_summary(self) -> dict[str, float]:
        return self.get_statistics().to_dict()


@register
class CategoricalTypeRecordList(AnalyticRecordList):

    categories: set

    def __init__(self, initlist=None, categories: Optional[Iterable] = None):
        super().__init__(initlist)
        categories = set(record.value for record in self) if categories is None else set(categories)
        self.categories = set(sorted(categories))

    def get_counts(self) -> dict[str, int]:
        count = defaultdict(int)
        for record in self:
            count[record.value] += record.interval.total_seconds()
        return {category: count.get(category, 0) for category in self.categories}

    def get_features(self) -> list[float]:
        return list(self.get_counts().values())

    def get_feature_summary(self) -> dict[str, float]:
        return self.get_counts()


@register
class SleepStageRecordList(CategoricalTypeRecordList):

    sleep_stage_mapping: dict[str, int] = {'HKCategoryValueSleepAnalysisInBed': -1,
                                           'HKCategoryValueSleepAnalysisAwake': 0,
                                           'HKCategoryValueSleepAnalysisAsleepREM': 1,
                                           'HKCategoryValueSleepAnalysisAsleepCore': 2,
                                           'HKCategoryValueSleepAnalysisAsleepDeep': 3}

    sleep_stage_name_mp: dict[str, str] = {'HKCategoryValueSleepAnalysisInBed': 'InBed',
                                           'HKCategoryValueSleepAnalysisAwake': 'Awake',
                                           'HKCategoryValueSleepAnalysisAsleepREM': 'REM',
                                           'HKCategoryValueSleepAnalysisAsleepCore': 'Core',
                                           'HKCategoryValueSleepAnalysisAsleepDeep': 'Deep'}

    def __init__(self, initlist=None):
        super().__init__(initlist=initlist, categories=self.sleep_stage_mapping.keys())

    def parse_sleep_blocks(self) -> dict[int, tuple[datetime, datetime, list[Record]]]:
        blocks = {}
        max_block_id = 0
        for record in self:
            if self.sleep_stage_mapping[record.value] == -1:
                continue
            start, end = record.startDate, record.endDate
            is_in_block = False
            for block_id, (int_start, int_end, stage_arr) in blocks.items():
                if end == int_start or start == int_end:
                    if end == int_start:
                        blocks[block_id] = (start, int_end, [record] + stage_arr)
                    else:
                        blocks[block_id] = (int_start, end, stage_arr + [record])
                    is_in_block = True
                    break
            if not is_in_block:
                blocks[max_block_id] = (start, end, [record])
                max_block_id += 1
        return blocks

    def split_by_sleep_blocks(self) -> list['SleepStageRecordList']:
        ret = []
        for block_id, (int_start, int_end, stage_arr) in self.parse_sleep_blocks().items():
            ret.append(SleepStageRecordList(stage_arr))
        return ret

    def get_features(self) -> list[float]:
        start, end = self.datetime_range()
        duration_in_hours = (end - start).total_seconds() / 3600
        return list(self.get_counts().values()) + [duration_in_hours]

    def get_feature_summary(self) -> dict[str, float]:
        start, end = self.datetime_range()
        duration = (end - start).total_seconds()
        summary = {}
        for key, value in self.get_counts().items():
            k = self.sleep_stage_name_mp[key]
            summary[f'{k}_duration'] = value / 3600
            summary[f'{k}_percent'] = value / duration
        summary['duration'] = duration / 3600
        return summary


@register
class EventTypeRecordList(AnalyticRecordList):

    latest_date: dt_date

    def __init__(self, initlist=None, latest_date: dt_date = None):
        super().__init__(initlist)
        self.latest_date = datetime.now().date() if latest_date is None else latest_date

    def split_by_date(self: RecordListType) -> dict[dt_date, RecordListType]:
        self.sort_by_date()
        ret = {}
        date_split_to_fill = super().split_by_date()
        for ref_date, records in date_split_to_fill.items():
            ret[ref_date] = records
            date = ref_date + timedelta(days=1)
            while date not in date_split_to_fill and date <= self.latest_date:
                ret[date] = EventTypeRecordList()
                date += timedelta(days=1)
        return ret

    def get_features(self) -> list[float]:
        total_time = sum((record.interval for record in self), start=timedelta(0))
        total_time = total_time.total_seconds()/len(self) if len(self) > 0 else 0
        return [total_time, len(self)]

    def get_feature_summary(self) -> dict[str, float]:
        total_time, num_events = self.get_features()
        return {'total_seconds': total_time, 'num_events': num_events}


@register
class CumulativeTypeRecordList(AnalyticRecordList):

    def accumulate(self, dtype: DType = float) -> DType:
        return sum(dtype(record.value) for record in self)

    def get_features(self) -> list[float]:
        return [self.accumulate()]

    def get_feature_summary(self) -> dict[str, float]:
        return {self.unit: self.get_features()[0]}


@register
class CaffeineIntakeRecordList(CumulativeTypeRecordList):

    caffeine_half_life: float = 4.0

    def get_level_at_midnight(self):
        level = 0.0
        _, end = self.datetime_range()
        midnight = datetime.combine((end + timedelta(days=1)).date(), datetime.min.time())
        midnight = midnight.replace(tzinfo=end.tzinfo)
        for record in self:
            hours_to_midnight = (midnight - record.startDate).total_seconds() / 3600
            level += float(record.value) * 2 ** (-hours_to_midnight / self.caffeine_half_life)
        return level

    def get_features(self) -> list[float]:
        return [self.accumulate(), self.get_level_at_midnight()]

    def get_feature_summary(self) -> dict[str, float]:
        return super().get_feature_summary() | {f'{self.unit}_at_midnight': self.get_level_at_midnight()}


class _SummaryTypeRecordList(AnalyticRecordList, ABC):

    latest_date: dt_date

    def __init__(self, initlist=None, latest_date: dt_date = None):
        super().__init__(initlist)
        self.latest_date = datetime.now().date() if latest_date is None else latest_date

    def split_by_date(self: RecordListType) -> dict[dt_date, RecordListType]:
        self.sort_by_date()
        ret = {}
        date_split_to_fill = super().split_by_date()
        for ref_date, records in date_split_to_fill.items():
            ret[ref_date] = records
            date = ref_date + timedelta(days=1)
            while date not in date_split_to_fill and date <= self.latest_date:
                ret[date] = records
                date += timedelta(days=1)
        return ret

    @abstractmethod
    def get_features(self) -> list[float]:
        pass


@register
class SummaryArrayTypeRecordList(ArrayTypeRecordList, _SummaryTypeRecordList):
    pass


@register
class SummaryCategoricalTypeRecordList(CategoricalTypeRecordList, _SummaryTypeRecordList):
    pass


@register
class SummaryCumulativeTypeRecordList(CumulativeTypeRecordList, _SummaryTypeRecordList):
    pass


@register
class InvalidTypeRecordList(AnalyticRecordList):

    def get_features(self) -> list[float]:
        raise NotImplementedError('Attempted to get features of InvalidRecordType')
