# -*- coding: utf-8 -*-

from typing import Dict

from .zhipuaicerebrum import ZhipuAICerebrum


def constructor(config: Dict):
    return ZhipuAICerebrum(config)


__all__=[
    'constructor'
]
