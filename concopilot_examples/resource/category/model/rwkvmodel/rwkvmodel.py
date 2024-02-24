# -*- coding: utf-8 -*-

import pathlib
import huggingface_hub
import modelscope
import logging
import validators
import requests
import os

from typing import Dict, List, Union

from modelscope.hub.file_download import model_file_download, get_cache_dir
from rwkv.model import RWKV
from rwkv.utils import PIPELINE
from concopilot.framework.resource.category import LLM
from concopilot.package.config import Settings
from concopilot.util import ClassDict


logger=logging.getLogger(__file__)


settings=Settings()


class RWKVModel(LLM):
    def __init__(self, config):
        super(RWKVModel, self).__init__(config)
        self.model_repo: ClassDict = self.config.config.model_repo

        if self.model_repo.huggingface:
            if not self.model_repo.huggingface.cache_dir:
                self.model_repo.huggingface.cache_dir=huggingface_hub.constants.HF_HUB_CACHE
            if not os.path.isabs(self.model_repo.huggingface.cache_dir):
                self.model_repo.huggingface.cache_dir=str(pathlib.Path(settings.working_directory).joinpath(self.model_repo.huggingface.cache_dir))
            self.huggingface_cache_dir=self.model_repo.huggingface.cache_dir

            if not self.model_repo.huggingface.local_dir and self.model_repo.huggingface.local_root:
                self.model_repo.huggingface.local_dir=str(pathlib.Path(self.model_repo.huggingface.pop('local_root')).joinpath(self.model_repo.huggingface.repo_id))
            if self.model_repo.huggingface.local_dir:
                if not os.path.isabs(self.model_repo.huggingface.local_dir):
                    self.model_repo.huggingface.local_dir=str(pathlib.Path(settings.working_directory).joinpath(self.model_repo.huggingface.local_dir))
                self.huggingface_local_dir=self.model_repo.huggingface.local_dir
            else:
                self.huggingface_local_dir=None
        else:
            self.huggingface_cache_dir=None
            self.huggingface_local_dir=None

        if self.model_repo.modelscope:
            if not self.model_repo.modelscope.cache_dir:
                self.model_repo.modelscope.cache_dir=get_cache_dir()
            if not os.path.isabs(self.model_repo.modelscope.cache_dir):
                self.model_repo.modelscope.cache_dir=str(pathlib.Path(settings.working_directory).joinpath(self.model_repo.modelscope.cache_dir))
            self.modelscope_cache_dir=self.model_repo.modelscope.cache_dir
        else:
            self.modelscope_cache_dir=None

        self.rwkv_strategy: str = self.config.config.rwkv_strategy
        self.tokenizer_file: str = self.config.config.tokenizer_file
        self.tokenizer_url: str = self.config.config.tokenizer_url
        self.tokenizer_force_update: bool = self.config.config.tokenizer_force_update
        self.pad_tokens: List[int] = self.config.config.pad_tokens

        self.model: RWKV = None
        self.pipeline: PIPELINE = None

    def inference(self, param: Union[LLM.LLMParameter, Dict], **kwargs) -> LLM.LLMResponse:
        param=dict(param)
        if kwargs is not None:
            param.update(kwargs)

        max_tokens=(param['max_tokens'] if 'max_tokens' in param else None) or self.config.config.max_tokens or 1024
        repetition_penalty=param['repetition_penalty'] if 'repetition_penalty' in param else self.config.config.repetition_penalty
        temperature=param['temperature'] if 'temperature' in param else self.config.config.temperature
        top_p=param['top_p'] if 'top_p' in param else self.config.config.top_p
        top_k=param['top_k'] if 'top_k' in param else self.config.config.top_k

        input_tokens=self.pad_tokens+self.pipeline.encode(param['prompt'])
        output_tokens=[]
        occurrence={}
        state=None
        token=None
        for i in range(max_tokens):
            tokens=input_tokens if i==0 else [token]

            logits, state=self.pipeline.model.forward(tokens, state)
            for n in occurrence:
                logits[n]-=(repetition_penalty+occurrence[n]*repetition_penalty)  # repetition penalty

            token=self.pipeline.sample_logits(logits, temperature=temperature, top_p=top_p, top_k=top_k)  # topp = 0 --> greedy decoding
            if token==0:
                break  # exit when 'endoftext'

            output_tokens+=[token]
            occurrence[token]=occurrence[token]+1 if token in occurrence else 1

        response=LLM.LLMResponse(
            content=self.pipeline.decode(output_tokens)
        )
        if param.get('require_token_len'):
            response.input_token_len=len(input_tokens)
            response.output_token_len=len(output_tokens)
        if param.get('require_cost'):
            response.cost=0
        return response

    def initialize(self):
        def download_hf(local_files_only):
            kwargs={k: v for k, v in self.model_repo.huggingface.items() if k!='local_files_only' and k!='local_root'}
            return huggingface_hub.hf_hub_download(local_files_only=local_files_only, **kwargs)

        def download_ms(local_files_only):
            kwargs={k: v for k, v in self.model_repo.modelscope.items() if k!='local_files_only'}
            return model_file_download(local_files_only=local_files_only, **kwargs)

        local_path=self.model_repo.local.model_path if self.model_repo.local else None
        if not local_path or not os.path.isdir(local_path):
            try:
                local_dir_hf=download_hf(local_files_only=True) if self.huggingface_cache_dir else None
            except Exception:
                local_dir_hf=None
            try:
                local_dir_ms=download_ms(local_files_only=True) if self.modelscope_cache_dir else None
            except Exception:
                local_dir_ms=None

            if not self.huggingface_cache_dir and not self.modelscope_cache_dir:
                raise ValueError('No model file found, must provide at lease one of local pre-downloaded path, HuggingFace repository ID and file, or ModelScope model ID and file.')
            elif not local_dir_hf and not local_dir_ms:
                try:
                    local_path=download_hf(local_files_only=False)
                except Exception as e:
                    logger.error(f'Download {self.model_repo.huggingface.repo_id}/{self.model_repo.huggingface.filename} from HuggingFace failed! Will try ModelScope', exc_info=e)
                    local_path=download_ms(local_files_only=False)
            elif local_dir_hf:
                local_path=local_dir_hf
            else:
                local_path=local_dir_ms

        tokenizer_file=self.config_file_path(self.tokenizer_file)
        if self.tokenizer_force_update or not os.path.isfile(tokenizer_file):
            if validators.url(self.tokenizer_url, simple_host=True):
                response=requests.get(self.tokenizer_url)
                if response.status_code==200:
                    with open(tokenizer_file, 'w', encoding='utf8') as file:
                        file.write(response.text)
                else:
                    raise requests.exceptions.RequestException(response.text)
            else:
                raise ValueError('No tokenizer_file found, and no valid tokenizer_url found.')

        self.model=RWKV(model=local_path, strategy=self.rwkv_strategy)
        self.pipeline=PIPELINE(self.model, tokenizer_file)

    def finalize(self):
        pass
