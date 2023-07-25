import asyncio
from unittest.mock import (
    patch,
    MagicMock,
)
import sys
sys.modules['spidev'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
import time
from evdev import (
    ecodes,
    InputEvent,
    KeyEvent,
)
import pytest

from rfid_reader import RfidReader
from authorizer import Authorizer
from relay import Relay


class MockEvDevice:

    def __init__(self):
        self.name = "Barcode Reader "
        self.scans = asyncio.Queue()

    async def async_read_loop(self):
        for attempt in await self.scans.get():
            yield attempt

    def scan(self, input):
        self.scans.put_nowait(self.string_to_ecode_list(input, True))

    def incomplete_scan(self, input):
        self.scans.put_nowait(self.string_to_ecode_list(intput, False))

    def string_to_ecode_list(self, input, enter=False):
        ''' Helper to create an iterable list of InputEvents from a string, and
        optionally include a termal KEY_ENTER event'''
        out = []
        for ch in input:
            ts = time.time()
            evt = InputEvent(int(ts),
                             int((ts - int(ts))*1_000_000),
                             ecodes.EV_KEY,
                             ecodes.ecodes[f"KEY_{ch.upper()}"],
                             KeyEvent.key_up)
            out.append(evt)
        if enter:
            ts = time.time()
            enter_evt = InputEvent(int(ts),
                                   int((ts - int(ts))*1_000_000),
                                   ecodes.EV_KEY,
                                   ecodes.KEY_ENTER,
                                   KeyEvent.key_up)
            out.append(enter_evt)

        return out


@pytest.fixture
def ev_device():
    return MockEvDevice()


@pytest.fixture
@patch('rfid_reader.RfidReader.find_ev_device')
def test_rfid_reader(find_ev_device, ev_device):
    find_ev_device.return_value = ev_device

    return RfidReader("test_rfid_reader", "Barcode Reader ")


@pytest.fixture
@patch('authorizer.read_data')
def test_authorizer(read_data):
    test_data = {
        'hours': {
            'allhours': [0, 24],
            'daytime': [11, 22]
        },
        'rfids': {
            '0123456789': {
                'access_times': 'allhours',
                'sponsor': 'beka' },
            '9876543210' : {
                'access_times': 'daytime',
                'sponsor': 'matt' }}
    }
    read_data.return_value = test_data
    return Authorizer()


@pytest.mark.asyncio
@pytest.fixture
@patch('relay.RELAY.relayOFF')
async def test_relay(relayOFF):
    return (Relay("front_door_latch"), relayOFF)


def test_make_request():
    src = "this_is_a_source_dev"
    ident = "whatever_needs_to_go_here"

    req = make_request(src, ident)

    assert req["source_id"] == src
    assert req["permissions"][0]["context"]["identifier"] == ident
