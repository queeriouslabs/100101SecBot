"""
Communication can be split between Inter-Process Communication (IPC) which
communicates between processes on the same device, and IP networking, aka
Internet Protocol, which would be between devices.

When executing on a unix-lixe device, IPC is manged via unix domain sockets.

Python's asyncio manages both with similar approaches but separate function
calls.

Abstracting out the commuication allows easy replacement as needed.
"""
import asyncio
import json
from json import JSONDecodeError
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from signal import (
    SIGTERM,
    SIGINT,
)

from settings import (
    Config,
    ProdConfig
)


class Comms:
    """ This class abstracts communication between components.

    Components on the same unix-like device use unix domain sockets.
    Components on different devices use IP/TCP sockets.

    Note:
        This class is specific for unix domain sockets.  The intention is to
    extent it for IP/TCP.

    To use, instanciate an instance with a device-unique name.  This impies a
    component specific socket at `<socket_root>/<name>.sock`.  `start` will
    create the socket if a server is necessary, i.e. if this components listens
    for connections.  Not all components need to listen, some just generate
    requests.

    Read via `new_data = await self.in_q.get()` to handing incoming data, and
    write via `await self.out_q.put(output)` in the specific application.

    If a device only makes requests, it can use the `request` method which
    requires a response.

    The rest of the communication is abstracted.

    You can subclass this if you are a monster, or just instanciate it via
    the `create_comms` helper function below.

    FIXME: Haven't decided if this will be ONLY unix domain scokets and there
    will be another class for IP/TCP, and a bridge will be required, or
    if this can be stuffed with all types of connections and bridges
    explicitly manged via the user of the instance.
    """
    def __init__(self, name):
        self.name = name
        self.callback = None
        self.clients = {}
        self.config = None
        self.connections = {}
        self.logger = logging.getLogger(name)
        self.server = None
        self.servers = {}
        self.socket_root = "."
        self.in_q = asyncio.Queue()
        self.out_q = asyncio.Queue()
        self.set_callback()
        self.tasks = {}

    def set_config(self, config):
        self.config = config
        self.socket_root = config.SOCKET_ROOT

    def start(self):
        """ Start's a server listening to a unix domain socket which is
        located in the `self.socket_root` directory with filename
        `{self.name}.sock`.

        Adds signal handlers for SIGTERM and SIGINT to call self.cleanup.
        """
        self.server = asyncio.start_unix_server(
            self.callback,
            f"{self.socket_root}/{self.name}.sock"
        )
        self.tasks['receiver'] = asyncio.create_task(self.server)
        self.tasks['responder'] = asyncio.create_task(self.response())
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(SIGTERM, self.cleanup)
        loop.add_signal_handler(SIGINT, self.cleanup)

    def stop(self):
        """ Stops the server and all associated tasks, removing the socket
        from the filesystem"""
        if self.server:
            self.server.close()

        sock_path = f"{self.name}.sock"
        if sock_path in os.listdir(self.socket_root):
            os.unlink(f"{self.socket_root}/{sock_path}")

        task_names = list(self.tasks.keys())
        while self.tasks:
            task = self.tasks.pop(task_names.pop())
            task.cancel()

    def cleanup(self):
        """ When a signal is received, this function is called to stop the
        server and exit gracefully
        """
        self.logger.warning("Cleaning up")
        self.stop()
        self.logger.warning("Exiting")
        exit()

    def set_callback(self):
        """ Constructs the client callback for an asyncio server, which
        closes over 'self' so the class' members are accessible in the
        callback.
        """

        async def client_callback(reader, writer):
            """ Implements the basic communication protocol.

            When a client connections, it MUST send a `\n` terminated
            string.

            That string MUST be decodeable as 'utf-8' into a valid
            JSON string.

            That JSON string MUST be valid request(see schema.py), though
            for performance reasons it's not programmatically validated.

            The request `source_id` dict member is used as the
            client identification and the client connections are stored
            in the self.connetions dict via that key.

            The request's dictionary representation is placed into the
            self.in_q for reading by the user of this comm instance.

            This is looped for all incoming client data.

            The server will close connections on errors in the incoming
            data.
            """
            req = await reader.readline()
            if reader.at_eof():
                return
            if (req == b''):
                return
            try:
                req = json.loads(req.decode('utf-8'))
            except (AttributeError, JSONDecodeError) as e:
                writer.close()
                await writer.wait_closed()
                raise e

            if (src_id := req.get('source_id')):
                if src_id in self.clients:
                    temp_r, temp_w = self.clients.pop(src_id)
                    try:
                        temp_w.close()
                        await temp_w.wait_closed()
                    except Exception as e:
                        self.logger(f"{e}")

                if src_id not in self.clients:
                    self.clients[src_id] = (reader, writer)
                await self.in_q.put(req)

            while True:
                req = await reader.readline()
                if reader.at_eof():
                    break
                if (req == b''):
                    continue
                try:
                    req = json.loads(req.decode('utf-8'))
                except (AttributeError, JSONDecodeError) as e:
                    writer.close()
                    await writer.wait_closed()
                    raise e

                if (src_id := req.get('source_id')):
                    if src_id not in self.clients:
                        self.clients[src_id] = (reader, writer)
                    await self.in_q.put(req)

        self.callback = client_callback

    async def connect(self, server):
        """ Make a connection to a local unix domain socket in the
        socket_root directory and keeps the connection in self.servers.
        """
        if server not in self.servers:
            sock_path = self.socket_root + "/" + server + ".sock"
            reader, writer = await asyncio.open_unix_connection(sock_path)
            self.servers[server] = (reader, writer)

    async def disconnect(self, conn_name):
        """ Disconnects from a local unix domain socket in self.servers.
        """
        if conn_name in self.servers:
            reader, writer = self.servers.pop(conn_name)
            writer.close()
            await writer.wait_closed()

    async def request(self, addr, req):
        """ A one-off request to a server.

        A user of this comms instance makes requests to other components on
        this device via thier unique name which identifies a socket in
        the socket_root directory.

        Manages the client-side request of the protocol.

        A request MUST be a valid request (see schema.py).

        That request MUST (and in this case, will) encode as a 'utf-8'
        json string.

        That string MUST end with a b'\n'.

        Expects a single response returned to the caller.
        """

        if addr not in self.servers:
            sock_path = f"{self.socket_root}/{addr}.sock"
            reader, writer = await asyncio.open_unix_connection(sock_path)
            self.servers[addr] = (reader, writer)
        else:
            reader, writer = self.servers[addr]

        msg = json.dumps(req).encode('utf-8')
        writer.write(msg + b'\n')
        await writer.drain()
        data = await reader.readline()

        if data == b'':
            return {}
        try:
            data = json.loads(data)
        except JSONDecodeError as e:
            self.logger.error(f"{e}")

        return data

    async def response(self):
        """ A response is always sent back to a connected client.

        Data put into the out_q MUST be a valid response (see schema.py).

        The source_id of the response is where the response is going.

        The source_id ought to be in self.clients dict to use the
        connection created via the server's client_callback.

        The Server does not close the connections.

        Note that the response must be generated by the user of this
        comm instance.

        """
        while True:
            data = await self.out_q.get()

            client_id = data['source_id']
            msg = json.dumps(data).encode('utf-8')
            if client_id in self.clients:
                _, client = self.clients[client_id]
                client.write(msg + b'\n')
                await client.drain()


