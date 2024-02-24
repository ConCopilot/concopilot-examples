# -*- coding: utf-8 -*-

import logging

from typing import Dict, List, Generator, Union, Any
from concopilot.framework.plugin import AbstractPlugin
from concopilot.framework.resource.category import Model
from concopilot.util.context import AssetRef
from concopilot.util import ClassDict


logger=logging.getLogger(__file__)


class ModelScopeOCRDetection(AbstractPlugin):
    def __init__(self, config: Dict):
        super(ModelScopeOCRDetection, self).__init__(config)

        self._model: Model = None

    @property
    def model(self) -> Model:
        if self._model is None:
            self._model=self.resources[0]
            assert isinstance(self._model, Model)
        return self._model

    def detect(
        self,
        img_data: Any,
        img_url: str,
        img_path: str,
        img_data_list: List[Any],
        img_url_list: List[str],
        img_path_list: List[str],
        **kwargs
    ) -> Union[Dict[str, Any], Generator]:
        inputs=[]
        if img_data:
            inputs.append(AssetRef.try_retrieve(img_data, self.context.assets))
        if img_url:
            inputs.append(img_url)
        if img_path:
            inputs.append(img_path)
        if img_data_list:
            for x in AssetRef.try_retrieve(img_data_list, self.context.assets):
                inputs.append(AssetRef.try_retrieve(x, self.context.assets))
        if img_url_list:
            for x in AssetRef.try_retrieve(img_url_list, self.context.assets):
                inputs.append(AssetRef.try_retrieve(x, self.context.assets))
        if img_path_list:
            for x in AssetRef.try_retrieve(img_path_list, self.context.assets):
                inputs.append(AssetRef.try_retrieve(x, self.context.assets))
        if len(inputs)<1:
            raise ValueError('None of the `img_data`, `img_url`, `img_path`, `img_data_list`, `img_url_list`, or `img_path_list` passed to the `detect_and_correct` method!')
        return self.model.inference({'input': inputs if len(inputs)>1 else inputs[0]}, **kwargs)['result']

    def command(self, command_name: str, param: Any, **kwargs) -> Any:
        if command_name=='detect':
            param=AssetRef.try_retrieve(param, self.context.assets)
            re=self.detect(
                param.get('img_data'),
                param.get('img_url'),
                param.get('img_path'),
                param.get('img_data_list'),
                param.get('img_url_list'),
                param.get('img_path_list')
            )
            return ClassDict(result_list=re) if isinstance(re, List) else ClassDict(result=re)
        else:
            raise ValueError(f'Unknown command: {command_name}. Only "detect" is acceptable.')
