# -*- coding: utf-8 -*-

from typing import Dict

from .glmmodel import GLMModel


def constructor(config: Dict):
    return GLMModel(config)


__all__=[
    'constructor'
]
