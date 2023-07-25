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


@pytest.mark.asyncio
@patch('relay.RELAY.relayON')
@patch('authorizer.datetime')
async def test_access_control(dt,
                              relayON,
                              test_rfid_reader,
                              test_authorizer,
                              test_relay):

    rfid_reader = test_rfid_reader
    scanner = rfid_reader.dev

    auth = test_authorizer
    relay, relayOFF = await test_relay

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
    assert relayOFF.called
    assert relayON.called
    await asyncio.sleep(3.1)

    auth.comms.stop()
    relay.comms.stop()

    while tasks:
        tasks.pop().cancel()
