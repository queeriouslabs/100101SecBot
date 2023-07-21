import asyncio
import sys
from unittest.mock import (
    patch,
    AsyncMock,
    MagicMock
)
# modules used by piplate but don't function on non-rpi env
sys.modules['spidev'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
import pytest
import relay


@pytest.mark.asyncio
@patch("relay.RELAY.relayON")
@patch("relay.RELAY.relayOFF")
async def test_init(relayOFF, relayON):
    ''' Initialization of the relay modules means that the
    relay is not failed, it is not open, and it is cool.

    Mocking relayON and relayOFF is required in a testing env to control the
    non-existent piplate.RELAYplate
    '''
    front_door = relay.Relay("front_door")
    task = asyncio.create_task(front_door.process())

    await asyncio.sleep(0)
    assert not front_door.failed.is_set()
    assert not front_door.open.is_set()
    assert front_door.cool.is_set()
    assert relayOFF.called

    task.cancel()
    front_door.comms.logger.handlers.clear()


@pytest.mark.asyncio
@patch("relay.RELAY.relayON")
@patch("relay.RELAY.relayOFF")
async def test_open(relayOFF, relayON):
    front_door = relay.Relay("front_door")
    task = asyncio.create_task(front_door.process())

    await asyncio.sleep(0)

    open_req = {
        'permissions': [{
            'grant': True,
            'perm': '/front_door/open'}, ]}

    await front_door.comms.in_q.put(open_req)
    await front_door.open.wait()
    assert not front_door.cool.is_set()
    await front_door.cool.wait()
    assert not front_door.open.is_set()
    task.cancel()
    front_door.comms.logger.handlers.clear()


@pytest.mark.asyncio
@patch("relay.RELAY.relayON")
@patch("relay.RELAY.relayOFF")
@patch("relay.Relay.unlock")
async def test_open_already_open(unlock_coro, relayOFF, relayON):
    front_door = relay.Relay("front_door")
    task = asyncio.create_task(front_door.process())
    await asyncio.sleep(0)

    open_req = {
        'permissions': [{
            'grant': True,
            'perm': '/front_door/open'}, ]}

    # set relay as open
    front_door.open.set()
    await front_door.comms.in_q.put(open_req)
    await asyncio.sleep(2)

    assert not unlock_coro.called

    task.cancel()
    front_door.comms.logger.handlers.clear()


@pytest.mark.asyncio
@patch("relay.RELAY.relayON")
@patch("relay.RELAY.relayOFF")
async def test_relay_failure(relayOFF, relayON):
    front_door = relay.Relay("front_door")
    task = asyncio.create_task(front_door.process())
    await asyncio.sleep(0)

    relayON.side_effect = AssertionError

    open_req = {
        'permissions': [{
            'grant': True,
            'perm': '/front_door/open'}, ]}

    await front_door.comms.in_q.put(open_req)
    await front_door.failed.wait()
    assert front_door.failed.is_set()

    task.cancel()
    front_door.comms.logger.handlers.clear()


@pytest.mark.asyncio
@patch("relay.RELAY.relayON")
@patch("relay.RELAY.relayOFF")
async def test_relay_hot(relayOFF, relayON):
    front_door = relay.Relay("front_door")
    task = asyncio.create_task(front_door.process())
    await asyncio.sleep(0)

    open_req = {
        'permissions': [{
            'grant': True,
            'perm': '/front_door/open'}, ]}

    # make relay hot
    front_door.cool.clear()
    await asyncio.sleep(.25)
    assert not front_door.cool.is_set()
    await front_door.comms.in_q.put(open_req)

    await asyncio.sleep(.25)
    assert not front_door.cool.is_set()
    assert not relayON.called
    front_door.cool.set()
    await asyncio.sleep(3)
    assert relayON.called

    task.cancel()
    front_door.comms.logger.handlers.clear()
