# -*- coding: utf-8 -*-

import zhipuai
import os

from typing import Dict, Union

from concopilot.framework.resource.category import LLM
from concopilot.util import ClassDict


class ZhipuAILLM(LLM):
    def __init__(self, config):
        super(ZhipuAILLM, self).__init__(config)
        self.base_url: str = self.config.config.base_url
        self.base_url_secret_name: str = self.config.config.base_url_secret_name
        self.api_key: str = self.config.config.api_key
        self.api_key_secret_name: str = self.config.config.api_key_secret_name
        self.timeout: float = self.config.config.timeout
        self.max_retries: int = self.config.config.max_retries
        self.custom_headers: ClassDict[str, str] = self.config.config.custom_headers

        self.model: str = self.config.config.model
        self.default_chat_param: ClassDict = self.config.config.default_chat_param if self.config.config.default_chat_param is not None else ClassDict()

        self.client: zhipuai.ZhipuAI = None

    def inference(self, param: Union[LLM.LLMParameter, Dict], **kwargs) -> LLM.LLMResponse:
        param=dict(param)
        if kwargs is not None:
            param.update(kwargs)
        param['model']=self.model
        param.update({k: v for k, v in self.default_chat_param.items() if k not in param})

        require_token_len=param.pop('require_token_len') if 'require_token_len' in param else False
        require_cost=param.pop('require_cost') if 'require_cost' in param else False

        if 'prompt' in param and param['prompt'] is not None and len(param['prompt'])>0:
            if 'messages' not in param:
                param['messages']=[]
            param['messages'].append({
                'role': 'user',
                'content': param.pop('prompt')
            })

        completion=self.client.chat.completions.create(**param)
        message=completion.choices[0].message
        response=LLM.LLMResponse(content=message.content, role=message.role)
        if message.tool_calls:
            response.calls=[
                ClassDict(
                    name=call.function.name,
                    arguments=call.function.arguments,
                    id=call.id,
                    type=call.type
                )
                for call in message.tool_calls
            ]
        if require_token_len:
            response.input_token_len=completion.usage.prompt_tokens
            response.output_token_len=completion.usage.completion_tokens
        if require_cost:
            response.cost=self.get_cost(completion.usage.prompt_tokens, completion.usage.completion_tokens)
        return response

    def initialize(self):
        if self.base_url_secret_name:
            self.base_url=os.getenv(self.base_url_secret_name, self.base_url)
        if self.api_key_secret_name:
            self.api_key=os.getenv(self.api_key_secret_name, self.api_key)

        self.client=zhipuai.ZhipuAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=self.max_retries,
            custom_headers=self.custom_headers if self.custom_headers else None
        )

    def finalize(self):
        if self.client:
            self.client.close()

    def get_cost(self, prompt_tokens, completion_tokens):
        model_cost=COSTS.get(self.model)
        if model_cost is not None:
            return (prompt_tokens*COSTS[self.model]['prompt']+completion_tokens*COSTS[self.model]['completion'])/1000
        else:
            return 0


COSTS={
    'glm-4': {'prompt': 0.1, 'completion': 0.1},
    'glm-4v': {'prompt': 0.1, 'completion': 0.1},
    'glm3-turbo': {'prompt': 0.005, 'completion': 0.005}
}
