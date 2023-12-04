# -*- coding: utf-8 -*-

import os
import json
import yaml
import zipfile

from typing import Dict, Optional

from concopilot.framework.interface import UserInterface
from concopilot.framework.message import Message
from concopilot.util.jsons import JsonEncoder
from concopilot.util import ClassDict


class YamlDumper(yaml.SafeDumper):
    pass


YamlDumper.add_multi_representer(dict, YamlDumper.represent_dict)


class WebChatUserInterface(UserInterface):
    def __init__(self, config: Dict):
        super(WebChatUserInterface, self).__init__(config)
        self._role_mapping=self.config.config.role_mapping
        self._dist_path=self.config.config.dist_path if self.config.config.dist_path else self.config_file_path('dist')
        self._websocket=None
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
        with open(os.path.join(self._dist_path, 'config.yaml'), 'w') as f:
            yaml.dump(web_config, f, Dumper=YamlDumper)

    @property
    def websocket(self):
        if self._websocket is None:
            self._websocket=self.resources[0]
        return self._websocket

    def next_msg(self, timeout):
        if self._msg is None:
            self._msg=self.websocket.recv(timeout=timeout)
            if self._msg is not None:
                self._msg=Message(**json.loads(self._msg))
                if isinstance(self._msg.content.text, str):
                    self._msg.content.text=self._msg.content.text.strip()
        return self._msg

    def send_msg_user(self, msg: Message):
        self.websocket.send(json.dumps(msg, cls=JsonEncoder, ensure_ascii=False))

    def has_user_msg(self) -> bool:
        return self.next_msg(timeout=0) is not None

    def get_user_msg(self) -> Optional[Message]:
        if msg:=self.next_msg(timeout=0) is not None:
            self._msg=None
        return msg

    def wait_user_msg(self) -> Optional[Message]:
        msg=self.next_msg(timeout=None)
        self._msg=None
        return msg
