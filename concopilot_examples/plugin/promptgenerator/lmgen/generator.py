# -*- coding: utf-8 -*-

import yaml

from typing import Dict

from concopilot.framework.plugin import Plugin, PluginPromptGenerator
from concopilot.framework.resource.category import LLM
from concopilot.util.yamls import YamlDumper


class LanguageModelPluginPromptGenerator(PluginPromptGenerator):
    def __init__(self, config: Dict):
        super(LanguageModelPluginPromptGenerator, self).__init__(config)
        self._model: LLM = None
        with open(self.config_file_path(self.config.config.instruction_file), encoding='utf8') as file:
            self.instruction: str = file.read()

    @property
    def model(self) -> LLM:
        if self._model is None:
            self._model=self.resources[0]
            assert isinstance(self._model, LLM)
        return self._model

    def generate_prompt(self, plugin: Plugin) -> str:
        config={
            'id': plugin.id,
            'name': plugin.name,
            'info': plugin.config.info,
            'commands': plugin.config.commands
        }
        config_str=yaml.dump(config, Dumper=YamlDumper)
        response=self.model.inference(param={
            'prompt': '\n\n'.join([self.instruction, config_str, 'Begin the summarize:\n'])
        })
        summary=response['content']
        return '\n\n'.join(['Summary:', summary, 'Detail:', '```yaml\n'+config_str+'\n```'])
