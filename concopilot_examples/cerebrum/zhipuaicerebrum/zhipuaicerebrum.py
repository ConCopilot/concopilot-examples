# -*- coding: utf-8 -*-

import json
import logging

from typing import List, Dict, Tuple, Optional

from concopilot.framework.plugin import Plugin, PluginManager
from concopilot.framework.cerebrum import InteractParameter, InteractResponse, AbstractCerebrum
from concopilot.framework.resource.category.model import LLM
from concopilot.framework.message import Message
from concopilot.framework.asset import Asset
from concopilot.util import ClassDict
from concopilot.util.jsons import JsonEncoder


logger=logging.getLogger(__file__)


class ZhipuAICerebrum(AbstractCerebrum):
    def __init__(self, config):
        super(ZhipuAICerebrum, self).__init__(config)
        self._model: LLM = None
        self.max_tokens: int = self.config.config.max_tokens
        self.msg_retrieval_mode: Message.RetrievalMode = Message.RetrievalMode[self.config.config.msg_retrieval_mode.upper()]
        self.instruction_prompt_role: str = self.config.config.instruction_prompt_role if self.config.config.instruction_prompt_role else 'system'
        self._instruction_prompt: str = f'Make your response less than {self.max_tokens} tokens.' if (self.max_tokens is not None and self.max_tokens>0) else None
        self._plugin_prompt: str = None
        self._tools=[]
        self._tool_plugin_map: Dict[str, Tuple[str, str]] = {}
        self._tool_failed_plugins: Dict[str, Plugin] = {}

    def setup_plugins(self, plugin_manager: PluginManager):
        self._tools=[]
        self._tool_plugin_map={}
        self._tool_failed_plugins={}
        if plugin_manager is not None:
            if self.config.config.use_tool_call:
                for plugin in plugin_manager.plugins:
                    if not self.create_plugin_tool(plugin):
                        self._tool_failed_plugins[plugin.name]=plugin
                if len(self._tool_failed_plugins)>0 and self.config.config.instruction_file:
                    with open(self.config_file_path(self.config.config.instruction_file), encoding='utf8') as file:
                        self._plugin_prompt=file.read().replace('{plugins}', '\n\n'.join([plugin.prompt for plugin in self._tool_failed_plugins.values()])).strip()
            else:
                if self.config.config.instruction_file:
                    with open(self.config_file_path(self.config.config.instruction_file), encoding='utf8') as file:
                        self._plugin_prompt=file.read().replace('{plugins}', plugin_manager.get_combined_prompt()).strip()

    def instruction_prompt(self) -> Optional[str]:
        return self._instruction_prompt

    @property
    def model(self) -> LLM:
        if self._model is None:
            self._model=self.resources[0]
            assert isinstance(self._model, LLM)
        return self._model

    def interact(self, param: InteractParameter, **kwargs) -> InteractResponse:
        current_context=[]

        prompt='\n\n'.join(param.instructions) if param.instructions else None
        if self._plugin_prompt:
            prompt+='\n\n'.join(([prompt] if prompt else [])+[self._plugin_prompt])
        if prompt:
            current_context.append(ZhipuAICerebrum.create_chat_message(self.instruction_prompt_role, prompt))

        if self.instruction_prompt():
            current_context.append(ZhipuAICerebrum.create_chat_message(self.instruction_prompt_role, self.instruction_prompt()))

        if param.assets is not None and len(param.assets)>0:
            if self.config.config.flatten_asset_meta:
                asset_meta_list=[Asset.get_meta(asset).flatten(sep='/', keep_container_type=True) for asset in param.assets]
            else:
                asset_meta_list=[Asset.get_meta(asset) for asset in param.assets]
            current_context.append(ZhipuAICerebrum.create_chat_message(self.instruction_prompt_role, 'Current AssetMeta list:\n\n```json\n'+json.dumps(asset_meta_list, cls=JsonEncoder, ensure_ascii=False, indent=4)+'\n```'))

        if param.message_history is not None and len(param.message_history)>0:
            for msg in param.message_history:
                if msg.sender.role=='user':
                    role='user'
                elif msg.sender.role=='cerebrum':
                    role='assistant'
                elif msg.sender.role=='plugin':
                    if self.config.config.use_tool_call and msg.sender.name+'_'+msg.content.command in self._tool_plugin_map:
                        role='tool'
                    else:
                        role='system'
                elif msg.sender.role:
                    role=msg.sender.role
                else:
                    role='system'

                tool_calls=None
                tool_call_id=None
                if self.config.config.use_tool_call and role=='assistant' and msg.receiver.role=='plugin' and msg.content is not None and msg.receiver.name+'_'+msg.content.command in self._tool_plugin_map:
                    content=None
                    last_is_tool_calls=len(current_context)>0 and 'tool_calls' in current_context[-1]
                    tool_calls=current_context[-1]['tool_calls'] if last_is_tool_calls else []
                    tool_calls.append({
                        'id': msg.content.get('id'),
                        'type': msg.content.get('type'),
                        'function': {
                            'name': msg.receiver.name+'_'+msg.content.command,
                            'arguments': json.dumps({k: str(v) for k, v in msg.content.param.items()}, cls=JsonEncoder, ensure_ascii=False)
                        }
                    })
                    if last_is_tool_calls:
                        continue
                elif role=='tool':
                    content=msg.content.response if isinstance(msg.content.response, str) else json.dumps(msg.content.response, cls=JsonEncoder, ensure_ascii=False)
                    tool_call_id=msg.content.id
                else:
                    content=msg.retrieve(self.msg_retrieval_mode)
                    if not isinstance(content, str):
                        content=json.dumps(content, cls=JsonEncoder, ensure_ascii=False)

                current_context.append(ZhipuAICerebrum.create_chat_message(role, content, tool_calls, tool_call_id))

        if param.content:
            current_context.append(ZhipuAICerebrum.create_chat_message('user', param.content))

        if param.command:
            current_context.append(ZhipuAICerebrum.create_chat_message('user', param.command))

        inference_param={
            'messages': current_context,
            'max_tokens': self.max_tokens,
            'require_token_len': param.require_token_len,
            'require_cost': param.require_cost
        }
        if len(self._tools)>0:
            inference_param['tools']=self._tools
            inference_param['tool_choice']='auto'
        reply=self.model.inference(inference_param, **kwargs)
        reply.plugin_calls=self.get_plugin_call(reply.pop('calls', None))

        return InteractResponse(**reply)

    @staticmethod
    def create_chat_message(role, content, tool_calls: Dict = None, tool_call_id: str = None):
        msg={'role': role, 'content': content}
        if tool_calls is not None:
            msg['tool_calls']=tool_calls
        if tool_call_id is not None:
            msg['tool_call_id']=tool_call_id
        return msg

    def create_plugin_tool(self, plugin: Plugin) -> bool:
        flag=True
        for command in plugin.config.commands:
            try:
                tool=ClassDict()
                tool.type='function'
                tool.function=ClassDict()
                tool.function.name=plugin.name+'_'+command.command_name
                tool.function.description=plugin.config.info.description_for_model if plugin.config.info.description_for_model else plugin.config.info.description
                tool.function.parameters=ClassDict(
                    type='object',
                    properties=ClassDict(),
                    required=[]
                )
                if isinstance(command.parameter.type, Dict):
                    for name, detail in command.parameter.type.items():
                        tool.function.parameters.properties[name]=ClassDict(type=get_tool_call_data_type(detail.type))
                        if detail.description:
                            tool.function.parameters.properties[name].description=detail.description
                        if detail.enum:
                            tool.function.parameters.properties[name].enum=detail.enum
                        if detail.required:
                            tool.function.parameters.required.append(name)
                else:
                    raise ValueError('ZhipuAI tool call do not support non-mapping command parameters.')

                self._tools.append(tool)
                self._tool_plugin_map[tool.function.name]=(plugin.name, command.command_name)
            except Exception as e:
                flag=False
                logger.warning(f'Converting plugin command to tool call failed. Plugin `{plugin.name}`, command `{command.command_name}`, will use prompt instead.', exc_info=e)

        return flag

    def get_plugin_call(self, calls: List[Dict]) -> Optional[List[InteractResponse.PluginCall]]:
        if calls is not None:
            plugin_calls=[]
            for call in calls:
                plugin_name, command=self._tool_plugin_map[call['name']]
                param=ClassDict.convert(json.loads(call['arguments']))
                plugin_calls.append(InteractResponse.PluginCall(
                    plugin_name=plugin_name,
                    command=command,
                    param=param,
                    id=call.get('id'),
                    type=call.get('type')
                ))
            return plugin_calls
        else:
            return None


def get_tool_call_data_type(param_type):
    if isinstance(param_type, str) and ((param_type:=param_type.lower()) in TYPES):
        return TYPES[param_type]
    else:
        raise ValueError(f'Cannot convert plugin parameter type `{param_type}` to ZhipuAI tool call type.')


TYPES={
    'integer': 'string',
    'int': 'string',
    'float': 'string',
    'boolean': 'string',
    'bool': 'string',
    'string': 'string',
    'str': 'string'
}
