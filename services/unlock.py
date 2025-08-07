import asyncio
import getpass
import os

from secbot.comms import create_comms

request = {
    "source_id": "unlock_cli",
    "target_id": "front_door_latch",
    "permissions": [{
        "perm": "/open",
        "grant": True}]
}


async def cli_unlock(config, req):
    name = "cli_unlock"
    comms = create_comms(name, config)

    user = getpass.getuser()
    comms.logger.info(f"cli unlock by {user}")

    target_id = req["target_id"]
    await comms.request(target_id, req)


if __name__ == "__main__":
    config = None
    if os.environ.get("QUEERIOUSLABS_ENV", None) == 'PROD':
        from settings import ProdConfig as config
    else:
        from settings import Config as config

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli_unlock(config, request))
