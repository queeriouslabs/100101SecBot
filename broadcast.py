import asyncio
import json
from comms import create_comms


MAX_EXTERNAL_CLIENTS = 20  # lmao max clients


async def process():

    comms = create_comms("broadcast")
    comms.start()

    clients = []

    async def on_connect(reader, writer):
        if len(clients) > MAX_EXTERNAL_CLIENTS:
            comms.logger.warning("Max Clients reached, rejecting")
            writer.write(b"501 Max Clients\r\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        cl = (reader, writer)
        clients.append(cl)
        comms.logger.info("Client Connected!")
        writer.write(b"Connected\r\n")
        await writer.drain()

    comms.logger.info("Starting external broadcast server")

    asyncio.create_task(asyncio.start_server(on_connect, '0.0.0.0', 8080))

    # Broadcasting is one way, from this device out to cliends.  Never
    # read from a client, they are awful, awful people with bad breath
    while True:
        data = await comms.in_q.get()
        good = []
        while clients:
            reader, writer = clients.pop()
            try:
                msg = json.dumps(data)
                writer.write(msg.encode('utf-8') + b'\r\n')
                await writer.drain()
            except Exception as e:
                comms.logger.info(e)
                writer.close()
                await writer.wait_closed()
            good.append((reader, writer))

        clients = good  # This '''pattern''' drops disconnected cliends


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.create_task(process())
    loop.run_forever()
