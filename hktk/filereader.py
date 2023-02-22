from hktk.fileutil import is_xml, convert_to_pathlib
from hktk.data_objects import Record, RecordList
from lxml import etree as ET
from typing import (Union, Optional, Iterator)
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class XMLRecord(Record):

    metadata: Optional[list[ET._Element]] = field(default=None, repr=False)

    @classmethod
    def from_element(cls, record_element: ET._Element):
        record_info = {k: v for k, v in record_element.attrib.items()}  # Convert to dict
        record_info['creationDate'] = XMLLoader.datetime_from_hk_string(record_info.get('creationDate'))
        record_info['startDate'] = XMLLoader.datetime_from_hk_string(record_info.get('startDate'))
        record_info['endDate'] = XMLLoader.datetime_from_hk_string(record_info.get('endDate'))
        record_info['metadata'] = record_element.findall('./')
        return cls(**record_info)


class XMLLoader:

    files: list[Path]

    def __init__(self, fp: str):
        fp = convert_to_pathlib(fp)
        self.files = []
        if fp.is_dir():
            self.files = [file for file in fp.iterdir() if is_xml(file) and file.exists()]
        else:
            self.files = [fp]

    def get_tag_summary(self) -> Union[set[str], dict[Path, set[str]]]:
        tags = dict()
        for file, elements in self.get_iterator_by_tag('./'):
            tags[file] = set()
            for element in elements:
                tags[file].add(element.tag)
        if len(self.files) == 1:
            return tags[self.files[0]]
        return tags

    def get_tag_type_summary(self, tag_name: str) -> Union[set[str], dict[Path, set[str]]]:
        tag_types = dict()
        for file, records in self.get_iterator_by_tag(tag_name):
            tag_types[file] = set()
            for record in records:
                tag_types[file].add(record.get('type'))
        if len(self.files) == 1:
            return tag_types[self.files[0]]
        return tag_types

    def get_record_type_summary(self) -> Union[set[str], dict[Path, set[str]]]:
        return self.get_tag_type_summary(tag_name='Record')

    def get_iterator_by_tag(self, tag: str) -> Iterator[tuple[Path, Iterator]]:
        for file in self.files:
            etree = ET.parse(file)
            yield file, etree.iterfind(tag)

    def iter_all_records(self) -> Iterator[tuple[Path, XMLRecord]]:
        for file, all_records in self.get_iterator_by_tag('Record'):
            for record in all_records:
                yield file, XMLRecord.from_element(record)

    def get_all_records(self) -> RecordList:
        return RecordList(record for file, record in self.iter_all_records())

    def get_all_records_by_type(self, record_type: Union[str, list[str]]) -> Union[RecordList, dict[Path, RecordList]]:
        type_records = defaultdict(RecordList)
        record_type = [record_type] if not isinstance(record_type, list) else record_type
        for file, all_records in self.get_iterator_by_tag('Record'):
            records = filter(lambda rec: rec.get('type') in record_type, all_records)
            for record in records:
                type_records[file].append(XMLRecord.from_element(record))
        if len(self.files) == 1:
            return type_records[self.files[0]]
        return type_records

    @staticmethod
    def datetime_from_hk_string(datetime_string: str) -> datetime:
        return datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S %z')
