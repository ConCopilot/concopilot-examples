# -*- coding: utf-8 -*-

import websockets
import websockets.sync.server
import websockets.exceptions
import threading
import logging

from typing import Dict

from concopilot.framework.resource import Resource


logger=logging.getLogger(__file__)


class SimpleWebSocketServer(Resource):
    def __init__(self, config: Dict):
        super(SimpleWebSocketServer, self).__init__(config)
        self._host=self.config.config.host
        self._port=self.config.config.port
        self._ssl_cert_path=self.config.config.ssl_cert_path
        self._uri=f'wss://{self._host}:{self._port}' if self._ssl_cert_path else f'ws://{self._host}:{self._port}'

        self._connections=set()
        self._server=None
        self._thrd: threading = None

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def uri(self) -> str:
        return self._uri

    def initialize(self):
        def handler(websocket):
            self._connections.add(websocket)
            try:
                logger.info('A connection has been connected.')
                while True:
                    data=websocket.recv()
                    for conn in self._connections.copy()-{websocket}:
                        try:
                            conn.send(data)
                        except websockets.exceptions.ConnectionClosed:
                            self._connections.remove(conn)
            except websockets.exceptions.ConnectionClosed:
                logger.info('A connection has been closed.')
            finally:
                self._connections.remove(websocket)

        if self._ssl_cert_path:
            import ssl
            ssl_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(self._ssl_cert_path)
        else:
            ssl_context=None

        self._server=websockets.sync.server.serve(handler, self.host, self.port, ssl_context=ssl_context)
        self._thrd=threading.Thread(target=self._server.serve_forever)
        self._thrd.start()

    def finalize(self):
        self._server.shutdown()
        self._thrd.join()
