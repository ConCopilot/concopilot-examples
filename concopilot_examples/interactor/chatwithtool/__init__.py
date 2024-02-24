# -*- coding: utf-8 -*-

from typing import Dict

from .interactor import ChatWithToolInteractor


def constructor(config: Dict, *args):
    return ChatWithToolInteractor(config, *args)


__all__=[
    'constructor'
]
