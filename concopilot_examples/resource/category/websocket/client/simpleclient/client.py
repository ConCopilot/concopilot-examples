# -*- coding: utf-8 -*-

import websockets.sync.client
import threading

from typing import Dict, Union, Iterable, Optional

from concopilot.framework.resource import Resource


class SimpleWebSocketClient(Resource):
    def __init__(self, config: Dict):
        super(SimpleWebSocketClient, self).__init__(config)
        self._host=self.config.config.host
        self._port=self.config.config.port
        self._ssl_cert_path=self.config.config.ssl_cert_path
        self._uri=f'wss://{self._host}:{self._port}' if self._ssl_cert_path else f'ws://{self._host}:{self._port}'

        self._conn=None

    def recv(self, timeout: Optional[float] = None) -> Union[str, bytes]:
        return self._conn.recv(timeout)

    def send(self, msg: Union[Union[str, bytes], Iterable[Union[str, bytes]]]) -> None:
        self._conn.send(msg)

    def ping(self, data: Optional[Union[str, bytes]] = None) -> threading.Event:
        return self._conn.ping(data)

    def pong(self, data: Union[str, bytes] = b"") -> None:
        self._conn.pong(data)

    def initialize(self):
        if self._ssl_cert_path:
            import ssl
            ssl_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(self._ssl_cert_path)
        else:
            ssl_context=None

        self._conn=websockets.sync.client.connect(self._uri, ssl_context=ssl_context)

    def finalize(self):
        self._conn.close()
