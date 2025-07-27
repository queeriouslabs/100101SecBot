#!/usr/bin/env python3
"""
Based on https://codeburst.io/building-beautiful-command-line-interfaces-with-python-26c7e1bb54df

With changes of course.  PyInquirer is not maintained, replaced with InquirerPy
"""
import asyncio
import os
import sys

from pyfiglet import figlet_format
from termcolor import colored
from InquirerPy import (
    inquirer,
)
from InquirerPy.base.control import (
    Choice,
)
from InquirerPy.utils import color_print

from secbot import comms
from secbot.database import (
    read_acl_data,
    write_rfid_data,
)


def add_user(rfids, new_rfid, access_hours, sponsor):
    """ Mutates the main 'rfids' dict by adding the new_rfid
    with access_hours and sponsor
    """
    rfids[new_rfid] = {'access_times': access_hours,
                       'sponsor': sponsor}


def del_user(rfids, target_rfid):
    """ Mutates the `rfids` dict and removes tne entry for
    `target_rfids`.
    """
    rfids.pop(target_rfid, None)


def mod_user(rfids, target_rfid, access_hours, sponsor):
    """ Mutates the `rfids` dict at entry `target_rfid` by first deleting
    the entry and then adding a new one for `target_rfid`.
    """
    del_user(rfids, target_rfid)
    add_user(rfids, target_rfid, access_hours, sponsor)


async def notify_authorizer():
    """ Sends a message to the rfid authorizer service to reload the cached
    access control list, in the event it was updated.
    """
    if os.environ.get("QUEERIOSLABS_ENV", None) == "PROD":
        from settings import ProdConfig as comms_config
    else:
        from settings import Config as comms_config

    link = comms.create_comms('shell', comms_config)
    request = {
        'target_id': 'authorizer',
        'source_id': 'shell',
        'permissions': [{
            'perm': '/reload',
            'ctx': {}
        }]}
    color_print([("magenta", "Notifying authorizer")])
    try:
        resp = await link.request('authorizer', request)
    except FileNotFoundError as e:
        color_print(
            [("yellow", "Authorizer not found, perhaps not running")])
        link.logger.handlers.clear()
        return
    msg = ""
    if resp['msg'] == "OK":
        color = "magenta"
        msg = "Done"
    else:
        color = "red"
        msg = "Please check Authorizer."
    color_print([(color, msg)])
    await link.disconnect("authorizer")
    # turn off logging handler for this link
    link.logger.handlers.clear()


def inquire_sponsors(rfids, cur_sponsor=None):
    """ Constructs a list of available sponsors from the list of existing
    sponsors in the existing rfid entires.
    When there are NO sponsors (i.e. the file is empty), then
    a sponsor is prompted.
    Does not otherwise ask for a new sponsor.
    """
    sponsors = set(data['sponsor'] for rfid, data in rfids.items())
    sponsors = sorted(list(sponsors))
    if "unknown" in sponsors:
        sponsors.remove("unknown")

    if cur_sponsor == "unknown":
        cur_sponsor = None

    if not sponsors:
        color_print([("yellow", "No sponsors available.")])
        return None

    sponsor = inquirer.select(message="Sponsor: ",
                              choices=sponsors,
                              default=cur_sponsor,
                              mandatory=True).execute()
    return sponsor


def inquire_hours(hours, cur_hours=None):
    """ Requests the user select the access hours label
    """
    display_hours = [Choice(label, name=f"{label}:  ({values[0]}-{values[1]})")
                     for label, values in hours.items()]

    rfid_hours = inquirer.select(
        message="Access Hours: ",
        choices=display_hours,
        default=cur_hours,
        mandatory=True,
    ).execute()

    return rfid_hours


