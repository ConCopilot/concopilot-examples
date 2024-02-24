# -*- coding: utf-8 -*-

import json
import logging

from typing import Dict, List, Tuple, Any

from concopilot.framework.plugin import PluginManager
from concopilot.framework.interactor import BasicInteractor
from concopilot.framework.resource import ResourceManager
from concopilot.framework.cerebrum import InteractParameter, InteractResponse, Cerebrum
from concopilot.framework.message import Message
from concopilot.framework.message.manager import MessageManager
from concopilot.util.context import Asset, AssetRef
from concopilot.util.identity import Identity
from concopilot.util.initializer import component
from concopilot.util.jsons import JsonEncoder
from concopilot.util import ClassDict
from concopilot import Settings


settings=Settings()
logger=logging.getLogger(__file__)


class AutoInteractor(BasicInteractor):
    def __init__(
        self,
        config: Dict,
        resource_manager: ResourceManager,
        cerebrum: Cerebrum,
        plugin_manager: PluginManager,
        message_manager: MessageManager
    ):
        super(AutoInteractor, self).__init__(
            config,
            resource_manager,
            cerebrum,
            plugin_manager,
            message_manager
        )
        with open(self.config_file_path(self.config.config.instruction_file), encoding='utf8') as file:
            self.instruction: str = file.read()
        self.goals: List[str] = None
        self.instructions: List[str] = None
        self.message_history_key=self.config.config.message_history_key
        self.message_history_start_key=self.config.config.message_history_key+'_start'
        self.message_summary_key=self.config.config.message_summary_key
        self.assets_key=self.config.config.assets_key
        self.summarize_token_len=self.config.config.summarize_token_len
        self.summarizer=component.create_component(self.config.config.summarizer)
        self.llm_param={}
        self.message_history: List[Message] = []
        self._goal_prompt_msg_list=[]

    def config_resources(self, resource_manager: ResourceManager):
        super(AutoInteractor, self).config_resources(resource_manager)
        self.summarizer.config_resources(resource_manager)

    def interact_loop(self):
        if not self._setup_goals():
            return

        cerebrum_command='Determine which next command to use, and respond using the json format specified above.'

        self.message_history: List[Message] = self.context.storage.get_or_default(self.message_history_key, [])
        message_history_start: int = self.context.storage.get_or_default(self.message_history_start_key, 0)
        msg_summary: str = self.context.storage.get_or_default(self.message_summary_key, 'No summary currently.')
        self.context.assets[self.message_summary_key]=Asset(
            asset_type='summary',
            asset_id=self.message_summary_key,
            name='message summary',
            description='The summary of interaction messages between you, plugins, and the user. This is for reminding you with events from your past.',
            content_type='text/plain',
            content=msg_summary
        )
        self.context.assets.update(self.context.storage.get_or_default(self.assets_key, {}))
        while True:
            try:
                if self.context.user_interface.has_user_msg():
                    count=0
                    while msg:=self.context.user_interface.get_user_msg():
                        if msg is not None:
                            if msg.receiver and msg.receiver.role=='interactor':
                                self.context.user_interface.send_msg_user(self.on_msg(msg))
                            else:
                                self._check_msg(msg, Identity(role='user', id=None, name=None))
                                self.message_history.append(msg)
                                count+=1
                        if not self.context.user_interface.has_user_msg():
                            break
                    cerebrum_command=cerebrum_command+f' Note that {count} incoming user message detected.'

                response, message_history_start=self._interact_with_cerebrum(cerebrum_command, message_history_start, self.context.assets)
                try:
                    msg=self.message_manager.parse(response)[0]
                except Exception as e:
                    logger.error('Failed to parse the cerebrum response message.', exc_info=e)
                    raise ValueError('Failed to parse the cerebrum response message, maybe the response format is not acceptable.')
                self._check_msg(msg, Identity(role='cerebrum', id=self.cerebrum.id, name=self.cerebrum.name))

                self.message_history.append(Message(
                    sender=Identity(role='user'),
                    receiver=Identity(role='cerebrum', id=self.cerebrum.id, name=self.cerebrum.name),
                    content_type='text/plain',
                    content=cerebrum_command,
                    time=settings.current_time()
                ))
                self.message_history.append(msg)
                self.context.storage.put(self.message_history_key, self.message_history)
                self.context.storage.put(self.assets_key, self.context.assets)

                cerebrum_command='Determine which next command to use, and respond using the format specified above.'
                if msg.receiver is not None:
                    if msg.receiver.role=='system':
                        if isinstance(msg.content, ClassDict):
                            if msg.content.error:
                                cerebrum_command='Last command execution threw an error. Check the error in the interaction messages, and try to fix the error and determine which next command to use, and respond using the json format specified above.'
                            elif msg.content.command=='exit':
                                break
                            else:
                                raise ValueError(f'Unknown "command" in the "content" section! Got "{msg.content.command}", but only "error" and "exit" are acceptable.')
                        else:
                            raise ValueError('The "content" section is supposed to be a Dict!')
                    elif msg.receiver.role=='cerebrum':
                        pass
                    elif msg.receiver.role=='user':
                        self.context.user_interface.send_msg_user(msg)
                        while msg:=self.context.user_interface.wait_user_msg():
                            if msg is not None:
                                if msg.receiver and msg.receiver.role=='interactor':
                                    self.context.user_interface.send_msg_user(self.on_msg(msg))
                                else:
                                    break
                            else:
                                logger.error('User interface pipeline is broken. Will exit.')
                                break
                        if not msg:
                            break
                        self._check_msg(msg, Identity(role='user', id=None, name=None))
                        self.message_history.append(msg)
                    elif msg.receiver.role=='plugin':
                        plugin=self.plugin_manager.get_plugin(name=msg.receiver.name)
                        if plugin is None:
                            raise ValueError(f'No such plugin with the name: {msg.receiver.name}.')
                        msg=plugin.on_msg(msg)
                        self._check_msg(msg, Identity(role='plugin', id=plugin.id, name=plugin.name))
                        self.message_history.append(msg)
                    else:
                        raise ValueError(f'Unknown "role" in the "receiver" section! Got "{msg.receiver.role}", but only "system", "cerebrum", "user", and "plugin" are acceptable.')
                else:
                    raise ValueError('A `receiver` section is required in your response message!')
            except Exception as e:
                logger.error('An error happened during the thinking loop.', exc_info=e)
                msg=Message(
                    sender=Identity(role='system'),
                    receiver=Identity(role='cerebrum', id=self.cerebrum.id, name=self.cerebrum.name),
                    content_type="<class 'dict'>",
                    content=ClassDict(
                        error=e.__class__.__name__,
                        detail=str(e)
                    )
                )
                self._check_msg(msg, Identity(role='system', id=None, name=None))
                self.message_history.append(msg)
                cerebrum_command='An error happened during the thinking loop. Check the error in the interaction messages, and try to fix the error and determine which next command to use, and respond using the json format specified above.'

    def _check_msg(self, msg: Message, sender: Identity) -> Message:
        if sender is not None:
            msg.sender=sender
        msg.time=settings.current_time()
        if msg.content and not Asset.is_trivial(msg.content):
            asset=Asset(
                asset_type=f'message content from `{sender if isinstance(sender, str) else "::".join([sender.role, sender.name])}`',
                content_type=str(msg.content.__class__),
                content=msg.content
            )
            msg.content_type='asset_ref'
            self.context.assets[str(asset.asset_id)]=asset
            msg.content=AssetRef(asset_id=asset.asset_id)
        if AutoInteractor._need_convert_to_status(msg):
            self.context.user_interface.send_msg_user(AutoInteractor._status_msg(msg))
        logger.debug('\n'+json.dumps(msg, cls=JsonEncoder, ensure_ascii=False, indent=4)+'\n')
        return msg

    @staticmethod
    def _need_convert_to_status(msg: Message) -> bool:
        return (not msg.sender or msg.sender.role!='user') and (not msg.receiver or msg.receiver.role!='user')

    @staticmethod
    def _status_msg(msg: Message) -> Message:
        return Message(
            sender=Identity(role='system'),
            receiver=Identity(role='user'),
            content_type='text/markdown',
            content=f'Current status:\n\n```json\n{json.dumps(msg, cls=JsonEncoder, ensure_ascii=False, indent=4)}\n```\n',
            time=msg.time
        )

    def _setup_goals(self):
        if self.config.config.goals is not None:
            self.goals=self.config.config.goals
        elif self.config.config.goals_file_path is not None:
            with open(self.config.config.goals_file_path, encoding='utf8') as file:
                self.goals=file.readlines()
        else:
            msg=Message(
                sender=Identity(role='system'),
                content_type='text/plain',
                content='Please input your goals:',
                time=settings.current_time()
            )
            self._goal_prompt_msg_list.append(msg)
            self.context.user_interface.send_msg_user(msg)
            while msg:=self.context.user_interface.wait_user_msg():
                if msg is not None:
                    if msg.receiver and msg.receiver.role=='interactor':
                        self.context.user_interface.send_msg_user(self.on_msg(msg))
                    else:
                        break
                else:
                    logger.error('User interface pipeline is broken. Will exit.')
                    return False
            self._goal_prompt_msg_list.append(msg)
            self.goals=msg.content.split('\n')

        instruction=self.instruction\
            .replace('{ai_name}', self.cerebrum.name)\
            .replace('{ai_role}', self.cerebrum.role)\
            .replace('{ai_id}', str(self.cerebrum.id))\
            .replace('{goals}', '\n'.join([f'{i+1}. {goal}' for i, goal in enumerate(self.goals)]))

        if self.config.config.with_plugin_prompt:
            instruction=instruction.replace('{plugins}', self.plugin_manager.get_combined_prompt())

        self.instructions=[instruction]

        return True

    def setup_plugins(self):
        if not self.config.config.with_plugin_prompt:
            self.cerebrum.setup_plugins(self.plugin_manager)

    def _interact_with_cerebrum(self, command: str, message_history_start: int, assets: Dict[str, Asset]) -> Tuple[InteractResponse, int]:
        response=self.cerebrum.interact(param=InteractParameter(
            instructions=self.instructions,
            command=command,
            message_history=self.message_history[message_history_start:],
            assets=[asset for asset in assets.values()],
            require_token_len=True,
            require_cost=True
        ), **self.llm_param)
        if response.input_token_len and response.input_token_len>self.summarize_token_len:
            msg_summary=self.summarizer.summarize(self.message_history[message_history_start:], assets[self.message_summary_key].content)
            assets[self.message_summary_key].content=msg_summary
            self.context.storage.put(self.message_summary_key, msg_summary)
            message_history_start=len(self.message_history)
            self.context.storage.put(self.message_history_start_key, message_history_start)
        return response, message_history_start

    def set_llm_param(self, update: Dict, remove: List) -> Dict:
        if update:
            self.llm_param.update(update)
        if remove:
            for key in remove:
                if key in self.llm_param:
                    self.llm_param.pop(key)

        return self.llm_param

    def retrieve_history(self, max_count: int = None) -> List[Message]:
        message_list=self._goal_prompt_msg_list+[(AutoInteractor._status_msg(msg) if AutoInteractor._need_convert_to_status(msg) else msg) for msg in self.message_history]
        if not max_count:
            max_count=len(message_list)
        return message_list[-max_count:]

    def clear_history(self) -> bool:
        self.message_history=[]
        return True

    def command(self, command_name: str, param: Any, **kwargs) -> Any:
        if command_name=='set_llm_param':
            return ClassDict(param=self.set_llm_param(param.get('update'), param.get('remove')))
        elif command_name=='retrieve_history':
            return ClassDict(histories=self.retrieve_history(param.get('max_count')))
        elif command_name=='clear_history':
            return ClassDict(status=self.clear_history())
        else:
            raise ValueError(f'Unknown command: {command_name}. Only "set_llm_param" is acceptable.')
