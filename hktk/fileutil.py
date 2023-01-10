from typing import Union
from pathlib import Path


def is_xml(fp: Union[str, Path]) -> bool:
    if isinstance(fp, str):
        return fp.split('.')[-1] == 'xml'
    elif isinstance(fp, Path):
        return fp.is_file() and fp.suffix == '.xml'
    else:
        raise TypeError(f'Invalid input of type {type(fp)}')


def convert_to_pathlib(fp: str) -> Path:
    return Path(fp)
