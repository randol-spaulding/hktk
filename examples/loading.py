from hktk.filereader import XMLLoader


def main(path_to_export_dot_xml: str):
    loader = XMLLoader(path_to_export_dot_xml)

    print('Record types:')
    for record_type in loader.get_record_type_summary():
        records = loader.get_all_records_by_type(record_type)
        print(f'\t{record_type}: num={len(records)}')
