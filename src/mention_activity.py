import html

from symphony.bdk.core.activity.command import CommandActivity, CommandContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from symphony.bdk.core.service.stream.stream_service import StreamService
from symphony.bdk.core.service.message.model import Message
from src.audit import Audit
from symphony.bdk.gen.agent_model.v4_message import V4Message
from loader.config import conf
import logging.config
import src.utils as utils
import asyncio

audit_stream = conf.get("bot_audit")

class MentionCommandActivity(CommandActivity):

    command_name = "/all"
    isReplyForward = False

    def __init__(self, messages: MessageService, streams: StreamService, users: UserService):
        self._messages = messages
        self._streams = streams
        self._users = users
        super().__init__()

    def matches(self, context: CommandContext) -> bool:

        mention = False
        if ("@" + context.bot_display_name) in context.text_content:
            mention = True

        command = False
        if self.command_name in context.text_content:
            command = True

        return mention, command

    async def on_activity(self, context: CommandContext):

        mention, command = (self.matches(context))

        streamType = (await self._streams.get_stream(context.stream_id))['stream_type']['type']

        if streamType == "IM" and command:
            asyncio.create_task(self.actual_logic(context))
        elif (streamType == "ROOM" or streamType == "MIM") and mention and command:
            asyncio.create_task(self.actual_logic(context))

    async def actual_logic(self, context):
        ## Check pod source
        user_pod_info = (await self._users.get_user_detail(context.initiator.user.user_id))["user_attributes"]["company_name"]

        if str(user_pod_info) in conf.get("allowedPod"):

            streamid = context.stream_id
            messageid = context.message_id
            displayName = context.initiator.user.display_name
            userid = context.initiator.user.user_id
            stream_type = (await self._streams.get_stream(streamid))["stream_type"]["type"]

            if audit_stream != "":
                botaudit = "Function /all called by <b>" + str(displayName) + " " + str(userid) + " </b> in " + str(streamid) + " (" + str(stream_type) + ")"
                await self._messages.send_message(audit_stream, f"<messageML>{botaudit}</messageML>")
                logging.debug("Function /all called by " + str(displayName) + " " + str(userid) + "  in " + str(streamid) + " (" + str(stream_type) + ")")

            try:
                originator = "<mention uid=\"" + str(userid) + "\"/>"
                botuserid = str(conf['bot']['id'])

                stream_type = (await self._streams.get_stream(streamid))["stream_type"]["type"]

                if str(stream_type) == "IM":
                    IMmention = ("There is only you and me, " + str(originator) + " <emoji shortcode=\"smile\" />")
                    return await self._messages.send_message(streamid, f"<messageML>{IMmention}</messageML>")

                elif str(stream_type) == "ROOM" or str(stream_type) == "MIM":

                    ## Handing reply message:
                    try:
                        logging.debug(f"This is a reply or forward message of {context.source_event.message.parent_message_id}")
                        isReplyForward = True

                        parent_message_content = (await self._messages.get_message(context.source_event.message.parent_message_id))["message"]
                        # logging.debug(f"parent_message_content {parent_message_content}")
                        check_parent_message_content = await utils.check_mentions(parent_message_content)
                        # logging.debug(f"1 {check_parent_message_content}")

                        if str(check_parent_message_content) == "(False, False)":
                            isReplyForward = False

                        elif str(check_parent_message_content) == "(True, True)":
                            new_message_content = (await self._messages.get_message(context.source_event.message.message_id))["message"]
                            # logging.debug(f"new_message_content {new_message_content}")

                            forwarded_message = "<br/><b>Forwarded Message:</b>Posted by"

                            # Forwarded message
                            if forwarded_message in new_message_content:
                                # print("FWD")
                                isReplyForward = True

                                fwd_message_content = str(new_message_content).split(forwarded_message)
                                check_fwd_message_content = await utils.check_mentions(fwd_message_content[0])
                                # logging.debug(f"A {check_fwd_message_content}")

                                if str(check_fwd_message_content) == "(True, True)":
                                    isReplyForward = False

                            # Replied message
                            else:
                                # print("REPLY")

                                if "</i>———————————" in str(new_message_content):
                                    new_message_content_split = str(new_message_content).split("</i>———————————")
                                    # print(new_message_content_split)

                                elif "_———————————" in str(new_message_content):
                                    new_message_content_split = str(new_message_content).split("_———————————")
                                    # print(new_message_content_split)

                                check_new_message_content = await utils.check_mentions(new_message_content_split[1])
                                # logging.debug(f"2 {check_new_message_content}")

                                if str(check_new_message_content) == "(True, True)":
                                    isReplyForward = False



                    except:
                        isReplyForward = False

                    if not isReplyForward:

                        await self._messages.send_message(streamid, f'''<messageML><mention uid="{str(userid)}"/>, @mention Notification sent (via blast) to all members of this room</messageML>''')

                        try:
                            roominfo = await self._streams.get_room_info(streamid)
                            roomname = html.escape(roominfo['room_attributes']['name'])
                        except:
                            roomname = streamid


                        # blastmessage = f'''Hi, <mention uid="{str(userid)}"/> has @mentioned you in <b><i>{roomname}</i></b> <a href="https://open.symphony.com/?streamId={str(streamid).replace("-", "+").replace("_", "/")}==&#38;streamType=chatroom"><b>View message now</b></a>'''
                        blastmessage = f'''Hi, <mention uid="{str(userid)}"/> has @mentioned you in <b><i>{roomname}</i></b> <a href="https://open.symphony.com/?streamId={str(streamid).replace("-", "%2B").replace("_", "%2F")}%3D%3D&#38;messageId={str(messageid).replace("-", "%2B").replace("_", "%2F")}%3D%3D"><b>View message now</b></a>'''

                        ## Room membership, also works for MIMs
                        response = await self._streams.list_room_members(streamid)

                        memberCount = len(response.value)

                        # Assuming each member has an 'id' attribute
                        user_ids = [member.id for member in response.value]

                        # Set the size of each sublist
                        sublist_size = 100  # Adjust this value based on your preference

                        # Create sublists of user IDs
                        sublists = [user_ids[i:i + sublist_size] for i in range(0, len(user_ids), sublist_size)]

                        # Iterate through the sublists
                        for sublist in sublists:
                            logging.debug(f"Processing sublist: {sublist}")

                            usersToSend = []
                            for user_id in sublist:
                                logging.debug(f"Processing user ID: {user_id}")
                                # Add your processing logic here

                                if (str(user_id) == str(botuserid)) or (str(user_id) == str(userid)):
                                #print("ignored ids")
                                    logging.debug(f"ignored id: {user_id}")
                                else:
                                    usersToSend.append(user_id)

                            # Create valid rooms
                            streamToSend = []
                            for index_streams in range(len(usersToSend)):
                                unique_userid = (usersToSend[index_streams])
                                createIM = (await self._streams.create_im_or_mim([int(unique_userid)]))['id']
                                logging.debug(f"createIM: {createIM}")
                                streamToSend.append(createIM)

                            await self._messages.blast_message(streamToSend, Message(content=blastmessage, data=None, attachments=None))

            except Exception as ex:
                logging.error("/all did not run")
                logging.exception("Message Command Processor Exception: {}".format(ex))
                await Audit.auditLoggingCommand(self, ex, context)

        else:
            logging.debug("Pod is not in allowed list, " + str(user_pod_info))
