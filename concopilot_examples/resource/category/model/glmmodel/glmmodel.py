# -*- coding: utf-8 -*-

import pathlib
import huggingface_hub
import modelscope
import logging
import os
import shutil

from typing import Dict, Union

from transformers import AutoTokenizer, AutoModel
from concopilot.framework.resource.category import LLM
from concopilot.package.config import Settings
from concopilot.util import ClassDict


logger=logging.getLogger(__file__)


settings=Settings()


class GLMModel(LLM):
    def __init__(self, config):
        super(GLMModel, self).__init__(config)
        self.model_repo: ClassDict = self.config.config.model_repo

        if self.model_repo.huggingface and self.model_repo.huggingface.repo_dir:
            if not os.path.isabs(self.model_repo.huggingface.repo_dir):
                self.model_repo.huggingface.repo_dir=os.path.join(settings.working_directory, self.model_repo.huggingface.repo_dir)
            self.huggingface_repo_dir=self.model_repo.huggingface.repo_dir
        else:
            self.huggingface_repo_dir=None

        if self.model_repo.modelscope and self.model_repo.modelscope.repo_dir:
            if not os.path.isabs(self.model_repo.modelscope.repo_dir):
                self.model_repo.modelscope.repo_dir=os.path.join(settings.working_directory, self.model_repo.modelscope.repo_dir)
            self.modelscope_repo_dir=self.model_repo.modelscope.repo_dir
        else:
            self.modelscope_repo_dir=None

        self.transformers: ClassDict = self.config.config.transformers if self.config.config.transformers else ClassDict()
        if self.transformers.auto_tokenizer is None:
            self.transformers.auto_tokenizer=ClassDict()
        if self.transformers.auto_model is None:
            self.transformers.auto_model=ClassDict()

        self.model = None
        self.tokenizer = None

    def inference(self, param: Union[LLM.LLMParameter, Dict], **kwargs) -> LLM.LLMResponse:
        param=dict(param)
        if kwargs is not None:
            param.update(kwargs)

        max_tokens=param.pop('max_tokens') if 'max_tokens' in param else 8192
        require_token_len=param.pop('require_token_len') if 'require_token_len' in param else False
        require_cost=param.pop('require_cost') if 'require_cost' in param else False

        reply, _=self.model.chat(
            tokenizer=self.tokenizer,
            query=param.pop('prompt'),
            history=param.pop('history'),
            max_length=max_tokens,
            **param
        )

        response=LLM.LLMResponse(
            content=reply
        )

        return response

    def initialize(self):
        def download_hf(download_dir):
            try:
                huggingface_hub.Repository(local_dir=download_dir, clone_from=self.model_repo.huggingface.repo_id)
            except Exception:
                shutil.rmtree(download_dir)
                raise

        def download_ms(download_dir):
            try:
                modelscope.snapshot_download(model_id=self.model_repo.modelscope.model_id, revision=self.model_repo.modelscope.revision, cache_dir=self.model_repo.modelscope.repo_dir)
            except Exception:
                shutil.rmtree(download_dir)
                raise

        local_dir=self.model_repo.local.repo_dir if self.model_repo.local else None
        if not local_dir or not os.path.isdir(local_dir):
            local_dir_hf=pathlib.Path(self.huggingface_repo_dir).joinpath(self.model_repo.huggingface.repo_id) if self.huggingface_repo_dir else None
            local_dir_ms=pathlib.Path(self.modelscope_repo_dir).joinpath(self.model_repo.modelscope.model_id) if self.modelscope_repo_dir else None
            if not local_dir_hf and not local_dir_ms:
                raise ValueError('No model repository found, must provide at lease one or local pre-downloaded path, HuggingFace repository ID, or ModelScope model ID.')
            elif local_dir_hf and local_dir_ms:
                if not os.path.isdir(local_dir_hf) and not os.path.isdir(local_dir_ms):
                    try:
                        download_hf(local_dir_hf)
                        local_dir=local_dir_hf
                    except Exception as e:
                        logger.error(f'clone {self.model_repo.huggingface.repo_id} from HuggingFace failed! Will try ModelScope', exc_info=e)
                        download_ms(local_dir_ms)
                        local_dir=local_dir_ms
                elif os.path.isdir(local_dir_hf):
                    local_dir=local_dir_hf
                else:
                    local_dir=local_dir_ms
            elif local_dir_hf:
                if not os.path.isdir(local_dir_hf):
                    download_hf(local_dir_hf)
                local_dir=local_dir_hf
            else:
                if not os.path.isdir(local_dir_ms):
                    download_ms(local_dir_ms)
                local_dir=local_dir_ms

        logger.info(f'Loading model from "{local_dir}"')
        self.tokenizer=AutoTokenizer.from_pretrained(local_dir, **self.transformers.auto_tokenizer)
        self.model=AutoModel.from_pretrained(local_dir, **self.transformers.auto_model)
        self.model=self.model.eval()

    def finalize(self):
        pass
