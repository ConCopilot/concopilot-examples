# -*- coding: utf-8 -*-

from typing import Dict

from .server import SimpleHttpServer


def constructor(config: Dict):
    return SimpleHttpServer(config)


__all__=[
    'constructor'
]
