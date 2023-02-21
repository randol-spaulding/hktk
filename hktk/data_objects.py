from collections import UserList
from dataclasses import dataclass, field
from typing import Union, List, Callable
from datetime import datetime


@dataclass
class Record:
    type: str = field()
    creationDate: datetime = field()
    startDate: datetime = field()
    endDate: datetime = field()
    value: Union[str, None] = field()
    sourceName: str = field(repr=False)
    sourceVersion: str = field(repr=False)
    unit: str = field(default=None, repr=False)
    device: str = field(default=None, repr=False)


class RecordList(UserList, List[Record]):

    def __getitem__(self, item: Union[int, slice]):
        if isinstance(item, int):
            return self[item]
        elif isinstance(item, slice):
            if isinstance(item.start, datetime) and isinstance(item.stop, datetime):
                def filter_fn(record: Record):
                    return any(item.start <= dt <= item.stop for dt in [record.startDate, record.endDate, record.creationDate])
                return self.filter(filter_fn)
            else:
                return self[item]
        else:
            raise KeyError(f'Invalid key "{item}" with type "{type(item)}"')

    def filter(self, func: Callable[[any], bool]) -> 'RecordList':
        filtered_list = RecordList()
        for item in self:
            if func(item):
                filtered_list.append(item)
        return filtered_list
