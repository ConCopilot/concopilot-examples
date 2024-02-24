# -*- coding: utf-8 -*-

from typing import Dict

from .pipeline import ModelScopePipeline


def constructor(config: Dict):
    return ModelScopePipeline(config)


__all__=[
    'constructor'
]
