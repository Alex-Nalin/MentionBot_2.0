#!/usr/bin/env python3
from symphony.bdk.core.activity.command import CommandContext
from symphony.bdk.core.activity.form import FormReplyContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from loader.config import conf
import traceback, html
import logging.config

audit_stream = conf.get("bot_audit")
## allow to get inside Symphony any exception messages

class Audit():
    def __init__(self, messages: MessageService, users: UserService):
        super().__init__()
        self._messages = messages
        self._users = users

    async def auditLoggingCommand(self, ex, context: CommandContext):

        streamid = context.stream_id
        displayName = context.initiator.user.display_name
        userid = context.initiator.user.user_id

        try:
            if audit_stream != "":
                exception_format = (html.escape('Exception: {}'.format(ex)))
                exception_msg = (exception_format + '<br/><br/>Message sent by ' + str(displayName) + 'in ' + str(streamid) + ': <code>' + str(context.text_content) + '</code>Error:<code>' + html.escape(traceback.format_exc()) + '</code>')
                await self._messages.send_message(audit_stream, f"<messageML>{exception_msg}</messageML>")
        except:
            logging.debug("auditLogging function did not run")


    async def audit_systemMessage(self, message):
        try:
            if audit_stream != "":
                await self._messages.send_message(audit_stream, f"<messageML>{message}</messageML>")
            return logging.debug(message)
        except:
            logging.debug("Audit did not work, please check audit stream Id is correct and that the bot is a member of")