import asyncio
from unittest.mock import (
    AsyncMock,
    patch,
)
import time
import pytest
from evdev import (
    InputEvent,
    KeyEvent,
    ecodes
)
from rfid_reader import (
    make_request,
    RfidReader,
)
from settings import Config as comms_config

class MockEvDevice:

    def __init__(self):
        self.name = "Barcode Reader "
        self.stuff = []

    async def async_read_loop(self):
        for x in self.stuff:
            yield x


def string_to_ecode_list(input, enter=False):
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


def test_make_request():
    src = "this_is_a_source_dev"
    ident = "whatever_needs_to_go_here"

    req = make_request(src, ident)

    assert req["source_id"] == src
    assert req["permissions"][0]["ctx"]["identity"] == ident


@pytest.mark.skip
@pytest.mark.asyncio
async def test_async_for():

    async def stuff():
        for x in ['a', 'b', 'c', 'd', 'e', 'f']:
            yield x

    results = ['a', 'b', 'c', 'd', 'e', 'f', 'g']

    async for a in stuff():
        assert a == results.pop(0)


@pytest.mark.asyncio
@patch("rfid_reader.RfidReader.find_ev_device")
async def test_get_reader(find_ev_device):
    name = "front_door_rfid"
    test_string = "1234567890"

    mevdev = MockEvDevice()
    mevdev.stuff = string_to_ecode_list(test_string, True)

    find_ev_device.return_value = mevdev

    rfid = RfidReader(name, "Barcode Reader ", comms_config)
    rfid.comms.request = AsyncMock()

    assert rfid.dev == mevdev

    expected_req = make_request(name, test_string)

    asyncio.create_task(rfid.process())
    await asyncio.sleep(1)
    rfid.comms.request.assert_called()
    rfid.comms.request.assert_awaited()
    rfid.comms.request.assert_called_with("authorizer", expected_req)


@pytest.mark.asyncio
@patch("rfid_reader.RfidReader.find_ev_device")
async def test_missing_dev(find_ev_device):
    name = "front_door_rfid"
    rfid = RfidReader(name, "Barcode Reader ", comms_config)

    rfid.dev = None

    with pytest.raises(ValueError):
        await rfid.process()


@pytest.mark.asyncio
@patch("rfid_reader.RfidReader.find_ev_device")
async def test_bad_key(find_ev_device):
    name = "test_name"
    test_ident = "012345A6789"
    expected_ident = "0123456789"
    expected_req = make_request(name, expected_ident)

    mevdev = MockEvDevice()
    mevdev.stuff = string_to_ecode_list(test_ident, True)
    find_ev_device.return_value = mevdev

    rfid = RfidReader(name, "Barcode Reader ", comms_config)
    rfid.comms.request = AsyncMock()

    assert rfid.dev == mevdev

    asyncio.create_task(rfid.process())
    await asyncio.sleep(1)

    rfid.comms.request.assert_called()
    rfid.comms.request.assert_awaited()
    rfid.comms.request.assert_called_with("authorizer", expected_req)
