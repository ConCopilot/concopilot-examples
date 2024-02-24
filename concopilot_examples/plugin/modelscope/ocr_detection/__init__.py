# -*- coding: utf-8 -*-

from typing import Dict

from .ocr_detection import ModelScopeOCRDetection


def constructor(config: Dict):
    return ModelScopeOCRDetection(config)


__all__=[
    'constructor'
]
