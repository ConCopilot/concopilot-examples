# -*- coding: utf-8 -*-

import openai
import re
import time
import os
import logging

from typing import Dict, Union

from colorama import Fore
from concopilot.framework.resource.category import LLM
from concopilot.util import ClassDict


logger=logging.getLogger(__file__)


class OpenAILLM(LLM):
    def __init__(self, config):
        super(OpenAILLM, self).__init__(config)
        self.api_type: str = self.config.config.api_type if self.config.config.api_type else 'openai'
        self.base_url: str = self.config.config.base_url
        self.api_version: str = self.config.config.api_version
        self.api_key: str = self.config.config.api_key
        self.organization: str = self.config.config.organization
        self.api_key_secret_name: str = self.config.config.api_key_secret_name
        self.engine: str = self.config.config.engine
        self.model: str = self.config.config.model
        self.deployment_id: str = self.config.config.deployment_id
        self.base_model_name: str = self.config.config.base_model_name
        self.base_model_name=self.base_model_name[:-3] if self.base_model_name.endswith('-v2') else self.base_model_name
        self.num_retries: int = self.config.config.num_retries if self.config.config.num_retries is not None else 10

        self.client: Union[openai.OpenAI, openai.AzureOpenAI] = None

    def inference(self, param: Union[LLM.LLMParameter, Dict], **kwargs) -> LLM.LLMResponse:
        param=dict(param)
        if kwargs is not None:
            param.update(kwargs)
        self._check_param(param)

        require_token_len=param.pop('require_token_len') if 'require_token_len' in param else False
        require_cost=param.pop('require_cost') if 'require_cost' in param else False

        if self.config.config.force_chat and 'prompt' in param and param['prompt'] is not None and len(param['prompt'])>0:
            if 'messages' not in param:
                param['messages']=[]
            param['messages'].append({
                'role': 'user',
                'content': param.pop('prompt')
            })

        for attempt in range(self.num_retries):
            backoff=5*(attempt+2)
            try:
                if 'messages' in param:
                    completion=self.client.chat.completions.create(**param)
                    message=completion.choices[0].message
                    response=LLM.LLMResponse(content=message.content, role=message.role)
                    if message.function_call:
                        response.calls=[
                            ClassDict(
                                name=message.function_call.name,
                                arguments=message.function_call.arguments
                            )
                        ]
                elif 'prompt' in param:
                    completion=self.client.completions.create(**param)
                    response=LLM.LLMResponse(content=completion.choices[0].text)
                else:
                    raise ValueError('Either a "messages" or a "prompt" field must exist in param.')
                if require_token_len:
                    response.input_token_len=completion.usage.prompt_tokens
                    response.output_token_len=completion.usage.completion_tokens
                if require_cost:
                    response.cost=self.get_cost(completion.usage.prompt_tokens, completion.usage.completion_tokens)
                return response
            except openai.RateLimitError as e:
                pattern=re.compile(r'Please retry after (\d+) seconds')
                if result:=pattern.search(str(e)):
                    backoff=int(result.group(1))+1
                logger.debug(f'{Fore.RED}Error: Reached rate limit, passing...{Fore.RESET}')
            except openai.APIStatusError as e:
                if e.status_code!=502:
                    raise
                if attempt==self.num_retries-1:
                    raise
            except openai.APIError as e:
                if attempt==self.num_retries-1:
                    raise
            except ValueError:
                raise
            logger.debug(f'{Fore.RED}Error: API Bad gateway. Waiting {backoff} seconds...{Fore.RESET}')
            time.sleep(backoff)
        raise RuntimeError(f'Failed to get response after {self.num_retries} retries')

    def _check_param(self, param: Dict):
        param['model']=self.model
        param['stream']=False
        if 'temperature' not in param and self.config.config.temperature is not None:
            param['temperature']=self.config.config.temperature
        if 'top_p' not in param and self.config.config.top_p is not None:
            param['top_p']=self.config.config.top_p
        if 'n' not in param and self.config.config.n is not None:
            param['n']=self.config.config.n
        if 'max_tokens' not in param and self.config.config.max_tokens is not None:
            param['max_tokens']=self.config.config.max_tokens
        if 'presence_penalty' not in param and self.config.config.presence_penalty is not None:
            param['presence_penalty']=self.config.config.presence_penalty
        if 'frequency_penalty' not in param and self.config.config.frequency_penalty is not None:
            param['frequency_penalty']=self.config.config.frequency_penalty
        if 'logit_bias' not in param and self.config.config.logit_bias is not None:
            param['logit_bias']=self.config.config.logit_bias
        if 'suffix' not in param and self.config.config.suffix is not None:
            param['suffix']=self.config.config.suffix
        if 'logprobs' not in param and self.config.config.logprobs is not None:
            param['logprobs']=self.config.config.logprobs
        if 'echo' not in param and self.config.config.echo is not None:
            param['echo']=self.config.config.echo
        if 'stop' not in param and self.config.config.stop is not None:
            param['stop']=self.config.config.stop
        if 'best_of' not in param and self.config.config.best_of is not None:
            param['best_of']=self.config.config.best_of

    def initialize(self):
        if self.api_key_secret_name:
            self.api_key=os.getenv(self.api_key_secret_name, self.api_key)

        if self.api_type.lower()=='openai':
            self.client=openai.OpenAI(
                base_url=self.base_url,
                organization=self.organization,
                api_key=self.api_key
            )
        elif self.api_type.lower()=='azure':
            self.client=openai.AzureOpenAI(
                azure_endpoint=self.base_url,
                api_version=self.api_version,
                api_key=self.api_key
            )
        else:
            raise ValueError('Unknown `api_type`, only "openai" and "azure" are allowed.')

    def finalize(self):
        if self.client:
            self.client.close()

    def get_cost(self, prompt_tokens, completion_tokens):
        model_cost=COSTS.get(self.base_model_name)
        if model_cost is not None:
            return (prompt_tokens*COSTS[self.base_model_name]['prompt']+completion_tokens*COSTS[self.base_model_name]['completion'])/1000
        else:
            return 0


COSTS={
    'gpt-3.5-turbo': {'prompt': 0.002, 'completion': 0.002},
    'gpt-3.5-turbo-0301': {'prompt': 0.002, 'completion': 0.002},
    'gpt-4-0314': {'prompt': 0.03, 'completion': 0.06},
    'gpt-4-32k': {'prompt': 0.06, 'completion': 0.12},
    'gpt-4-32k-0314': {'prompt': 0.06, 'completion': 0.12},
    'text-embedding-ada-002': {'prompt': 0.0004, 'completion': 0.0},
    'text-davinci-003': {'prompt': 0.02, 'completion': 0.02},
}
