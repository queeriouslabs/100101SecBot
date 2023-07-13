import asyncio
import time
import piplates.RELAYplate as RELAY
from app import create_app


_app = None
relay_failed = asyncio.Event()
relay_open = asyncio.Event()
relay_cool = asyncio.Event()


async def relay_cooldown():
    await asyncio.sleep(3)
    relay_cool.set()


def relay_on():
    _app.logger.info("Unlocking Front Door")
    RELAY.relayON(0, 2)
    relay_open.set()
    relay_cool.clear()


def relay_off():
    _app.logger.info("Locking Front Door")
    RELAY.relayOFF(0, 2)
    relay_open.clear()
    asyncio.create_task(relay_cooldown())


async def open():
    cooldown_marker = time.time() #: Track waiting time

    while not relay_open.is_set():
        try:
            relay_on()
            cooldown_marker = time.time()
            break
        except AssertionError:
            app.logger.warn("Relay is missing")
            await asyncio.sleep(0.2)

        if (time.time() - cooldown_marker > 1):
            app.logger.error("Relay not opened after 1s, quitting")
            relay_failed.set()
            return

    await asyncio.sleep(3 - (time.time() - cooldown_marker))
    relay_off()


async def process():
    global _app
    name = "front_door"
    _app = create_app(f"{name}")
    _app.logger.info(f"Starting {name}")
    relay_off()
    relay_failed.clear()

    while not relay_failed.is_set():
        req = await _app.in_q.get()

        # don't need to process a request if it's already opened
        if relay_open.is_set():
            continue

        if not relay_cool.is_set():
            await relay_cool.wait()

        for p in req['permissions']:
            # only need to handle the first grant to open door
            if (p['grant'] and (p['perm'] == "/front_door/open")):
                asyncio.create_task(open())
                break
