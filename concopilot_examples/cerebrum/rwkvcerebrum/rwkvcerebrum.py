# -*- coding: utf-8 -*-

import json

from typing import Optional

from concopilot.framework.plugin import PluginManager
from concopilot.framework.cerebrum import InteractParameter, InteractResponse, AbstractCerebrum
from concopilot.framework.resource.category.model import LLM
from concopilot.framework.message import Message
from concopilot.framework.asset import Asset
from concopilot.util.jsons import JsonEncoder


class RWKVCerebrum(AbstractCerebrum):
    def __init__(self, config):
        super(RWKVCerebrum, self).__init__(config)
        self._model: LLM = None
        self.max_tokens: int = self.config.config.max_tokens
        self.msg_retrieval_mode: Message.RetrievalMode = Message.RetrievalMode[self.config.config.msg_retrieval_mode.upper()]
        self._instruction_prompt: str = f'Make your response less than {self.max_tokens} tokens.' if (self.max_tokens is not None and self.max_tokens>0) else None
        self._plugin_prompt: str = None

    def setup_plugins(self, plugin_manager: PluginManager):
        if plugin_manager is not None and self.config.config.instruction_file:
            with open(self.config_file_path(self.config.config.instruction_file), encoding='utf8') as file:
                self._plugin_prompt=file.read().replace('{plugins}', plugin_manager.get_combined_prompt())

    def instruction_prompt(self) -> Optional[str]:
        return self._instruction_prompt

    @property
    def model(self) -> LLM:
        if self._model is None:
            self._model=self.resources[0]
            assert isinstance(self._model, LLM)
        return self._model

    def interact(self, param: InteractParameter, **kwargs) -> InteractResponse:
        prompt_list=param.instructions.copy() if param.instructions else []

        if self._plugin_prompt is not None:
            prompt_list.insert(-1, self._plugin_prompt)

        if self.instruction_prompt():
            prompt_list.append(self.instruction_prompt())

        if param.assets is not None and len(param.assets)>0:
            if self.config.config.flatten_asset_meta:
                asset_meta_list=[Asset.get_meta(asset).flatten(sep='/', keep_container_type=True) for asset in param.assets]
            else:
                asset_meta_list=[Asset.get_meta(asset) for asset in param.assets]
            prompt_list.append('Current AssetMeta list:\n\n```json\n'+json.dumps(asset_meta_list, cls=JsonEncoder, ensure_ascii=False, indent=4)+'\n```')

        if param.message_history is not None and len(param.message_history)>0:
            prompt_list.append('Below are interaction messages between you, plugins, and the user so far:')
            for msg in param.message_history:
                content=msg.retrieve(self.msg_retrieval_mode)
                if not isinstance(content, str):
                    content=json.dumps(content, cls=JsonEncoder, ensure_ascii=False)
                prompt_list.append(content)

        if param.content:
            prompt_list.append(param.content)

        if param.command:
            prompt_list.append(param.command)

        reply=self.model.inference({
            'prompt': '\n\n'.join(prompt_list),
            'max_tokens': self.max_tokens,
            'require_token_len': param.require_token_len,
            'require_cost': param.require_cost
        }, **kwargs)

        return InteractResponse(**reply)
