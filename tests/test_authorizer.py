import asyncio
import copy
from datetime import datetime
from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)
import pytest
from authorizer import (
    Authorizer,
)


@patch("authorizer.read_data")
def test_authorizer_init(read_data):
    test_data = {
        'hours': {
            'allhours': [0, 24],
            'daytime': [11, 22]
        },
        'rfids': {
            '01234567890' : {
                'access_times': 'allhours',
                'sponsor': 'beka' }}
    }
    read_data.return_value = test_data

    authy = Authorizer()

    assert authy.hours == test_data['hours']
    assert authy.rfids == test_data['rfids']


@patch('authorizer.datetime')
@patch("authorizer.read_data")
def test_authorizer_lookup(read_data, dt):
    rfid1 = '0000000001'
    rfid2 = '0000000002'
    rfid3 = '0000000003'

    test_data = {
        'hours': {
            'allhours': [0, 24],
            'daytime': [11, 22]
        },
        'rfids': {
            rfid1 : {
                'access_times': 'allhours',
                'sponsor': 'beka' },
            rfid2 : {
                'access_times': 'daytime',
                'sponsor': 'beka' }}
    }
    read_data.return_value = test_data

    authy = Authorizer()

    permission = "/open"
    ctx_1 = {'identity' : rfid1}
    ctx_2 = {'identity' : rfid2}
    ctx_3 = {'identity' : rfid3}

    # too early for daytime access
    dt.now = Mock(return_value=datetime(2023, 1, 2, 9, 30))
    assert authy.lookup(permission, copy.deepcopy(ctx_1))
    assert not authy.lookup(permission, copy.deepcopy(ctx_2))
    assert not authy.lookup(permission, copy.deepcopy(ctx_3))

    # very beginning of daytime access
    dt.now = Mock(return_value=datetime(2023, 1, 2, 11, 0))
    assert authy.lookup(permission, copy.deepcopy(ctx_1))
    assert authy.lookup(permission, copy.deepcopy(ctx_2))
    assert not authy.lookup(permission, copy.deepcopy(ctx_3))

    # inside daytime access
    dt.now = Mock(return_value=datetime(2023, 1, 2, 15, 30))
    assert authy.lookup(permission, copy.deepcopy(ctx_1))
    assert authy.lookup(permission, copy.deepcopy(ctx_2))
    assert not authy.lookup(permission, copy.deepcopy(ctx_3))

    # very end of daytime access
    dt.now = Mock(return_value=datetime(2023, 1, 2, 22, 0))
    assert authy.lookup(permission, copy.deepcopy(ctx_1))
    assert not authy.lookup(permission, copy.deepcopy(ctx_2))
    assert not authy.lookup(permission, copy.deepcopy(ctx_3))

    # too late for daytime access
    dt.now = Mock(return_value=datetime(2023, 1, 2, 22, 0))
    assert authy.lookup(permission, copy.deepcopy(ctx_1))
    assert not authy.lookup(permission, copy.deepcopy(ctx_2))
    assert not authy.lookup(permission, copy.deepcopy(ctx_3))

    ctx_e = {}
    with pytest.raises(ValueError):
        authy.lookup(permission, ctx_e)


@patch('authorizer.datetime')
@patch('authorizer.read_data')
def test_authorizer_grant_permissions(read_data, dt):
    rfid1 = '0000000001'
    rfid2 = '0000000002'
    rfid3 = '0000000003'

    test_data = {
        'hours': {
            'allhours': [0, 24],
            'daytime': [11, 22]
        },
        'rfids': {
            rfid1 : {
                'access_times': 'allhours',
                'sponsor': 'beka' },
            rfid2 : {
                'access_times': 'daytime',
                'sponsor': 'beka' }}
    }
    read_data.return_value = test_data

    permission = "/open"
    ctx_1 = {'identity' : rfid1}
    ctx_2 = {'identity' : rfid2}
    ctx_3 = {'identity' : rfid3}

    req_1 = {
        "source_id": "test_source",
        "target_id": "test_target",
        "permissions" : [{
            "perm": permission,
            "ctx": ctx_1 }]}
    req_2 = {
        "source_id": "test_source",
        "target_id": "test_target",
        "permissions" : [{
            "perm": permission,
            "ctx": ctx_2 }]}
    req_3 = {
        "source_id": "test_source",
        "target_id": "test_target",
        "permissions" : [{
            "perm": permission,
            "ctx": ctx_3 }]}

    authy = Authorizer()

    dt.now = Mock(return_value=datetime(2023, 1, 2, 9, 30))
    authy.grant_permissions(req_1)
    assert req_1['permissions'][0]['grant']
    authy.grant_permissions(req_2)
    assert not req_2['permissions'][0]['grant']
    authy.grant_permissions(req_3)
    assert not req_3['permissions'][0]['grant']


@pytest.mark.asyncio
@patch('authorizer.datetime')
@patch('authorizer.read_data')
async def test_authorizer_process(read_data, dt):
    rfid1 = '0000000001'
    rfid2 = '0000000002'
    rfid3 = '0000000003'

    test_data = {
        'hours': {
            'allhours': [0, 24],
            'daytime': [11, 22]
        },
        'rfids': {
            rfid1 : {
                'access_times': 'allhours',
                'sponsor': 'beka' },
            rfid2 : {
                'access_times': 'daytime',
                'sponsor': 'beka' }}
    }
    read_data.return_value = test_data

    permission = "/open"
    ctx_1 = {'identity' : rfid1}
    ctx_2 = {'identity' : rfid2}
    ctx_3 = {'identity' : rfid3}

    req_1 = {
        "source_id": "test_source",
        "target_id": "front_door_latch",
        "permissions" : [{
            "perm": permission,
            "ctx": ctx_1 }]}
    req_2 = {
        "source_id": "test_source",
        "target_id": "front_door_latch",
        "permissions" : [{
            "perm": permission,
            "ctx": ctx_2 }]}
    req_3 = {
        "source_id": "test_source",
        "target_id": "front_door_latch",
        "permissions" : [{
            "perm": permission,
            "ctx": ctx_3 }]}

    exp_1 = copy.deepcopy(req_1)
    exp_1['permissions'][0]['grant'] = True
    exp_1['permissions'][0]['ctx'] ={}

    authy = Authorizer()
    authy.comms.request = AsyncMock()

    dt.now = Mock(return_value=datetime(2023, 1, 2, 9, 30))
    process = asyncio.create_task(authy.process())
    await asyncio.sleep(0)

    await authy.comms.in_q.put(req_1)
    await asyncio.sleep(0)
    assert authy.comms.request.awaited
    assert authy.comms.request.assert_called
    authy.comms.request.assert_awaited_with(exp_1['target_id'], exp_1)
    authy.comms.request.assert_called_with(exp_1['target_id'], exp_1)

    authy.comms.stop()
    process.cancel()
