from symphony.bdk.core.activity.command import CommandActivity, CommandContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from symphony.bdk.core.service.stream.stream_service import StreamService
from src.audit import Audit
from symphony.bdk.gen.agent_model.v4_message import V4Message
from loader.config import conf
import logging.config
import src.utils as utils
import asyncio

audit_stream = conf.get("bot_audit")

class MentionCommandActivity(CommandActivity):

    command_name = "/all"

    def __init__(self, messages: MessageService, streams: StreamService, users: UserService):
        self._messages = messages
        self._streams = streams
        self._users = users
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
        ## Check pod source
        user_pod_info = (await self._users.get_user_detail(context.initiator.user.user_id))["user_attributes"]["company_name"]

        if str(user_pod_info) in conf.get("allowedPod"):

            streamid = context.stream_id
            displayName = context.initiator.user.display_name
            userid = context.initiator.user.user_id
            stream_type = (await self._streams.get_stream(streamid))["stream_type"]["type"]

            if audit_stream != "":
                botaudit = "Function /all called by <b>" + str(displayName) + " " + str(userid) + " </b> in " + str(streamid) + " (" + str(stream_type)
                await self._messages.send_message(audit_stream, f"<messageML>{botaudit}</messageML>")

            try:

                splitter = False
                thereIsMore = False
                once = True
                atMentionLimit = 39
                streamid = context.stream_id
                from_user = context.initiator.user.user_id
                originator = "<mention uid=\"" + str(from_user) + "\"/>"
                botuserid = str(conf['bot']['id'])
                mentions = ""

                stream_type = (await self._streams.get_stream(streamid))["stream_type"]["type"]

                if str(stream_type) == "IM":
                    IMmention = ("There is only you and me, " + str(originator) + " <emoji shortcode=\"smile\" />")
                    return await self._messages.send_message(streamid, f"<messageML>{IMmention}</messageML>")

                ## Room membership, also works for MIMs
                response = await self._streams.list_room_members(streamid)

                counter = 0
                counterAtmentionedOnly = 0
                totalUsersInRoom = len(response.value)

                if int(totalUsersInRoom) > int(atMentionLimit):
                    splitter = True

                for index in range(len(response.value)):

                    userId = str(response.value[index]["id"])

                    # ## Check the member is not a service account/bot
                    # user_details = await self._users.get_user_detail(userId)
                    # accountype = user_details.user_attributes.account_type

                    if (str(userId) == str(from_user)) or (str(userId) == str(botuserid)):# or (str(accountype) == "SYSTEM"):
                        #print("ignored ids")
                        logging.debug("ignored ids")
                    else:
                        counter += 1
                        counterAtmentionedOnly += 1
                        mentions += "<mention uid=\"" + userId + "\"/> "

                        if splitter and int(counter) + 1 == int(atMentionLimit):
                            logging.debug("Displaying @mention")
                            if once:

                                mention_card = "<card iconSrc =\"\" accent=\"tempo-bg-color--blue\"><header></header><body>" + mentions + "</body></card>"
                                previous_message: V4Message = await self._messages.send_message(streamid, f"<messageML>{mention_card}</messageML>")
                                messageid = previous_message.message_id
                                await utils.messageidWriteToFile(self, streamid, messageid)
                                once = False
                                logging.debug("A")
                                logging.debug(mention_card)

                            else:
                                # get messageid from file
                                messageid = await utils.getmessageid(self, streamid)

                                mention_card = "<card iconSrc =\"\" accent=\"tempo-bg-color--blue\"><header></header><body>" + mentions + "</body></card>"
                                try:
                                    previous_message: V4Message =  await self._messages.update_message(streamid, messageid, f"<messageML>{mention_card}</messageML>")
                                except:
                                    previous_message: V4Message = await self._messages.send_message(streamid, f"<messageML>{mention_card}</messageML>")
                                messageid = previous_message.message_id
                                await utils.messageidWriteToFile(self, streamid, messageid)
                                logging.debug("B")
                                logging.debug(mention_card)

                            counter = 0
                            mentions = ""
                            thereIsMore = True
                            once = False
                        elif thereIsMore and (int(totalUsersInRoom) == int(counterAtmentionedOnly) + 2):
                            logging.debug("Displaying @mention for more users")

                            # get messageid from file
                            messageid = await utils.getmessageid(self, streamid)

                            mention_card = "<card iconSrc =\"\" accent=\"tempo-bg-color--blue\"><header></header><body>" + mentions + "</body></card>"
                            try:
                                previous_message: V4Message =  await self._messages.update_message(streamid, messageid, f"<messageML>{mention_card}</messageML>")
                            except:
                                previous_message: V4Message = await self._messages.send_message(streamid, f"<messageML>{mention_card}</messageML>")

                            messageid = previous_message.message_id
                            await utils.messageidWriteToFile(self, streamid, messageid)
                            logging.debug("C")
                            logging.debug(mention_card)

                if splitter == False:
                    logging.debug("Displaying @mention")

                    mention_card = "<card iconSrc =\"\" accent=\"tempo-bg-color--blue\"><header></header><body>" + mentions + "</body></card>"

                    previous_message: V4Message = await self._messages.send_message(streamid, f"<messageML>{mention_card}</messageML>")
                    messageid = previous_message.message_id
                    await utils.messageidWriteToFile(self, streamid, messageid)
                    logging.debug("D")
                    logging.debug(mention_card)

                try:
                    # get messageid from file
                    messageid = await utils.getmessageid(self, streamid)
                    await self._messages.update_message(streamid, messageid, f"<messageML>The room was @mentioned by {originator} (all mentions are now hidden)</messageML>")
                except:
                    logging.debug("Didnt Work")

            except Exception as ex:
                logging.error("/status did not run")
                logging.exception("Message Command Processor Exception: {}".format(ex))
                await Audit.auditLoggingCommand(self, ex, context)

        else:
            logging.debug("Pod is not in allowed list, " + str(user_pod_info))