def config_logging(comms, comms_config):
    """ Configures logging for comms related components.

    Uses a TimedRotatingFileHandler to rotate logs automatically
    once a week, keeping a years worth of logs by default.

    Pass in a Comm instance and a Config from settings.py.
    """
    handler = TimedRotatingFileHandler(
        filename=comms_config.LOG_FILE,
        when="W6",
        interval=1,
        backupCount=52,
        encoding=None,
        delay=False,
        utc=True,
        atTime=None)

    formatter = logging.Formatter(comms_config.LOG_FORMAT)
    handler.setLevel(comms_config.LOG_LEVEL)
    handler.setFormatter(formatter)
    comms.logger.addHandler(handler)
    comms.logger.setLevel(comms_config.LOG_LEVEL)
    comms.logger.info("Logging enabled")


def create_comms(name):
    """ Helper function to create a configured Comms instance.

    Specificy a `name` which is unique on the executing device which
    corresponse to the component using a unix domain socket with the
    same name.

    e.g. you must consider the `name` a a device-unique identifier which
    addresses this component, and that other components on this device will
    use to address this component.
    """
    comms = Comms(name)
    # I don't like this.   Inherent from some flask stuff.
    # make a loader/executor which just configs the thing, or something.
    if os.environ.get('QUEERIOUSLABS_ENV') == 'PROD':
        comms_config = ProdConfig()
    else:
        comms_config = Config()

    comms.set_config(comms_config)
    config_logging(comms, comms_config)
    comms.logger.info(f"App {name} initialized")
    return comms
