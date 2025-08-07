""" Functional examples of how to use the comms module to create an
echo server.

The server is implemented as a single async coroutine which runes forever.

It waits on the comms.in_q.get() to act.

When it receives data, it logs something and will send out a
response via comms.out_q.put() which grants any permission requested.

The incoming data is pre-validated as a permission request so it's not
validated here, but it can be as desired.

The outgoing data MUST be a response object as specified in schema.py.  It's
validated before sent to the client by the comms instance.

Note that "echo" is the name passed to create_comms.  This wil create
a socket at "./echo.sock", assuming the configuration is the default.

Look at echo_client.py for the corresponding client-side usage of the comms
module.

Start this component from the command-line like:
    `$ python echo.py`
"""
import asyncio
import json
from secbot.comms import create_comms
from settings import ExampleConfig as comms_config


async def process():

    comms = create_comms("echo", comms_config)
    comms.start()  # start a server which will put data into the in_q

    while True:
        data = await comms.in_q.get() # wait on data in the in_q
        client = data['source_id']

        comms.logger.info(f"got {data} from {client}")

        permissions = data.pop('permissions')
        for perm in permissions:
            resp = data.copy()
            resp['code'] = 0
            resp['msg'] = "Success"
            await comms.out_q.put(resp)  # outgoing data into the out_q


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(process())
    loop.run_forever()
