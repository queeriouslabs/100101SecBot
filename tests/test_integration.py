import asyncio
from datetime import datetime
from unittest.mock import (
    patch,
    AsyncMock,
    MagicMock,
    Mock,
)
import sys
sys.modules['spidev'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
import pytest


@pytest.mark.skip("Won't work, debugging only")
@pytest.mark.asyncio
@patch('authorizer.datetime')
async def test_mock_ev_device(dt, ev_device):
    scanner = ev_device

    test_rfid_1 = "0123456789"
    test_rfid_2 = "9876543210"

    scanner.scan(test_rfid_1)
    async for ev in scanner.async_read_loop():
        print(ev)

    scanner.scan(test_rfid_2)
    async for ev in scanner.async_read_loop():
        print(ev)


@pytest.mark.skip("Won't work, debugging only")
@pytest.mark.asyncio
@patch('authorizer.datetime')
async def test_mock_rfid_reader(dt, test_rfid_reader):
    scanner = test_rfid_reader.dev

    test_rfid_1 = "0123456789"
    test_rfid_2 = "9876543210"

    scanner.scan(test_rfid_1)
    async for ev in scanner.async_read_loop():
        print(ev)

    scanner.scan(test_rfid_2)
    async for ev in scanner.async_read_loop():
        print(ev)


@pytest.mark.asyncio
@patch('relay.RELAY.relayOFF')
@patch('relay.RELAY.relayON')
@patch('authorizer.datetime')
async def test_access_control(dt,
                              relayON,
                              relayOFF,
                              test_rfid_reader,
                              test_authorizer,
                              test_relay):

    rfid_reader = test_rfid_reader
    scanner = rfid_reader.dev

    auth = test_authorizer
    relay, relay_off = await test_relay

    all_hours_rfid = '0123456789'
    daytime_rfid = '9876543210'

    dt.now = Mock(return_value=datetime(2023, 1, 2, 9, 30))

    loop = asyncio.get_event_loop()

    tasks = [asyncio.create_task(auth.process()),
             asyncio.create_task(rfid_reader.process()),
             asyncio.create_task(relay.process())]

    await asyncio.sleep(.1)
    scanner.scan(all_hours_rfid)

    await asyncio.sleep(.1)
    assert relayON.called
    await asyncio.sleep(3.1)
    assert relayOFF.called

    scanner.scan(all_hours_rfid)

    await asyncio.sleep(7)
    assert relayON.call_count == 2
    assert relayOFF.call_count == 2

    # access denied, not between 11 and 22
    scanner.scan(daytime_rfid)
    await asyncio.sleep(7)
    assert relayON.call_count == 2
    assert relayOFF.call_count == 2

    dt.now = Mock(return_value=datetime(2023, 1, 2, 11, 30))
    scanner.scan(daytime_rfid)
    await asyncio.sleep(7)
    assert relayON.call_count == 3
    assert relayOFF.call_count == 3

    auth.comms.stop()
    relay.comms.stop()

    while tasks:
        tasks.pop().cancel()
