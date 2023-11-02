from symphony.bdk.core.activity.command import CommandActivity, CommandContext
from symphony.bdk.core.activity.user_joined_room import UserJoinedRoomActivity, UserJoinedRoomContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from symphony.bdk.core.service.stream.stream_service import StreamService
from loader.config import conf
from src.audit import Audit
import logging.config
import asyncio

audit_stream = conf.get("bot_audit")

class HelpCommandActivity(CommandActivity):
    command_name = "/help"

    def __init__(self, messages: MessageService, streams: StreamService):
        self._messages = messages
        self._streams = streams
        super().__init__()

    def matches(self, context: CommandContext) -> bool:
        ## This is for @mention /all at the start of the string
        # return context.text_content.startswith("@" + context.bot_display_name + " " + self.command_name)

        mention = False
        if ("@" + context.bot_display_name) in context.text_content:
            mention = True

        command = False
        if self.command_name in context.text_content:
            command = True

        ## This allows the @mention and /all to be placed anywhere in the text
        # if (("@" + context.bot_display_name) and self.command_name) in context.text_content:
        if mention and command:
            return True
        else:
            return False

    async def on_activity(self, context: CommandContext):
        asyncio.create_task(self.actual_logic(context))

    async def actual_logic(self, context):
        streamid = context.stream_id
        displayName = context.initiator.user.display_name
        userid = context.initiator.user.user_id
        stream_type = (await self._streams.get_stream(streamid))["stream_type"]["type"]

        if audit_stream != "":
            botaudit = "Function /help called by <b>" + str(displayName) + " " + str(userid) + " </b> in " + str(streamid) + " (" + str(stream_type)
            await self._messages.send_message(audit_stream, f"<messageML>{botaudit}</messageML>")
            logging.debug(botaudit)

        try:

            displayHelp = "<card accent='tempo-bg-color--blue' iconSrc=''> \
                                <header><h2>Bot Commands (v2.0)</h2></header> \
                                <body> \
                                  <table style='max-width:100%'><thead><tr style='background-color:#4D94FF;color:#ffffff;font-size:1rem' class=\"tempo-text-color--white tempo-bg-color--black\"> \
                                        <td><b>Command</b></td> \
                                        <td><b>Description</b></td> \
                                      </tr> \
                                    </thead> \
                                    <tbody> \
                                      <tr> \
                                        <td>/all</td> \
                                        <td>At Mention all users of the stream</td> \
                                      </tr> \
                                    <tr> \
                                      <td>/status</td> \
                                      <td>Shows how long the Mention Bot has been running for</td> \
                                    </tr> \
                                    </tbody> \
                                    </table> \
                                </body> \
                            </card>"

            await self._messages.send_message(context.stream_id, f"<messageML>{displayHelp}</messageML>")

        except Exception as ex:
            logging.error("/help did not run")
            logging.exception("Message Command Processor Exception: {}".format(ex))
            await Audit.auditLoggingCommand(self, ex, context)

