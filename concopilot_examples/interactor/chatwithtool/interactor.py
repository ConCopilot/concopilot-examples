# -*- coding: utf-8 -*-

import json
import logging

from typing import Dict, List, Optional, Any

from concopilot.framework.plugin import PluginManager
from concopilot.framework.interactor import BasicInteractor
from concopilot.framework.resource import ResourceManager
from concopilot.framework.cerebrum import InteractParameter, Cerebrum
from concopilot.framework.message import Message
from concopilot.framework.message.manager import MessageManager
from concopilot.framework.asset import Asset, AssetRef
from concopilot.framework.identity import Identity
from concopilot.util.jsons import JsonEncoder
from concopilot.util import ClassDict
from concopilot import Settings


settings=Settings()
logger=logging.getLogger(__file__)


class ChatWithToolInteractor(BasicInteractor):
    def __init__(
        self,
        config: Dict,
        resource_manager: ResourceManager,
        cerebrum: Cerebrum,
        plugin_manager: PluginManager,
        message_manager: MessageManager
    ):
        super(ChatWithToolInteractor, self).__init__(
            config,
            resource_manager,
            cerebrum,
            plugin_manager,
            message_manager
        )
        self.persist_history_and_asset: bool = self.config.config.persist_history_and_asset
        self.message_history_key: str = self.config.config.message_history_key
        self.message_history_start_key: str = self.config.config.message_history_key+'_start'
        self.message_summary_key: str = self.config.config.message_summary_key
        self.assets_key: str = self.config.config.assets_key
        self.hello_msg_content: str = self.config.config.hello_msg_content
        self.summarize_token_len: Optional[int] = self.config.config.summarize_token_len
        self.instructions: List[str] = []
        self.verbose: bool = self.config.config.verbose
        self.wait_user_comment: bool = self.config.config.wait_user_comment
        self.exit_tokens: set[str] = set(self.config.config.exit_tokens)

        self.llm_param={}
        self.message_history: List[Message] = []
        self.message_history_start: int = 0

        self._thrd_id=None

    def setup_prompts(self):
        super(ChatWithToolInteractor, self).setup_prompts()
        if self.config.config.instruction_file:
            with open(self.config_file_path(self.config.config.instruction_file), encoding='utf8') as file:
                instruction=file.read()
            instruction=instruction\
                .replace('{ai_name}', self.cerebrum.name)\
                .replace('{ai_role}', self.cerebrum.role)\
                .replace('{ai_id}', str(self.cerebrum.id))

            instruction=instruction.replace('{plugins}', self.plugin_manager.get_combined_prompt())

            self.instructions.append(instruction)

    def interact_loop(self):
        if self.persist_history_and_asset:
            self.message_history: List[Message] = self.context.storage.get_or_default(self.message_history_key, [])
            self.message_history_start: int = self.context.storage.get_or_default(self.message_history_start_key, 0)
            self.context.assets[self.message_summary_key]=Asset(
                asset_type='summary',
                asset_id=self.message_summary_key,
                name='message summary',
                description='The summary of interaction messages between you, plugins, and the user. This is for reminding you with events from your past.',
                content_type='text/plain',
                content=self.context.storage.get_or_default(self.message_summary_key, '')
            )
            self.context.assets.update(self.context.storage.get_or_default(self.assets_key, {}))

        if len(self.message_history)>0:
            msg_list=[]
            for i in range(-1, -len(self.message_history)-1, -1):
                if self.message_history[i].sender.role!='cerebrum':
                    msg_list=self.message_history[i+1:]
                    break
            if len(msg_list)==0:
                msg_list=self._interact_with_cerebrum()
        else:
            msg=Message(
                sender=Identity(role='cerebrum', name=self.cerebrum.name),
                receiver=Identity(role='user'),
                content_type='text/plain',
                content=self.hello_msg_content,
                time=settings.current_time()
            )
            self.message_history.append(msg)
            self._check_and_send_msg_to_user(msg)
            if not self._wait_user_msg():
                return
            msg_list=self._interact_with_cerebrum()

        self.status=BasicInteractor.Status.RUNNING
        while self.status==BasicInteractor.Status.RUNNING:
            try:
                has_user_msg=False
                for msg in msg_list:
                    try:
                        self._check_and_send_msg_to_user(msg)
                        if msg.receiver is None:
                            raise ValueError(f'A `receiver` section is required in message `{json.dumps(msg, cls=JsonEncoder, ensure_ascii=False, indent=2)}`!')
                        if msg.receiver.role=='cerebrum':
                            pass
                        elif msg.receiver.role=='user':
                            has_user_msg=True
                            pass
                        elif msg.receiver.role=='plugin':
                            plugin=self.plugin_manager.get_plugin(name=msg.receiver.name)
                            if plugin is None:
                                raise ValueError(f'No such plugin with the name: {msg.receiver.name}.')
                            msg=plugin.on_msg(msg)
                            msg=self._check_msg_serializable(msg)
                            self.message_history.append(msg)
                            self._check_and_send_msg_to_user(msg)
                        else:
                            raise ValueError(f'Unknown `role` under the `receiver` section! Got "{msg.receiver.role}", but only "cerebrum", "user", and "plugin" are acceptable.')
                    except Exception as e:
                        logger.error('An error happened in parsing a message.', exc_info=e)
                        msg=Message(
                            sender=Identity(role='system'),
                            receiver=Identity(role='cerebrum', id=self.cerebrum.id, name=self.cerebrum.name),
                            content_type="<class 'dict'>",
                            content=ClassDict(
                                error=type(e).__name__,
                                detail=str(e)
                            ),
                            time=settings.current_time()
                        )
                        self.message_history.append(msg)
                        if self.verbose:
                            self._check_and_send_msg_to_user(msg)
                if has_user_msg or (self.wait_user_comment and self.verbose):
                    if not self._wait_user_msg():
                        break
                if not self._check_user_msg():
                    break
                msg_list=self._interact_with_cerebrum()
            except Exception as e:
                logger.error('An error happened during the interaction loop.', exc_info=e)
                msg=Message(
                    sender=Identity(role='system'),
                    receiver=Identity(role='user'),
                    content_type="<class 'dict'>",
                    content=ClassDict(
                        error=type(e).__name__,
                        detail=str(e)
                    ),
                    time=settings.current_time()
                )
                self.message_history.append(msg)
                self._check_and_send_msg_to_user(msg)
                if not self._wait_user_msg():
                    break

        self.status=BasicInteractor.Status.STOPPED

    def _check_msg_serializable(self, msg: Message) -> Message:
        msg.time=settings.current_time()
        if msg.content and not Asset.is_trivial(msg.content):
            asset=Asset(
                asset_type=f'message content from `{msg.sender if isinstance(msg.sender, str) else "::".join([msg.sender.role, msg.sender.name])}`',
                content_type=str(type(msg.content)),
                content=msg.content
            )
            msg.content_type='asset_ref'
            self.context.assets[str(asset.asset_id)]=asset
            msg.content=AssetRef(asset_id=asset.asset_id)
        return msg

    def _get_msg_to_user(self, msg: Message):
        msg_to_user=Message(**msg)
        if msg.receiver is None or msg.receiver.role is None:
            msg_to_user.sender=Identity(role='system')
            msg_to_user.receiver=Identity(role='user')
            msg_to_user.content_type='text/markdown'
            msg_to_user.content=f'No receiver message:\n\n```json\n{json.dumps(msg, cls=JsonEncoder, ensure_ascii=False, indent=2)}\n```\n'
        if msg.sender.role!='user':
            if msg.receiver and msg.receiver.role:
                if msg.receiver.role!='user':
                    msg_to_user.sender=Identity(role='system')
                    msg_to_user.receiver=Identity(role='user')
                    msg_to_user.content_type='text/markdown'
                    json_content=json.dumps(msg, cls=JsonEncoder, ensure_ascii=False, indent=2)
                    if msg.sender.role=='cerebrum':
                        if msg.receiver.role=='cerebrum':
                            if self.verbose:
                                msg_to_user.content=f'Cerebrum thoughts:\n\n```json\n{json_content}\n```\n'
                            else:
                                return None
                        elif msg.receiver.role=='plugin':
                            if self.verbose:
                                msg_to_user.content=f'Calling Plugin Command:\n\n```json\n{json_content}\n```\n'
                            else:
                                return None
                        else:
                            if self.verbose:
                                msg_to_user.content=f'Unknown receiver in cerebrum message:\n\n```json\n{json_content}\n```\n'
                            else:
                                return None
                    elif msg.sender.role=='plugin':
                        if self.verbose:
                            msg_to_user.content=f'Plugin Response:\n\n```json\n{json_content}\n```\n'
                        else:
                            return None
                    elif msg.sender.role=='system':
                        if self.verbose:
                            msg_to_user.content=f'System message:\n\n```json\n{json_content}\n```\n'
                        else:
                            return None
                    else:
                        if self.verbose:
                            msg_to_user.content=f'Unknown sender in message:\n\n```json\n{json_content}\n```\n'
                        else:
                            return None

        return msg_to_user

    def _check_and_send_msg_to_user(self, msg):
        if (msg:=self._get_msg_to_user(msg)) is not None:
            self.context.user_interface.send_msg_to_user(msg)

    def _check_user_msg(self) -> bool:
        while self.context.user_interface.has_user_msg():
            msg=self.context.user_interface.get_user_msg()
            if msg is not None:
                if msg.receiver and msg.receiver.role=='interactor':
                    self.context.user_interface.send_msg_to_user(self.on_msg(msg))
                else:
                    if msg.content in self.exit_tokens:
                        return False
                    msg.sender=Identity(role='user')
                    self._thrd_id=msg.thrd_id
                    msg=self._check_msg_serializable(msg)
                    self.message_history.append(msg)
        return True

    def _wait_user_msg(self) -> bool:
        while msg:=self.context.user_interface.wait_user_msg():
            if msg is not None:
                if msg.receiver and msg.receiver.role=='interactor':
                    self.context.user_interface.send_msg_to_user(self.on_msg(msg))
                else:
                    break
            else:
                logger.warning('User interface pipeline is broken. Will exit.')
                break
        if msg is None or msg.content in self.exit_tokens:
            return False
        msg.sender=Identity(role='user')
        self._thrd_id=msg.thrd_id
        msg=self._check_msg_serializable(msg)
        self.message_history.append(msg)
        return True

    def _interact_with_cerebrum(self) -> List[Message]:
        response=self.cerebrum.interact(param=InteractParameter(
            instructions=self.instructions,
            command=None,
            message_history=self.message_history,
            assets=[asset for asset in self.context.assets.values()],
            require_token_len=False,
            require_cost=False
        ), **self.llm_param)
        try:
            msg_list=self.message_manager.parse(response, thrd_id=self._thrd_id)
        except Exception as e:
            logger.error('Failed to parse the cerebrum response message.', exc_info=e)
            raise ValueError('Failed to parse the cerebrum response message, maybe the response format is not a legal JSON.')
        for msg in msg_list:
            msg.sender=Identity(role='cerebrum', id=self.cerebrum.id, name=self.cerebrum.name)
            if msg.receiver is None:
                msg.receiver=Identity(role='user')
        if len(msg_list)==0:
            msg_list.append(Message(
                sender=Identity(role='system'),
                receiver=Identity(role='user'),
                content_type="<class 'dict'>",
                content=ClassDict(
                    error='NoResponseMessage',
                    detail='The cerebrum does not return any message.'
                ),
                time=settings.current_time()
            ))
        self.message_history.extend(msg_list)
        return msg_list

    def set_llm_param(self, update: Dict, remove: List) -> Dict:
        if update:
            self.llm_param.update(update)
        if remove:
            for key in remove:
                if key in self.llm_param:
                    self.llm_param.pop(key)

        return self.llm_param

    def retrieve_history(self, max_count: int = None) -> List[Message]:
        message_list=[]
        if not max_count:
            max_count=len(self.message_history)
        count=0
        for i in range(-1, -len(self.message_history)-1, -1):
            msg=self._get_msg_to_user(self.message_history[i])
            if msg is not None:
                message_list.insert(0, msg)
                count+=1
                if count>=max_count:
                    break
        return message_list

    def clear_history(self) -> bool:
        self.message_history=[]
        return True

    def command(self, command_name: str, param: Any, **kwargs) -> Any:
        if command_name=='set_llm_param':
            return ClassDict(param=self.set_llm_param(param.get('update'), param.get('remove')))
        elif command_name=='retrieve_history':
            return ClassDict(histories=self.retrieve_history(param.get('max_count') if param else None))
        elif command_name=='clear_history':
            return ClassDict(status=self.clear_history())
        else:
            raise ValueError(f'Unknown command: {command_name}. Only "set_llm_param" is acceptable.')
