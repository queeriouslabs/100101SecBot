import asyncio
import time
import piplates.RELAYplate as RELAY
from app import create_app


class Latch:

    def __init__(self, name):
        self.app = create_app(name)
        self.app.logger.info(f"Starting {name}")
        self.failed = asyncio.Event()
        self.open = asyncio.Event()
        self.cool = asyncio.Event()
        self.failed.clear()
        self.cool.set()
        self.relay_off()

    async def cooldown(self):
        ''' If the latch is hot, waits for 3s before setting it to cool '''
        if not self.cool.is_set():
            await asyncio.sleep(3)  # cooldown time
            self.cool.set()         # latch is cool

    def relay_on(self):
        ''' handles opening the actual relay via piplates.  Sets the
        latch status to 'hot' by clearing the cool event.
        '''
        self.app.logger.info("Unlocking Front Door")
        RELAY.relayON(0, 2)
        self.cool.clear()  # relay is hot
        self.open.set()    # latch is open

    def relay_off(self):
        ''' closes the relay, clearing the open event, and creating the
        cooldown task '''
        self.app.logger.info("Locking Front Door")
        RELAY.relayOFF(0, 2)
        self.open.clear()                     # latch is closed
        asyncio.create_task(self.cooldown())  # enter cooldown

    async def unlock(self):
        ''' Task to open the lock via the relay, then close the relay
        after a 3s delay.

        If the relay doesn't open after 1s, however, the relay is
        failed, which sets the "relay_failed" event and exits the
        coroutine.
        '''
        cooldown_marker = time.time() #: Track waiting time for relay to open
        while not self.open.is_set():
            try:
                self.relay_on()
                break
            except AssertionError:
                self.app.logger.warning("Relay is missing")
                await asyncio.sleep(0.2)

            if (time.time() - cooldown_marker > 1):
                self.app.logger.error("Relay not opened after 1s, quitting")
                self.failed.set()
                return

        await asyncio.sleep(3)  #: open time: 3s
        self.relay_off()

    async def process(self):
        ''' While the piplate relay is still responding, wait for an
        incoming request.  If the latch is open, ignore the request.  If the
        latch is cooling down, wait, then process the request for the
        correct permissions.
        '''
        while not self.failed.is_set():
            req = await self.app.in_q.get()

            # don't need to process a request if it's already opened
            if self.open.is_set():
                continue

            # it's not open, is it in cooldown period?
            if not self.cool.is_set():
                await self.cool.wait()

            # OK, time to check if we actually handle the permission requested
            for perm in req['permissions']:
                # only need to handle the first grant to open door
                if (perm['grant'] and (perm['perm'] == "/front_door/open")):
                    asyncio.create_task(self.unlock())
                    break  # break for loop, only need first open perm


if __name__ == "__main__":
    front_door = Latch("front_door")
    front_door.app.start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(front_door.process())
    RELAY.relayOFF(0, 2) # uhh...just in case an error occurred
