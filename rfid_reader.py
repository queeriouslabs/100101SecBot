""" This implemenetation of an RFID Reader expects a keyboard-like device
which registers with linux's event sub-system.

`evdev` does all the heavy lifting of interacting with the device and emits
individual InputEvents for analysis, which represent keyboard key interactions.

"down" presses are ignored in favor of readering "up" events (e.g. key-release)
and the return key represents the end of an string of input.

That string of input is treated as an identifier, and this component
interprets this identifier as a request to open the front door.

The main loop waits for input from the event subsystem and analyzes each event
to fit the input criteria, storing key values until return is detected.
"""
import asyncio
import evdev
from comms import create_comms


def make_request(source_id, identifier):
    """ Helper function to creates permission request targetting the
    front_door_latch, adding the identifier to the permission's context
    """
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
        self.comms = create_comms(name)
        self.dev = self.find_ev_device(dev_name)

    def find_ev_device(self, label):
        """ Queries devices for one with the name `label` and returns an
        evdev.InputDevice, if found.

        If no device is found with such a name, exit the interpretter.
        """
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        try:
            rfid_reader = [d for d in devices if d.name == label][0]
        except IndexError:
            self.comms.logger.error(f"No RFID reader: {label}")
            exit()
        if rfid_reader:
            self.comms.logger.info(f"Found {label}")

        for d in devices:
            if d != label:
                d.close()

        return rfid_reader

    async def process(self):
        """ Main loop for this component.  Waits on events from the event
        device and checks if they are Key Presses.  If they are, it will
        filter out Key Down (press) in favor of Key Up (release).  The
        value of the keys are derived from the key codes (e.g. KEY_5).

        non-integers are filtered out except for Return, which represents
        the end of an input string.

        When enter is found, the string is assemled and sent to the
        `authenticator` component with a permission request to open the front
        door.
        """
        keys = []

        if not self.dev:
            raise ValueError(f"Missing device for {self.name}")

        async for ev in self.dev.async_read_loop():
            if ev.type != evdev.ecodes.EV_KEY or ev.value != 0:
                continue

            if ev.code != evdev.ecodes.KEY_ENTER:
                c = evdev.categorize(ev)
                self.comms.logger.info(
                    f"Appending keycode: {c.keycode}, {c.keycode[4:]}")
                try:
                    keys.append(int(c.keycode[4:]))
                except ValueError as e:
                    pass
            else:
                identifier = "".join(map(str, keys))
                try:
                    # ignores response
                    await self.comms.request("authenticator",
                                           make_request(self.name, identifier))
                except ValueError as e:
                    self.comms.logger.error(f"Auth request failed with {e}")
                keys = []


if __name__ == "__main__":
    front_door_reader = RfidReader("front_door_rfid", "Barcode Reader ")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(front_door_reader.process())
