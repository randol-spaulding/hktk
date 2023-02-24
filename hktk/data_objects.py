from hktk.typing import RecordListType, DType, SupportsContains
from hktk.exceptions import MalformedHealthKitDataException
from collections import UserList, defaultdict, OrderedDict
from dataclasses import dataclass, field
from typing import Union, List, Callable, Iterable, Optional, TypeVar, Literal, Hashable
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from datetime import date as dt_date


DType = TypeVar('DType')
RecordListType = TypeVar('RecordListType')

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


class ArrayTypeRecordList(RecordList):

    def get_array(self, dtype: DType = float) -> tuple[list[datetime], list[DType]]:
        times, values = [], []
        for record in self:
            times.append(record.startDate)
            values.append(dtype(record.value))
        return times, values

    def get_statistics(self, dtype: DType = float) -> tuple[float, float]:
        self.sort_by_date()
        prev_time, prev_value = None, None
        S, S2, T = 0, 0, 0
        for record in self:
            time, value = record.startDate, dtype(record.value)
            if prev_time is None:
                prev_time, prev_value = time, value
                continue
            dt = (time - prev_time).total_seconds()
            ds = (value + prev_value)/2
            ds2 = (value ** 2 + prev_value ** 2) / 2
            T += dt
            S += dt * ds
            S2 += dt * ds2
        mean = S / T
        variance = S2 / T - mean ** 2
        return mean, variance


class SleepStageRecordList(RecordList):
    pass


class FlagTypeRecordList:
    pass


class SummaryTypeRecordList:
    pass
