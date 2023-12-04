# -*- coding: utf-8 -*-

from typing import Dict

from .interface import WebChatUserInterface


def constructor(config: Dict):
    return WebChatUserInterface(config)


__all__=[
    'constructor'
]
