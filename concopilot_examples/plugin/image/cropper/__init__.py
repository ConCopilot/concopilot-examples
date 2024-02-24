# -*- coding: utf-8 -*-

from typing import Dict

from .cropper import ImageCopper


def constructor(config: Dict):
    return ImageCopper(config)


__all__=[
    'constructor'
]
