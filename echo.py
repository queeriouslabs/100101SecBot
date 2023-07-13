import asyncio
import json
from app import create_app


async def process():

    app = create_app("echo")
    app.start()

    while True:
        data = await app.in_q.get()
        client = data['source_id']

        app.logger.info(f"got {data} from {client}")

        permissions = data.pop('permissions')
        for perm in permissions:
            resp = data.copy()
            resp['perm'] = perm
            resp['grant'] = True
            await app.out_q.put(resp)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(process())
    loop.run_forever()
