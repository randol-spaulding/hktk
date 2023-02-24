from typing import Protocol, TypeVar


DType = TypeVar('DType')
RecordListType = TypeVar('RecordListType')


class SupportsContains(Protocol):

    def __contains__(self, item) -> bool:
        pass
