# -*- coding: utf-8 -*-

from typing import Dict

from .client import SimpleWebSocketClient


def constructor(config: Dict):
    return SimpleWebSocketClient(config)


__all__=[
    'constructor'
]
