# -*- coding: utf-8 -*-

import yaml
import uuid

from typing import Dict

from concopilot.framework.plugin import Plugin, PluginPromptGenerator
from concopilot.util.yamls import YamlDumper


class YamlPluginPromptGenerator(PluginPromptGenerator):
    def __init__(self, config: Dict):
        super(YamlPluginPromptGenerator, self).__init__(config)

    def generate_prompt(self, plugin: Plugin) -> str:
        config={
            'id': plugin.id,
            'name': plugin.name,
            'info': plugin.config.info,
            'commands': plugin.config.commands
        }
        config_str=yaml.dump(config, Dumper=YamlDumper)
        return '```yaml\n'+config_str+'\n```'
