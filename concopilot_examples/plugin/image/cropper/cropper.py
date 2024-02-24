# -*- coding: utf-8 -*-

import cv2
import logging
import numpy as np

from typing import Dict, List, Union, Any

from PIL import Image
from concopilot.framework.plugin import AbstractPlugin
from concopilot.util.context import AssetRef
from concopilot.util import ClassDict


logger=logging.getLogger(__file__)


class ImageCopper(AbstractPlugin):
    def __init__(self, config: Dict):
        super(ImageCopper, self).__init__(config)

    def crop(
        self,
        img_data: Any,
        cut_polygons: Union[np.ndarray, List[np.ndarray], List[List[int]], List[List[List[int]]]],
        **kwargs
    ) -> List[np.ndarray]:
        img_data=AssetRef.try_retrieve(img_data, self.context.assets)
        if img_data is None:
            raise ValueError('The `img_data` is a required field but not passed!')
        cut_polygons=AssetRef.try_retrieve(cut_polygons, self.context.assets)
        if cut_polygons is None:
            raise ValueError('The `cut_polygons` is a required field but not passed!')

        if isinstance(img_data, Image.Image):
            img_data=np.asarray(img_data)
        cut_polygons=np.array(cut_polygons).reshape([-1, 4, 2])

        corpped=[]
        for corp_area in cut_polygons:
            rect=cv2.boundingRect(corp_area)
            x, y, w, h=rect
            corpped.append(img_data[y:y+h, x:x+w].copy())
        return corpped

    def command(self, command_name: str, param: Any, **kwargs) -> Any:
        if command_name=='crop':
            param=AssetRef.try_retrieve(param, self.context.assets)
            corpped=self.crop(
                param.get('img_data'),
                param.get('cut_polygons')
            )
            return ClassDict(corpped=corpped)
        else:
            raise ValueError(f'Unknown command: {command_name}. Only "crop" is acceptable.')
