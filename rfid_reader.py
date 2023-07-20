import asyncio
import evdev
from app import create_app
from schema import validate_request


def make_request(source_id, identifier):
    ''' Creates a open permission request targetting the front_door_latch
        adding the identifier to the permission's context '''
    req = {
        "source_id": source_id,
        "target_id": "front_door_latch",
        "permissions": [{
            "perm": "/open",
            "context": {"identifier": identifier}}]
    }
    return req


class RfidReader:

    def __init__(self, name, dev_name):
        self.name = name
        self.app = create_app(name)
        self.dev = self.find_ev_device(dev_name)

    def find_ev_device(self, label):
        ''' Returns an evdev.InputDevice, if found, with name==label.'''
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        try:
            rfid_reader = [d for d in devices if d.name == label][0]
        except IndexError:
            self.app.logger.error(f"No RFID reader: {label}")
            exit()
        if rfid_reader:
            self.app.logger.info(f"Found {label}")

        for d in devices:
            if d != label:
                d.close()

        return rfid_reader

    async def process(self):
        keys = []

        if not self.dev:
            raise ValueError(f"Missing device for {self.name}")

        async for ev in self.dev.async_read_loop():
            if ev.type != evdev.ecodes.EV_KEY or ev.value != 0:
                continue

            if ev.code != evdev.ecodes.KEY_ENTER:
                c = evdev.categorize(ev)
                self.app.logger.info(
                    f"Appending keycode: {c.keycode}, {c.keycode[4:]}")
                try:
                    keys.append(c.keycode[4:])
                except ValueError as e:
                    pass
            else:
                identifier = "".join(keys)
                try:
                    # ignores response
                    await self.app.request("auth",
                                           make_request(self.name, identifier))
                except ValueError as e:
                    self.app.logger.error(f"Auth request failed with {e}")
                keys = []


if __name__ == "__main__":
    front_door_reader = RfidReader("front_door_rfid", "Barcode Reader ")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(front_door_reader.process())
