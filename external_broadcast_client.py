""" A client which acts as an external connection from the network to
the device to receive messages broadcasted by the device.  For example, some
external light up display which consumes messages from the front door.

We know the following when creating a connection to the broadcast component:
    1) It's all utf-8 encoded bytes
    2) All complete messages terminate with b'\r\n'
    3) On connection, the service sends b'Connected\r\n'
    4) All subsequent messages are json objects

"""

import asyncio
import json


async def listen():
    # create the TCP connection
    # replace with IP address if dns doesn't function
    reader, writer = await asyncio.open_connection("the-gibson", 8080)
    # Get the first line
    data = await reader.readline()
    if data == b'Connected\r\n':
        print("Successful Connection")

    # main loop which is only active when a complete line is received from
    # the underlying socket.
    while True:
        data = await reader.readline()

        if data == b'':
            # Connection is probably close
            # we break out of loop and die but you could attempt reconnectins
            # at some reasonable rate
            break
        try:
            # decode to a string and try loading into a json object
            data = json.loads(data.decode('utf-8'))
        except Exception as e:
            # if there's any exception on the decoding or json loading,
            # just toss the data
            print(f"Error: {e}")
            continue

        # at this point we ought to have a json object to inspect.
        if data['source_id'] == "front_door_latch":
            if data['event'] == "/front_door/ready":
                print("Door Is Ready")
            elif data['event'] == "/front_door/open":
                print("Door Is Open")
            elif data['event'] == "/front_door/cooling":
                print("Door is Cooling")
            else:
                print("unknown event!")
        else:
            print("Unhandled Source!")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(listen())
    loop.run_forever()
