'''
broadcast.py will serve TCP clients on the network and local clients via
a unix domain socket at /<socket root>/broadcast.sock.   Anything written to
the unix socket will be broadcast to all TCP clients with no checking.

Clients are never read and cannot impact the service, they only may
receive infomation send by the service.

to test, you can run the service as is:
    $ python broadcast.py

In another terminal, you can connect a TCP client to the interface:
    $ telnet localhost 8080

In a 3rd terminal, simulate a local device sending messages to the broadcast
service using the broadcast_client.py:
    $ python broacast_client.py

The messages will be echoed to the TCP client throught he broadcast service.
Any tcp client which can access the service can connect to receive broadcast
messages.
'''
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
        comms.logger.info(f"Client Connected: {len(clients)}")
        writer.write(b"Connected\r\n")
        await writer.drain()

    comms.logger.info("Starting external broadcast server")

    asyncio.create_task(asyncio.start_server(on_connect, '0.0.0.0', 8080))

    # Broadcasting is one way, from this device out to cliends.  Never
    # read from a client, they are awful, awful people with bad breath
    while True:
        data = await comms.in_q.get()
        comms.logger.debug(f"{__file__}: Got data: {data}")
        good = []
        while clients:
            reader, writer = clients.pop()
            comms.logger.debug(f"{__file__}: sending to client")
            try:
                msg = json.dumps(data)
                writer.write(msg.encode('utf-8') + b'\r\n')
                await writer.drain()
                good.append((reader, writer))
            except ConnectionError:
                writer.close()
            except Exception as e:
                comms.logger.debug(e)
                writer.close()
                await writer.wait_closed()

        clients = good  # This '''pattern''' drops disconnected cliends


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.create_task(process())
    loop.run_forever()
