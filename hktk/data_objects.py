from hktk.typing import RecordListType, DType, SupportsContains
from hktk.exceptions import MalformedHealthKitDataException
from collections import UserList, defaultdict, OrderedDict
from dataclasses import dataclass, field
from typing import Union, List, Callable, Iterable, Optional, TypeVar, Literal, Hashable
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from datetime import date as dt_date

record_lists = defaultdict(lambda: None)


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
    def hk_types(self):
        return set(record.type for record in self)

    @property
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
            if isinstance(item.start, datetime) and isinstance(item.stop, datetime):
                def filter_fn(record: Record) -> bool:
                    return any(item.start <= dt <= item.stop for dt in [record.startDate, record.endDate, record.creationDate])
                return self.filter(filter_fn)
            else:
                return super().__getitem__(item)
        else:
            raise KeyError(f'Invalid key "{item}" with type "{type(item)}"')

    def sort_by_date(self, date_type: Literal['startDate', 'endDate', 'creationDate'] = 'startDate'):
        self.sort(key=lambda record: getattr(record, date_type))

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

    def get_type_subset(self: RecordListType, record_types: Union[str, SupportsContains]) -> RecordListType:
        if isinstance(record_types, str):
            record_types = [record_types]
        return self.filter(lambda record: record.type in record_types)

    def split_by_types(self: RecordListType) -> dict[str, RecordListType]:
        ret = defaultdict(type(self))
        for record in self:
            ret[record.type].append(record)
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
    def unit(self) -> str:
        unit = set(record.unit for record in self)
        if len(unit) == 1:
            return unit.pop()
        elif len(unit) > 1:
            raise MalformedHealthKitDataException(f'Records of type {self.hk_types} has multiple units: {unit}')
        return ''

    @abstractmethod
    def get_features(self) -> list[float]:
        pass


@dataclass
class StatisticSummary:
    mean: float = field(default=None)
    variance: float = field(default=None)
    min: Union[int, float] = field(default=None)
    max: Union[int, float] = field(default=None)
    unit: str = field(default=None)

    def to_vector(self) -> list[float]:
        return [self.mean, self.variance, self.min, self.max]

    @property
    def std(self) -> float:
        return self.variance ** 0.5 if self.variance is not None else None



class ArrayTypeRecordList(RecordList):

    def get_array(self, dtype: DType = float) -> tuple[list[datetime], list[DType]]:
        times, values = [], []
        for record in self:
            times.append(record.startDate)
            values.append(dtype(record.value))
        return times, values

    def get_statistics(self, dtype: DType = float) -> StatisticSummary:
        if len(self) == 0:
            return StatisticSummary()
        elif len(self) == 1:
            value = dtype(self[0].value)
            return StatisticSummary(mean=value, variance=0, min=value, max=value, unit=self.unit)
        self.sort_by_date()
        prev_time, prev_value = None, None
        S, S2, T = 0, 0, 0
        min_value, max_value = float('inf'), -float('inf')
        for record in self:
            time, value = record.startDate, dtype(record.value)
            min_value, max_value = min(min_value, value), max(max_value, value)
            if prev_time is None:
                prev_time, prev_value = time, value
                continue
            dt = (time - prev_time).total_seconds()
            ds = (value + prev_value)/2
            ds2 = (value ** 2 + prev_value ** 2) / 2
            T += dt
            S += dt * ds
            S2 += dt * ds2
        T = len(self) if T == 0 else T  # in weird case where all samples happen simultaneously
        mean = S / T
        variance = S2 / T - mean ** 2
        return StatisticSummary(mean=mean, variance=variance, min=min_value, max=max_value, unit=self.unit)


class SleepStageRecordList(RecordList):
    pass


class FlagTypeRecordList:
    pass


class SummaryTypeRecordList:
    pass
