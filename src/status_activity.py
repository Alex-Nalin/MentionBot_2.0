from symphony.bdk.core.activity.command import CommandActivity, CommandContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.stream.stream_service import StreamService
from loader.config import conf
import logging.config
import os, psutil, time, datetime
from src.audit import Audit
import asyncio

audit_stream = conf.get("bot_audit")


class StatusCommandActivity(CommandActivity):

    command_name = "/status"

    def __init__(self, messages: MessageService, streams: StreamService):
        self._messages = messages
        self._streams = streams
        super().__init__()

    def matches(self, context: CommandContext) -> bool:
        ## This is for @mention /all at the start of the string
        # return context.text_content.startswith("@" + context.bot_display_name + " " + self.command_name)

        ## This allows the @mention and /all to be placed anywhere in the text
        if (("@" + context.bot_display_name) and self.command_name) in context.text_content:
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

        try:

            if audit_stream != "":
                botaudit = "Function /status called by <b>" + str(displayName) + " " + str(userid) + " </b> in " + str(streamid) + " (" + str(stream_type)
                await self._messages.send_message(audit_stream, f"<messageML>{botaudit}</messageML>")
                logging.debug(botaudit)

            date2 = datetime.datetime.now()
            p = psutil.Process(os.getpid())
            date1 = datetime.datetime.strptime(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time())),"%Y-%m-%d %H:%M:%S")

            uptime = ("\n%d days, %d hours, %d minutes, %d seconds" % dhms_from_seconds(date_diff_in_seconds(date2, date1)))
            uptimemessage = "I have been running for " + str(uptime)
            return await self._messages.send_message(streamid, f"<messageML>{uptimemessage}</messageML>")

        except Exception as ex:
            logging.error("/status did not run")
            logging.exception("Message Command Processor Exception: {}".format(ex))
            await Audit.auditLoggingCommand(self, ex, context)



## Used for Bot status call to see untime
def date_diff_in_seconds(dt2, dt1):
  timedelta = dt2 - dt1
  return timedelta.days * 24 * 3600 + timedelta.seconds
#
def dhms_from_seconds(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return (days, hours, minutes, seconds)