def add_rfid_handler(rfids, hours, dirty):
    """ Adds a new rfid record, prompting the user for the rfid, access times,
    and sponsor.
    """
    done = False

    while not done:
        new_rfid = inquirer.text(
            message="Please enter new RFID: ",
            mandatory=True,
        ).execute()

        if not new_rfid:
            return dirty

        if new_rfid in rfids:
            next_step = inquirer.select(
                message="RFID exists.  Go Back or Modify it?",
                choices=["Go Back", "Modify"]
            ).execute()
            if next_step == "Modify":
                return mod_rfid_handler(rfids, hours, dirty, new_rfid)
            else:
                return dirty

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
    """ Modifies an rfid record, editing either the hours or the sponsor.
    If the record doesn't exist, exits to the main prompt.
    """
    if not target_rfid:
        target_rfid = inquirer.text(message="Target RFID: ").execute()

    if target_rfid not in rfids:
        color_print([("red", f"RFID {target_rfid} not found, returning")])
        return dirty

    cur_hours = rfids[target_rfid]['access_times']
    cur_sponsor = rfids[target_rfid]['sponsor']

    done = False
    while not done:
        color_print([("magenta", f"Modifying {target_rfid}")])

        new_hours = inquire_hours(hours, cur_hours)
        new_sponsor = inquire_sponsors(rfids, cur_sponsor)

        if cur_hours == new_hours and cur_sponsor == new_sponsor:
            color_print([("magenta", "No changes detected, returning")])
            break

        newline = False
        msg = [("", "rfid "),
               ("magenta", f"{target_rfid}"),
               ("", " has been "),
               ("yellow", "modified: \n")]
        if (cur_hours != new_hours):
            msg.extend([
                ("magenta", "    hours"),
                ("", " from '"),
                ("red", f"{cur_hours}"),
                ("", "' to '"),
                ("green", f"{new_hours}"),
                ("", "'")])
            newline = True
        if (cur_sponsor != new_sponsor):
            if newline:
                msg.append(("", "\n"))
            msg.extend([
                ("magenta", "    sponsor"),
                ("", " from '"),
                ("red", f"{cur_sponsor}"),
                ("", "' to '"),
                ("green", f"{new_sponsor}"),
                ("", "'")])
        color_print(msg)

        confirm = inquirer.confirm(message="Is this correct? ").execute()
        if confirm:
            mod_user(rfids, target_rfid, new_hours, new_sponsor)
            dirty = True
            done = True

    return dirty


def del_rfid_handler(rfids, hours, dirty):
    """ Confirms with the user to remove a specified rfid record.
    """
    done = False
    while not done:
        target_rfid = inquirer.text(message="Target RFID: ").execute()

        if target_rfid not in rfids:
            color_print([("red", f"RFID {target_rfid} not found, returning")])
            return dirty

        msg = f"Confirm removal RFID '{target_rfid}'?"
        confirm = inquirer.confirm(message=msg).execute()

        if confirm:
            del_user(rfids, target_rfid)
            assert target_rfid not in rfids
            dirty = True
            done = True

    return dirty


def commit_handler(rfids, hours, dirty):
    """ Commits the rfid records back to disk and notifies the authorizer.
    """
    if dirty:
        save = inquirer.confirm(message="Save Changes?").execute()
        if not save:
            return dirty
        color_print([("magenta", "Saving changes")])
        write_rfid_data(rfids)
        color_print([("green", "Saved")])
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as e:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(notify_authorizer())
    return False


def quit_handler(rfids, hours, dirty):
    """ Exits, confirming with the user to save or not if data has not aleady
    been committed.
    """
    if dirty:
        dirty = commit_handler(rfids, hours, dirty)
    if dirty:
        color_print([("yellow", "Abandoning Changes")])
    sys.exit(0)


def run():
    """ Main operating loop """
    acl_data = read_acl_data()
    hours = acl_data['hours']
    rfids = acl_data['rfids']
    dirty = False
    running = True

    handlers = {
        "Add RFID Access": add_rfid_handler,
        "Modify RFID Access": mod_rfid_handler,
        "Remove RFID Access": del_rfid_handler,
        "Quit": quit_handler,
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
    euid = os.geteuid()
    if euid != 0:
        color_print([("yellow", "Script not started as root, running sudo")])
        args = ['sudo', sys.executable] + sys.argv + [os.environ]
        os.execlpe('sudo', *args)
    print(colored(figlet_format("QueeriousLabs\nSecBot", "slant"), "magenta"))
    run()


if __name__ == "__main__":
    main()
