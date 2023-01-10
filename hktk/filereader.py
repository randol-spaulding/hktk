from hktk.fileutil import is_xml, convert_to_pathlib
from xml.etree import ElementTree as ET
from typing import (Union, Iterator)
from pathlib import Path


class XMLLoader:

    files: list[Path]

    def __init__(self, fp: str):
        fp = convert_to_pathlib(fp)
        self.files = []
        if fp.is_dir():
            self.files = [file for file in fp.iterdir() if is_xml(file)]
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

    def get_record_type_summary(self) -> Union[set[str], dict[Path, set[str]]]:
        record_types = dict()
        for file, records in self.get_iterator_by_tag('Record'):
            record_types[file] = set()
            for record in records:
                record_types[file].add(record.get('type'))
        if len(self.files) == 1:
            return record_types[self.files[0]]
        return record_types

    def get_iterator_by_tag(self, tag: str) -> Iterator[tuple[Path, ]]:
        for file in self.files:
            etree = ET.parse(file)
            yield file, etree.iterfind(tag)

    def get_all_records_by_type(self, record_type: str) -> Union[list[ET.Element], dict[Path, list[ET.Element]]]:
        type_records = dict()
        for file, all_records in self.get_iterator_by_tag('Record'):
            records = filter(lambda record: record.get('type') == record_type, all_records)
            type_records[file] = list(records)
        if len(self.files) == 1:
            return type_records[self.files[0]]
        return type_records
