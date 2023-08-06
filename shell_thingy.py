import csv
import os
import shutil
import asyncio
import comms
from database import read_acl_data


def add_user(rfid, access_hours, sponsor):
    pass


def del_user(rfid):
    pass


def mod_user(rfid, access_hours, sponsor):
    del_user(rfid)
    add_user(rfid, access_hours, sponsor)


async def notify_authorizer():
    link = comms.create_comms('shell')
    request = {
        'target_id': 'authorizer',
        'source_id': 'shell',
        'permissions': [{
            'perm': '/reload',
            'ctx': {}
        }]}
    await link.request('authorizer', request)


def commit():
    pass
    # save file
    # notify authorizer to reload file


def main():
    acl_data = read_acl_data()
    hours = acl_data['hours']
    rfids = acl_data['rfids']
