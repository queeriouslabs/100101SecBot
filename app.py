import asyncio
import datetime
import json
from json import JSONDecodeError
from jsonschema import ValidationError
import logging
from logging.handlers import TimedRotatingFileHandler
import os
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
        self.config = None
        self.logger = logging.getLogger(__name__)
        self.tasks = {}
        self.callback = None
        self.server = None
        self.server_task = None
        self.socket_root = "."
        self.in_q = asyncio.Queue()
        self.out_q = asyncio.Queue()
        self.set_callback()
        self.connections = {}

    def start(self):
        self.server = asyncio.start_unix_server(
            self.callback,
            f"{self.socket_root}/{self.name}.sock"
        )
        self.tasks['receiver'] = asyncio.create_task(self.server)
        self.tasks['responder'] = asyncio.create_task(self.response())

    def stop(self):
        if self.server:
            self.server.close()

    async def response(self):
        while True:
            data = await self.out_q.get()

            validate_response(data)

            client_id = data['target_id']
            msg = json.dumps(data).encode('utf-8')
            if client_id in self.connections:
                _, client = self.connections[client_id]
                client.write(msg + b'\n')
                await client.drain()

    def set_callback(self):
        """ Constructs the client callback for asyncio server, closed over
        'self' so the app's members are accessible in the callback. """

        async def client_callback(reader, writer):
            while True:
                req = await reader.readline()
                try:
                    req = json.loads(req.decode('utf-8'))
                except (AttributeError, JSONDecodeError):
                    writer.close()
                    await writer.wait_closed()
                    return

                try:
                    validate_request(req)
                except ValidationError:
                    writer.close()
                    await writer.wait_closed()
                    return

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

    async def request(self, req):
        validate_request(req)

        target = req['target_id']
        if target in self.connections:
            _, server = self.connections.get(target)
            msg = json.dumps(req).encode('utf-8')
            server.write(msg + b'\n')
            await server.drain()


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
    app.logger.info("Logging enabled")
    app.logger.info("App initialized")
    return app
