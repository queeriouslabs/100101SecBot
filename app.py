import asyncio
import datetime
import json
from json import JSONDecodeError
from jsonschema import ValidationError
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from signal import (
    SIGTERM,
    SIGINT,
)
import time

from settings import (
    Config,
    ProdConfig
)
from schema import (
    validate_request,
    validate_response,
)


class App:

    def __init__(self, name):
        self.name = name
        self.callback = None
        self.config = None
        self.connections = {}
        self.logger = logging.getLogger(__name__)
        self.server = None
        self.server_task = None
        self.socket_root = "."
        self.in_q = asyncio.Queue()
        self.out_q = asyncio.Queue()
        self.set_callback()
        self.tasks = {}

    def start(self):
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
        #TODO: What to do about tasks
        if self.server:
            self.server.close()

        sock_path = f"{self.name}.sock"
        if sock_path in os.listdir(self.socket_root):
            os.unlink(f"{self.socket_root}/{sock_path}")

        for task in self.tasks:
            self.logger.info(f"Cancelling {task}")
            self.tasks[task].cancel()

    def cleanup(self):
        self.logger.warn("Cleaning up")
        self.stop()
        self.logger.warn("Exiting")
        exit()

    def set_callback(self):
        """ Constructs the client callback for asyncio server, closed over
        'self' so the app's members are accessible in the callback. """

        async def client_callback(reader, writer):
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

                try:
                    validate_request(req)
                except ValidationError as e:
                    writer.close()
                    await writer.wait_closed()
                    raise e

                if(src_id := req.get('source_id')):
                    self.connections[src_id] = (reader, writer)
                    await self.in_q.put(req)

        self.callback = client_callback

    async def connect(self, server):
        if server not in self.connections:
            sock_path = self.socket_root + "/" + server + ".sock"
            reader, writer = await asyncio.open_unix_connection(sock_path)
            self.connections[server] = (reader, writer)

    async def disconnect(self, conn_name):
        if conn_name in self.connections:
            reader, writer = self.connections.pop(conn_name)
            writer.close()
            await writer.wait_closed()

    async def request(self, addr, req):
        ''' A one-off request to a server.  Expects a response.'''

        validate_request(req)
        target = req['target_id']
        if target != addr:
            raise ValueError(f"addr: {addr} and target: {target} mismatched")

        sock_path = f"{self.socket_root}/{addr}.sock"
        reader, writer = await asyncio.open_unix_connection(sock_path)

        msg = json.dumps(req).encode('utf-8')
        writer.write(msg + b'\n')
        await writer.drain()

        data = await reader.readline()
        writer.close()
        await writer.wait_closed()

        try:
            data = json.loads(data)
        except JSONDecodeError as e:
            self.logger(f"{e}")

        validate_response(data)
        return data

    async def response(self):
        # Always goes back to the source
        while True:
            data = await self.out_q.get()

            validate_response(data)

            client_id = data['source_id']
            msg = json.dumps(data).encode('utf-8')
            if client_id in self.connections:
                _, client = self.connections[client_id]
                client.write(msg + b'\n')
                await client.drain()


def config_logging(app, app_config):
    handler = TimedRotatingFileHandler(
        filename=app_config.LOG_FILE,
        when="W6",
        interval=1,
        backupCount=52,
        encoding=None,
        delay=False,
        utc=True,
        atTime=None)

    formatter = logging.Formatter(app_config.LOG_FORMAT)
    handler.setLevel(app_config.LOG_LEVEL)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(app_config.LOG_LEVEL)
    app.logger.info("Logging enabled")


def create_app(name):
    app = App(name)
    # I don't like this.   Inherent from some flask stuff.
    # make a loader/executor which just configs the thing, or something.
    if os.environ.get('QUEERIOUSLABS_ENV') == 'PROD':
        app_config = ProdConfig()
    else:
        app_config = Config()

    app.config = app_config
    config_logging(app, app_config)
    app.logger.info(f"App {name} initialized")
    return app
