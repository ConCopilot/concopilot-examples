# -*- coding: utf-8 -*-

from typing import Dict

from .server import SimpleWebSocketServer


def constructor(config: Dict):
    return SimpleWebSocketServer(config)


__all__=[
    'constructor'
]
