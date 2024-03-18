# -*- coding: utf-8 -*-

import logging

from typing import Dict

from modelscope.pipelines import pipeline, Pipeline
from modelscope.utils.constant import Tasks
from concopilot.framework.resource.category import Model
from concopilot.util import ClassDict


logger=logging.getLogger(__file__)


def create_tasks_mapping(mapping):
    if mapping is None:
        mapping={}
    for attr in dir(Tasks):
        if not attr.startswith('__'):
            value=getattr(Tasks, attr)
            if isinstance(value, str):
                mapping[attr.lower().replace('-', '_')]=value
                mapping[value.lower().replace('-', '_')]=value
    return mapping


class ModelScopePipeline(Model):
    tasks_mapping={}

    def __init__(self, config):
        super(ModelScopePipeline, self).__init__(config)
        self.pipeline_params: ClassDict = self.config.config.pipeline_params
        self.inference_defaults: ClassDict = self.config.config.inference_defaults if self.config.config.inference_defaults else ClassDict()

        self.pipeline: Pipeline = None

    def inference(self, param: Dict, **kwargs) -> Dict:
        p=dict(self.inference_defaults)
        p.update(param)
        p.update(kwargs)
        model_input=p.pop('input')

        return ClassDict(result=self.pipeline(input=model_input, **p))

    def initialize(self):
        if len(ModelScopePipeline.tasks_mapping)==0:
            ModelScopePipeline.tasks_mapping=create_tasks_mapping(ModelScopePipeline.tasks_mapping)

        self.pipeline_params.task=ModelScopePipeline.tasks_mapping[self.pipeline_params.task.lower().replace('-', '_')]
        self.pipeline=pipeline(**self.pipeline_params)
        logger.info(f'ModelScope Pipeline initialized with task: `{self.pipeline_params.task}` and model: `{self.pipeline_params.model}`')

    def finalize(self):
        pass
