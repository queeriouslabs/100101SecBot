import csv
import pudb


def read_acl_data():
    """ reads persistent acl data from the filesystem
    """
    hours = {}
    rfids = {}

    with open("data/hours.csv", 'r') as f:
        hours_csv = csv.reader(f)
        next(hours_csv)  # drop header
        for row in hours_csv:
            hours[row.pop(0)] = row

    with open("data/rfids.csv", 'r') as f:
        rfids_csv = csv.DictReader(f)
        for row in rfids_csv:
            rfids[row.pop('rfid')] = row

    return {'hours': hours, 'rfids': rfids}


def write_rfid_data(rfids):
    """ writes the rfids.csv file in the data directory """
    with open('data/rfids.csv', 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['rfid', 'access_times', 'sponsor'])
        for rfid in rfids:
            writer.writerow([rfid,
                             rfids[rfid]['access_times'],
                             rfids[rfid]['sponsor']])


def write_hours_data(hours):
    """ writes the hours.csv file in the data directory """
    with open('data/hours.csv', 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['name', 'start_hour', 'end_hour'])
        for level in hours:
            writer.writerow(level,
                            hours[level][0],
                            hours[level][1])
