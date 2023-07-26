""" This Relay componenent is implemneted with a piplates Relay Plate:
    https://pi-plates.com/relayr1/

The openness of the door is not tracked.  What is tracked is if the relay is
on or off.

When the relay is ON the door is UNLOCKED.

The door is held UNLOCKED for 3s to allow a human to open it.
The lock is engaged after 3s.  The door can still close while locked.
After the relay is turned off, it is held in a un-usable state for 3s.  This
let's the relay cooldown.

Thus the minimal cycle for unlocking is 6s.

If the relay is ON and a request comes in to turn the relay ON, the request
is ignored.

Worst case behavior is a request can be made again.  At human scale, the
order of seconds is fine as it requires physical motion.

If the RelayPlate cannot communicate with the driver, the relay enters a
failed state.

The states of Open, Close, and Failed are managed via asyncio Events which
may be awaited, checked, or toggled via coroutines.

On initialization the relay is closed.
"""
import asyncio
import time
import piplates.RELAYplate as RELAY
from comms import create_comms


class Relay:

    def __init__(self, name):
        self.comms = create_comms(name)
        self.comms.logger.info(f"Starting {name}")
        self.failed = asyncio.Event()
        self.open = asyncio.Event()
        self.cool = asyncio.Event()
        self.failed.clear()
        self.cool.clear()
        RELAY.relayOFF(0, 2)

    async def cooldown(self):
        ''' If the latch is hot, waits for 3s before setting it to cool '''
        if not self.cool.is_set():
            await asyncio.sleep(3)  # cooldown time
            self.cool.set()         # latch is cool

    def relay_on(self):
        ''' handles opening the actual relay via piplates.  Sets the
        latch status to 'hot' by clearing the cool event.
        '''
        self.comms.logger.info("Unlocking Front Door")
        RELAY.relayON(0, 2)
        self.cool.clear()  # relay is hot
        self.open.set()    # latch is open

    def relay_off(self):
        ''' closes the relay, clearing the open event, and creating the
        cooldown task '''
        self.comms.logger.info("Locking Front Door")
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
                self.comms.logger.warning("Relay is missing")
                await asyncio.sleep(0.2)

            if (time.time() - cooldown_marker > 1):
                self.comms.logger.error("Relay not opened after 1s, quitting")
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
        self.comms.start()

        while not self.failed.is_set():
            req = await self.comms.in_q.get()

            # don't need to process a request if it's already opened
            if self.open.is_set():
                continue

            # it's not open, is it in cooldown period?
            if not self.cool.is_set():
                await self.cool.wait()

            # OK, time to check if we actually handle the permission requested
            for perm in req['permissions']:
                # only need to handle the first grant to open door
                if (perm['grant'] and (perm['perm'] == "/open")):
                    asyncio.create_task(self.unlock())
                    break  # break for loop, only need first open perm


if __name__ == "__main__":
    front_door = Relay("front_door_latch")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(front_door.process())
    RELAY.relayOFF(0, 2) # uhh...just in case an error occurred
