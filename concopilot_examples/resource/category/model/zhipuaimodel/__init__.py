# -*- coding: utf-8 -*-

from typing import Dict

from .zhipuaimodel import ZhipuAILLM


def constructor(config: Dict):
    return ZhipuAILLM(config)


__all__=[
    'constructor'
]
