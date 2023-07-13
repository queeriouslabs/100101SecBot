import asyncio
import json
from app import create_app


async def test_echo():
    # sock = "./test_sock"
    # reader, writer = await asyncio.open_unix_connection(sock)
    name = "echo_client"
    app = create_app(name)
    await app.connect("echo")
    reader, _ = app.connections['echo']

    for x in range(0, 100):
        req = {
            "source_id": "echo",
            "target_id": "echo",
            "permissions": [
                {
                    "perm": "/open/the/door",
                    "context": {"what": x}
                }]}
        await app.request(req)

        print(await reader.readline())

    await app.disconnect("echo")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_echo())
