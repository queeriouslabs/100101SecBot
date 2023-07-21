import asyncio
import json
from comms import create_comms


async def process():

    comms = create_comms("echo")
    comms.start()

    while True:
        data = await comms.in_q.get()
        client = data['source_id']

        comms.logger.info(f"got {data} from {client}")

        permissions = data.pop('permissions')
        for perm in permissions:
            resp = data.copy()
            resp['perm'] = perm
            resp['grant'] = True
            await comms.out_q.put(resp)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(process())
    loop.run_forever()
