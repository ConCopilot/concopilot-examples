# -*- coding: utf-8 -*-

import os
import re
import json
import uuid
import yaml
import zipfile
import logging
import numpy as np
from PIL import Image

from typing import Dict, Optional

from concopilot.framework.interface import UserInterface
from concopilot.framework.message import Message
from concopilot.framework.asset import AssetRef
from concopilot.framework.asset import asset_regex
from concopilot.util.jsons import JsonEncoder
from concopilot.util.yamls import YamlDumper
from concopilot.util import ClassDict
from ....util import images


logger=logging.getLogger(__file__)


class WebChatUserInterface(UserInterface):
    def __init__(self, config: Dict):
        super(WebChatUserInterface, self).__init__(config)
        self._role_mapping=self.config.config.role_mapping
        self._dist_path=self.config.config.dist_path if self.config.config.dist_path else self.config_file_path('dist')
        self._websocket=None
        self._msg_cache=[]
        self._msg=None

        if not os.path.isdir(self._dist_path) or not os.listdir(self._dist_path):
            with zipfile.ZipFile(self.config_file_path('dist.zip'), 'r') as zip_ref:
                zip_ref.extractall(self._dist_path)

        web_config=ClassDict(
            websocket_host=self.config.config.websocket_host,
            websocket_port=self.config.config.websocket_port,
            slider_params=self.config.config.slider_params,
            role_mapping=self.config.config.role_mapping,
            options=self.config.config.options
        )
        with open(os.path.join(self._dist_path, 'config.yaml'), 'w', encoding='utf8') as f:
            yaml.dump(web_config, f, Dumper=YamlDumper)

    @property
    def websocket(self):
        if self._websocket is None:
            self._websocket=self.resources[0]
        return self._websocket

    def _recv_msg(self, timeout):
        try:
            msg=self.websocket.recv(timeout=timeout)
        except TimeoutError:
            msg=None
        if msg is not None:
            msg=Message(**json.loads(msg))
            if isinstance(msg.content, str):
                msg.content=msg.content.strip()
        return msg

    def next_msg(self, timeout):
        if self._msg is None:
            if len(self._msg_cache)>0:
                self._msg=self._msg_cache.pop(0)
            else:
                self._msg=self._recv_msg(timeout=timeout)
        return self._msg

    def send_msg_user(self, msg: Message):
        if msg.sender and msg.sender.role=='interactor' and msg.content_type=='command' and msg.content and msg.content.command=='retrieve_history' and msg.content.response:
            histories=msg.content.response.histories
            msg.content.response.histories=[]
            self._send_msg_user_single(msg)
            for m in histories:
                self._send_msg_user_single(m)
        else:
            self._send_msg_user_single(msg)

    def _send_msg_user_single(self, msg: Message):
        if not msg.id and self.config.config.add_msg_id:
            msg.id=uuid.uuid4()
        if msg.content_type and ((content_type:=msg.content_type.strip()).startswith('image/') or content_type=='image' or content_type=='img'):
            msg.content=WebChatUserInterface._convert_img_src(AssetRef.try_retrieve(msg.content, self.context.assets))
            msg=json.dumps(msg, cls=JsonEncoder, ensure_ascii=False)
        else:
            msg=json.dumps(msg, cls=JsonEncoder, ensure_ascii=False)
            msg='```'.join([(self._check_asset_refs(x) if idx%2==0 else x) for idx, x in enumerate(msg.split('```'))])
        self.websocket.send(msg)

    def on_msg_user(self, msg: Message) -> Optional[Message]:
        if not msg.thrd_id:
            msg=Message(**msg)
            msg.thrd_id=str(uuid.uuid4())
        thrd_id=msg.thrd_id
        self.send_msg_user(msg)
        while msg:=self._recv_msg(timeout=None):
            if msg.thrd_id==thrd_id:
                return msg
            else:
                self._msg_cache.append(msg)

    def has_user_msg(self) -> bool:
        return self.next_msg(timeout=0) is not None

    def get_user_msg(self) -> Optional[Message]:
        if (msg:=self.next_msg(timeout=0)) is not None:
            self._msg=None
        return msg

    def wait_user_msg(self) -> Optional[Message]:
        msg=self.next_msg(timeout=None)
        self._msg=None
        return msg

    def _check_asset_refs(self, inputs: str):
        inputs=asset_regex.asset_ref_img_markdown_embedding_pattern.sub(self._convert_from_asset_ref_img_markdown, inputs)
        inputs=asset_regex.asset_ref_common_embedding_pattern.sub(self._convert_from_asset_ref, inputs)
        return inputs

    @staticmethod
    def _try_convert_asset_ref(data: str):
        if data.startswith('{') and data.endswith('}'):
            data=json.loads(data)
        return AssetRef.try_convert(data)

    @staticmethod
    def _convert_img_src(img_src):
        if isinstance(img_src, Image.Image):
            return images.pillow_image_to_data_url(img_src)
        elif isinstance(img_src, np.ndarray):
            return images.ndarray_image_to_data_url(img_src)
        else:
            return str(img_src)

    def _convert_from_asset_ref_img_markdown(self, match_obj: re.Match):
        try:
            img_src=match_obj.group(2)
            if asset_ref:=WebChatUserInterface._try_convert_asset_ref(img_src):
                img_src=asset_ref.retrieve(self.context.assets)
                img_src=WebChatUserInterface._convert_img_src(img_src)
                return f'{match_obj.group(1)}({img_src})'
            else:
                return match_obj.group(0)
        except Exception as e:
            logger.error('AssetRef error during converting to a Markdown Image.', exc_info=e)
            return match_obj.group(0)

    def _convert_from_asset_ref(self, match_obj: re.Match):
        try:
            data=match_obj.group(1)
            if asset_ref:=WebChatUserInterface._try_convert_asset_ref(data):
                data=asset_ref.retrieve(self.context.assets)
                return str(data)
            else:
                return match_obj.group(0)
        except Exception as e:
            logger.error('AssetRef error during converting.', exc_info=e)
            return match_obj.group(0)
