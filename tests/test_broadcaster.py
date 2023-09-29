import asyncio
import json
import pytest
from broadcast import process
from comms import create_comms


async def listener(ret_q):
    reader, writer = await asyncio.open_connection('localhost', 8080)
    data = await reader.readline()
    # throw away "Connected"
    data = await reader.readline()
    await ret_q.put(data)


@pytest.mark.asyncio
async def test_broadcast_single_client():
    # start the broadcaster process
    bcast_task = asyncio.create_task(process())

    await asyncio.sleep(.5)
    # add a listening client
    ret_q = asyncio.Queue()
    listen_task = asyncio.create_task(listener(ret_q))
    await asyncio.sleep(.25)

    # simulate a service on the same device as broadcastor
    comms = create_comms("test")

    msg = "\n".join([
        "This is a story",
        "All about how",
        "My life got flipped",
        "Turned upside-down."])

    req = {
        "source_id": "test",
        "target_id": "broadcast",
        "permissions": [
            {
                "perm": "/broadcast",
                "context": {},
                "msg": msg,
            }]}

    await asyncio.sleep(1)
    # fire off the service's message
    await comms.request('broadcast', req, False)
    await asyncio.sleep(.25)

    # hope the listener got a response
    recv = json.loads((await ret_q.get()).decode('utf-8'))

    assert recv == req
    rm = recv['permissions'][0]['msg']
    assert msg == rm

    comms.stop()
    bcast_task.cancel()
    listen_task.cancel()
