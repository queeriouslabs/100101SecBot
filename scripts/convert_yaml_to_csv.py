#!/usr/bin/env python3
import csv
import os
import shutil
import yaml


def build_context():
    context = {}
    contents = os.listdir()
    context['data_backup_exists'] = 'data_backup' in contents
    context['data_exists'] = 'data' in contents
    context['ids_file_exists'] = 'ids.yaml' in contents
    if context['data_backup_exists']:
        backup_contents = os.listdir('data_backup/')
        context['ids_in_backup'] = 'ids.yaml' in backup_contents
    if context['data_exists']:
        data_contents = os.listdir('data/')
        context['hours_in_data'] = 'hours.csv' in data_contents
        context['rfids_in_data'] = 'rfids.csv' in data_contents

    return context


def convert_yaml_to_csv():
    # open ids.yaml for reading
    with open('ids.yaml', 'r') as f:
        y = yaml.safe_load(f.read())

        # dump access time labels to hours.csv
        with open('data/hours.csv', 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["name", "start_hour", "end_hour"])
            for level in y['levels']:
                writer.writerow([level, y['levels'][level]['hours'][0], y['levels'][level]['hours'][1]])

        # dump rfid entries to rfids.csv
        with open('data/rfids.csv', 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['rfid', 'access_times', 'sponsor'])
            for sponsor in y['rfids']:
                for item in y['rfids'][sponsor]:
                    writer.writerow([item['id'], item['level'], sponsor])


def main():
    ctx = build_context()
    if not ctx['ids_file_exists']:
        raise ValueError("ids.yaml not available, quitting")
    if not ctx['data_backup_exists']:
        os.mkdir('data_backup')
        shutil.copy('ids.yaml', 'data_backup')
    if not ctx['data_exists']:
        os.mkdir('data')
    if ctx.get('rfids_in_data'):
        raise ValueError("rfids.csv already exists, quitting")
    convert_yaml_to_csv()

if __name__ == '__main__':
    # main()
    print("\n\nThis was already done, you probably don't want to run this\n")
    print("And if you do, you probably need to edit the paths.\n\n")
