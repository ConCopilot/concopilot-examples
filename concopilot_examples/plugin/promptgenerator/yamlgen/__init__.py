# -*- coding: utf-8 -*-

from typing import Dict

from .generator import YamlPluginPromptGenerator


def constructor(config: Dict):
    return YamlPluginPromptGenerator(config)


__all__=[
    'constructor'
]
