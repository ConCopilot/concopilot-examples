# -*- coding: utf-8 -*-

from typing import Dict

from .card_detection_correction import ModelScopeCardDetectionCorrection


def constructor(config: Dict):
    return ModelScopeCardDetectionCorrection(config)


__all__=[
    'constructor'
]
