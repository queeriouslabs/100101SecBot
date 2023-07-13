import asyncio
import evdev
import datetime
import time
from app import create_app
from schema import validate_request


def make_request(identifier):
    req = {
        "source_id": "rfid_reader",
        "target_id": "front_door_latch",
        "permissions": [{
            "perm": "/open",
            "context": {"identifier": identifier}}]
    }
    return req


async def process():
    app = create_app("rfid_reader")

    # TODO: How do i get addresses
    await app.connect("auth")

    rfid_reader_name = "Barcode Reader "
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    rfid_reader = [d for d in devices if d.name == rfid_reader_name][0]

    if rfid_reader:
        app.logger.info(f"Found {rfid_reader_name}")

    for d in devices:
        if d != rfid_reader:
            d.close()

    keys = []

    async for ev in rfid_reader.async_read_loop():
        if ev.type != evdev.ecodes.EV_KEY:
            continue

        c = evdev.categorize(ev)

        if c.keystate != 0:
            continue

        if ev.code == evdev.ecodes.KEY_ENTER:
            await app.request(make_request("".join(map(str, keys))))
            # yield "".join(map(str, keys))
            keys = []
        else:
            app.logging.info(f"Appending keycode: {c.keycode}, {c.keycode[4:]}")
            try:
                keys.append(int(c.keycode[4:]))
            except ValueError:
                pass
