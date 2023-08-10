#!/usr/bin/env python3
# https://codeburst.io/building-beautiful-command-line-interfaces-with-python-26c7e1bb54df
import asyncio
import csv
import os
import shutil
import sys

from pyfiglet import figlet_format
from termcolor import colored
from InquirerPy import (
    inquirer,
    get_style,
)
from InquirerPy.base.control import (
    Choice,
)

import comms
from database import (
    read_acl_data,
    write_rfid_data,
)


def add_user(rfids, new_rfid, access_hours, sponsor):
    rfids[new_rfid] = {'access_times': access_hours,
                       'sponsor': sponsor}


def del_user(rfids, target_rfid):
    del rfids[target_rfid]


def mod_user(rfids, target_rfid, access_hours, sponsor):
    del_user(rfids, target_rfid)
    add_user(rfids, target_rfid, access_hours, sponsor)


async def notify_authorizer():
    link = comms.create_comms('shell')
    request = {
        'target_id': 'authorizer',
        'source_id': 'shell',
        'permissions': [{
            'perm': '/reload',
            'ctx': {}
        }]}
    print("Notifying authorizer")
    print(await link.request('authorizer', request))
    await link.disconnect("authorizer")


def commit():
    pass
    # save file
    # notify authorizer to reload file


def inquire_sponsors(rfids, cur_sponsor=None):
    sponsors = set(data['sponsor'] for rfid, data in rfids.items())
    if not sponsors:
        print("No sponsors available.")
        return None

    sponsor = inquirer.select(message="Sponsor: ",
                              choices=sponsors,
                              mandatory=True).execute()
    return sponsor


def inquire_hours(hours, cur_hours=None):
    display_hours = [Choice(label, name=f"{label}:  ({values[0]}-{values[1]})")
                     for label, values in hours.items()]

    rfid_hours = inquirer.select(
        message="Access Hours: ",
        choices=display_hours,
        mandatory=True,
    ).execute()

    return rfid_hours


def add_rfid_handler(rfids, hours, dirty):
    done = False

    while not done:
        new_rfid = inquirer.text(
            message="Please enter new RFID: ",
            mandatory=True,
            validate=lambda result: len(result) > 0,
            invalid_message="Input cannot be empty",
        ).execute()

        if new_rfid in rfids:
            next_step = inquirer.select(
                message="RFID exists.  Go Back or Modify it?",
                choices=["Go Back", "Modify"]
            ).execute()
            if next_step=="Modify":
                return mod_rfid_handler(rfids, hours, dirty, new_rfid)
            else:
                return False

        rfid_hours = inquire_hours(hours)
        sponsor = inquire_sponsors(rfids)
        if not sponsor:
            sponsor = inquirer.text(
                message="Sponsor required and none found.  Please enter a name:",
                mandatory=True,
                validate=lambda result: len(result) > 0,
                invalid_message="Input cannot be empty",
            ).execute()

        new_rec = f"'{sponsor}' is adding new rfid '{new_rfid}' with access '{rfid_hours}'\n"
        new_rec = new_rec + "Confirm? "
        confirm = inquirer.confirm(new_rec).execute()

        if confirm:
            add_user(rfids, new_rfid, rfid_hours, sponsor)
            dirty = True
            done = True

    return dirty


def mod_rfid_handler(rfids, hours, dirty, target_rfid=None):
    if not target_rfid:
        target_rfid = inquirer.text(message="Target RFID: ").execute()

    if target_rfid not in rfids:
        print(f"RFID {target_rfid} not found, returning")
        return False

    cur_hours = rfids[target_rfid]['access_times']
    cur_sponsor = rfids[target_rfid]['sponsor']

    done = False
    while not done:
        print(f"Modifying {target_rfid}")

        new_hours = inquire_hours(hours, cur_hours)
        new_sponsor = inquire_sponsors(rfids, cur_sponsor)

        if cur_hours == new_hours and cur_sponsor == new_sponsor:
            print(f"No changes detected, returning")
            break

        newline = False
        msg = f"rfid {target_rfid} has been modified: \n"
        if (cur_hours != new_hours):
            msg += f"    hours from '{cur_hours}' to '{new_hours}'"
            newline=True
        if (cur_sponsor != new_sponsor):
            if newline:
                msg += "\n"
            msg += f"    sponsor from '{cur_sponsor}' to '{new_sponsor}'"
        msg += "\nIs this correct?"

        confirm = inquirer.confirm(message=msg).execute()
        if confirm:
            mod_user(rfids, target_rfid, new_hours, new_sponsor)
            dirty=True
            done=True

    return dirty


def del_rfid_handler(rfids, hours, dirty):
    done = False
    while not done:
        target_rfid = inquirer.text(message="Target RFID: ").execute()

        if target_rfid not in rfids:
            print(f"RFID {target_rfid} not found, returning")
            return False

        msg = f"Confirm removal RFID '{target_rfid}'?"
        confirm = inquirer.confirm(message=msg).execute()

        if confirm:
            del_user(rfids, target_rfid)
            assert target_rfid not in rfids
            dirty=True
            done=True

    return dirty


def commit_handler(rfids, hours, dirty):
    if dirty:
        write_rfid_data(rfids)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(notify_authorizer())
    return False


def quit_handler(rfids, hours, dirty):
    if dirty:
        save = inquirer.confirm(message="Save Changes?").execute()
        if not save:
            sys.exit(0)
        else:
            commit_handler(rfids, hours, dirty)
    sys.exit(0)
    return False


def setup_style():
    style = get_style({
    }, style_override=False)
    return style


def run(style):
    acl_data = read_acl_data()
    hours = acl_data['hours']
    rfids = acl_data['rfids']
    dirty = False
    running = True

    handlers = {"Quit": quit_handler,
                "Add RFID Access": add_rfid_handler,
                "Modify RFID Access": mod_rfid_handler,
                "Remove RFID Access": del_rfid_handler,
                }

    while running:
        if dirty:
            handlers.update({"Commit Changes": commit_handler})
        else:
            handlers.pop('Commit Changes', None)

        command = inquirer.select(
            message="Command:", choices=list(handlers.keys())).execute()

        dirty = handlers[command](rfids, hours, dirty)


def main():
    style = setup_style()
    print(colored(figlet_format("QueeriousLabs\nSecBot", "slant"), "magenta"))
    run(style)


if __name__ == "__main__":
    main()
