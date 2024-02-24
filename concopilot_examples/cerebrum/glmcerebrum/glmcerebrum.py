# -*- coding: utf-8 -*-

import json

from typing import Optional

from concopilot.framework.plugin import PluginManager
from concopilot.framework.cerebrum import InteractParameter, InteractResponse, AbstractCerebrum
from concopilot.framework.resource.category.model import LLM
from concopilot.framework.message import Message
from concopilot.util.context import Asset
from concopilot.util.jsons import JsonEncoder


class GLMCerebrum(AbstractCerebrum):
    def __init__(self, config):
        super(GLMCerebrum, self).__init__(config)
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
        instruction_list=param.instructions.copy() if param.instructions else []

        if self._plugin_prompt is not None:
            instruction_list.insert(-1, self._plugin_prompt)

        if self.instruction_prompt():
            instruction_list.append(self.instruction_prompt())

        if param.assets is not None and len(param.assets)>0:
            instruction_list.append('Current AssetMeta list:\n\n```json\n'+json.dumps([Asset.get_meta(asset) for asset in param.assets], cls=JsonEncoder, ensure_ascii=False, indent=4)+'\n```')

        history=[]
        if len(instruction_list)>0:
            history.append({'role': 'system', 'content': '\n\n'.join(instruction_list)})
        if param.message_history is not None and len(param.message_history)>0:
            for msg in param.message_history:
                if msg.sender.role=='user':
                    role='user'
                elif msg.sender.role=='cerebrum':
                    role='assistant'
                elif msg.sender.role=='plugin':
                    role='observation'
                elif msg.sender.role:
                    role=msg.sender.role
                else:
                    role='system'
                content=msg.retrieve(self.msg_retrieval_mode)
                if not isinstance(content, str):
                    content=json.dumps(content, cls=JsonEncoder, ensure_ascii=False)
                history.append({'role': role, 'content': content})

        prompt_list=[]
        if param.content:
            prompt_list.append(param.content)

        if param.command:
            prompt_list.append(param.command)

        reply=self.model.inference({
            'prompt': '\n\n'.join(prompt_list),
            'history': history,
            'max_tokens': self.max_tokens,
            'require_token_len': param.require_token_len,
            'require_cost': param.require_cost
        }, **kwargs)

        return InteractResponse(**reply)
