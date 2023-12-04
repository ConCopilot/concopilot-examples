# -*- coding: utf-8 -*-

from typing import Dict

from .glmcerebrum import GLMCerebrum


def constructor(config: Dict):
    return GLMCerebrum(config)


__all__=[
    'constructor'
]
