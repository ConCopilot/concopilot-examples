# -*- coding: utf-8 -*-

import os
import threading
import logging

from typing import Dict

from http.server import HTTPServer, SimpleHTTPRequestHandler
from concopilot.framework.resource import Resource


logger=logging.getLogger(__file__)


class SimpleHttpServer(Resource):
    def __init__(self, config: Dict):
        super(SimpleHttpServer, self).__init__(config)
        self._host=self.config.config.host
        self._port=self.config.config.port
        self._directory=os.path.abspath(self.config.config.directory if self.config.config.directory else '.')
        self._uri=f'http://{self._host}:{self._port}'

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
        dir=self._directory

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super(Handler, self).__init__(*args, directory=dir, **kwargs)

        self._server=HTTPServer((self.host, self.port), RequestHandlerClass=Handler)
        self._thrd=threading.Thread(target=self._server.serve_forever)
        self._thrd.start()
        logger.info(f'A SimpleHttpServer started at: {self.uri}')

    def finalize(self):
        self._server.shutdown()
        self._thrd.join()
