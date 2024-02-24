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
from concopilot.util.context import AssetRef
from concopilot.util.jsons import JsonEncoder
from concopilot.util.yamls import YamlDumper
from concopilot.util import ClassDict
from ....util import images


logger=logging.getLogger(__file__)


asset_ref_pattern_img=re.compile(r'(!\[.*])\((.*)\)')
asset_ref_pattern=re.compile(r'<\|(.*)\|>')


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
        msg=json.dumps(msg, cls=JsonEncoder, ensure_ascii=False)
        msg=self._check_asset_refs(msg)
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
        inputs=asset_ref_pattern_img.sub(self._convert_from_asset_ref_image, inputs)
        inputs=asset_ref_pattern.sub(self._convert_from_asset_ref, inputs)
        return inputs

    def _convert_from_asset_ref_image(self, match_obj: re.Match):
        try:
            img_src=match_obj.group(2).strip()
            if img_src.startswith('<|') and img_src.endswith('|>'):
                img_src=img_src[2:-2].strip()

            if img_src.startswith('asset://'):
                img_src=AssetRef.try_retrieve(img_src, self.context.assets)
            elif img_src.startswith('{') and img_src.endswith('}'):
                img_src=json.loads(img_src)
                if asset_ref:=AssetRef.try_convert(img_src):
                    img_src=asset_ref.retrieve(self.context.assets)
                else:
                    return match_obj.group(0)
            else:
                return match_obj.group(0)

            if isinstance(img_src, Image.Image):
                img_src=images.pillow_image_to_data_url(img_src)
            elif isinstance(img_src, np.ndarray):
                img_src=images.ndarray_image_to_data_url(img_src)
            else:
                img_src=str(img_src)

            return f'{match_obj.group(1)}({img_src})'
        except Exception as e:
            logger.error('AssetRef error during converting to a Markdown Image.', exc_info=e)
            return match_obj.group(0)

    def _convert_from_asset_ref(self, match_obj: re.Match):
        try:
            data=match_obj.group(1).strip()
            if data.startswith('asset://'):
                data=AssetRef.try_retrieve(data, self.context.assets)
            elif data.startswith('{') and data.endswith('}'):
                data=json.loads(data)
                if asset_ref:=AssetRef.try_convert(data):
                    data=asset_ref.retrieve(self.context.assets)
                else:
                    return match_obj.group(0)
            else:
                return match_obj.group(0)

            return str(data)
        except Exception as e:
            logger.error('AssetRef error during converting.', exc_info=e)
            return match_obj.group(0)
