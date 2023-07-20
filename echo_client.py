import asyncio
import json
from app import create_app


async def test_echo():
    name = "echo_client"
    app = create_app(name)
    # await app.connect("echo")
    # reader, _ = app.connections['echo']

    for x in range(0, 100):
        req = {
            "source_id": name,
            "target_id": 'echo',
            "permissions": [
                {
                    "perm": "/open/the/door",
                    "context": {"number": x}
                }]}
        print(await app.request("echo", req))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_echo())
