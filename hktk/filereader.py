from hktk.fileutil import is_xml, convert_to_pathlib
from lxml import etree as ET
from typing import (Union, Optional, Iterator)
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class XMLRecord:
    type: str = field()
    creationDate: str = field()
    startDate: str = field()
    endDate: str = field()
    sourceName: str = field(repr=False)
    sourceVersion: str = field(repr=False)
    value: str = field(default=None)
    unit: str = field(default=None, repr=False)
    device: str = field(default=None, repr=False)
    metadata: Optional[list[ET._Element]] = field(default=None, repr=False)

    @property
    def creation_datetime(self) -> datetime:
        return XMLLoader.datetime_from_hk_string(self.creationDate)

    @property
    def start_datetime(self) -> datetime:
        return XMLLoader.datetime_from_hk_string(self.startDate)

    @property
    def end_datetime(self) -> datetime:
        return XMLLoader.datetime_from_hk_string(self.endDate)


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
                yield file, XMLRecord(**record.attrib, metadata=record.findall('./'))

    def get_all_records_by_type(self, record_type: str) -> Union[list[XMLRecord], dict[Path, list[XMLRecord]]]:
        type_records = dict()
        for file, all_records in self.get_iterator_by_tag('Record'):
            records = filter(lambda record: record.get('type') == record_type, all_records)
            type_records[file] = [XMLRecord(**record.attrib, metadata=record.findall('./')) for record in records]
        if len(self.files) == 1:
            return type_records[self.files[0]]
        return type_records

    @staticmethod
    def datetime_from_hk_string(datetime_string: str) -> datetime:
        return datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S %z')
