# 81, 84-87, 91-94, 120, 135-136, 180
import asyncio
import os
from unittest.mock import patch
import pytest
from comms import create_comms
import schema


@pytest.mark.asyncio
async def test_comms_init():

    test_server_name = "test_server_name"
    server = create_comms(test_server_name)
    assert server.name == test_server_name
    assert server.socket_root == "."
    assert server.callback
    assert server.config

    server.start()
    await asyncio.sleep(.1)
    assert server.server
    assert f"{server.name}.sock" in os.listdir(server.socket_root)
    assert 'receiver' in server.tasks.keys()
    assert server.tasks['receiver']
    assert 'responder' in server.tasks.keys()
    assert server.tasks['responder']

    server.stop()
    assert not server.tasks
    assert f"{server.name}.sock" not in os.listdir(server.socket_root)

    with pytest.raises(SystemExit) as e:
        server.cleanup()


@pytest.mark.asyncio
async def test_client_server_connections():
    test_server_name = "test_server_name"
    server = create_comms(test_server_name)
    server.start()
    await asyncio.sleep(0)

    test_client_name = "test_client_name"
    client = create_comms(test_client_name)

    await client.connect(test_server_name)
    assert test_server_name in client.servers

    await client.disconnect(test_server_name)
    assert test_server_name not in client.servers

    server.stop()


@pytest.mark.asyncio
async def test_client_server_communication():

    async def process(comms):
        data = await comms.in_q.get()
        client = data['source_id']

        resp = data.copy()
        resp.pop('permissions')
        resp['code'] = 0
        resp['msg'] = "Success"
        await comms.out_q.put(resp)

        # permissions = data.pop('permissions')
        # for perm in permissions:
            # grant = data.copy()
            # grant['perm'] = perm
            # grant['grant'] = True

    test_server_name = "test_server_name"
    server = create_comms(test_server_name)
    server.start()
    await asyncio.sleep(0)
    asyncio.create_task(process(server))

    test_client_name = "test_client_name"
    client = create_comms(test_client_name)

    perm = "/what/a/permission"
    perm_context = { "key": "value" }
    permission = {
        "perm": perm,
        "context": perm_context }
    schema.validate_permission(permission)

    request = {
        "source_id": test_client_name,
        "target_id": test_server_name,
        "permissions": [ permission ]}
    schema.validate_request(request)

    grant = {
        "source_id": test_client_name,
        "target_id": test_server_name,
        "perm": permission,
        "grant": True
    }
    schema.validate_grant(grant)

    resp = {
        "source_id": test_client_name,
        "target_id": test_server_name,
        "code": 0,
        "msg": "Success"
    }
    schema.validate_response(resp)

    server_response = await client.request(test_server_name, request)
    assert server_response == resp
    server.stop()
