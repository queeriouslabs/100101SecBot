import asyncio
import json
from comms import create_comms


async def test_echo():
    name = "echo_client"
    comms = create_comms(name)
    # await comms.connect("echo")
    # reader, _ = comms.connections['echo']

    for x in range(0, 100):
        req = {
            "source_id": name,
            "target_id": 'echo',
            "permissions": [
                {
                    "perm": "/open/the/door",
                    "context": {"number": x}
                }]}
        print(await comms.request("echo", req))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_echo())
