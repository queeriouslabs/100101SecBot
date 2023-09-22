""" A client which sends a request to the echo component.

This client does not create it's own server, but makes use of the
"comms.request" to connect and make 100 permission requests.

The device name is "echo_client" which is also the source_id of the
request.

The requests will be validated by comms.request and so validation
is skipped here for simplicitly.

comms.request("echo", req) send the dict which is serialized and validated,
and returns a reponse, which is then printed.

For this to work, ensure that the echo.py component is started first.

This will run on it's own like:
    `$ python echo_client.py`
"""
import asyncio
from comms import create_comms


async def broadcast_test():
    name = "broadcast_client"
    comms = create_comms(name)

    for x in range(0, 100):
        req = {
            "source_id": name,
            "target_id": 'broadcast',
            "permissions": [
                {
                    "perm": "/open/the/door",
                    "context": {"number": x},
                    "msg": "lmao",
                }]}
        print(await comms.request("broadcast", req, resp=False))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(broadcast_test())
