# -*- coding: utf-8 -*-

from typing import Dict

from .ocr_recognition import ModelScopeOCRRecognition


def constructor(config: Dict):
    return ModelScopeOCRRecognition(config)


__all__=[
    'constructor'
]
