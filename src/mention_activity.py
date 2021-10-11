from symphony.bdk.core.activity.command import CommandActivity, CommandContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from symphony.bdk.core.service.stream.stream_service import StreamService
from loader.config import conf
# from loader.config import Stream_Service


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
        # text_to_echo = context.text_content[context.text_content.index(self.command_name) + len(self.command_name):]
        # await self._messages.send_message(context.stream_id, f"<messageML>{text_to_echo}</messageML>")

    # async def atRoom(self, msg):

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
        print(totalUsersInRoom)

        if int(totalUsersInRoom) > int(atMentionLimit):
            splitter = True

        for index in range(len(response.value)):

            userId = str(response.value[index]["id"])

            # ## Check the member is not a service account/bot
            # user_details = await self._users.get_user_detail(userId)
            # accountype = user_details.user_attributes.account_type

            if (str(userId) == str(from_user)) or (str(userId) == str(botuserid)):# or (str(accountype) == "SYSTEM"):
                print("ignored ids")
                #logging.debug("ignored ids")
            else:
                counter += 1
                counterAtmentionedOnly += 1
                mentions += "<mention uid=\"" + userId + "\"/> "

                if splitter and int(counter) == int(atMentionLimit):
                    #logging.debug("Displaying @mention")
                    if once:

                        mention_card = "<card iconSrc =\"\" accent=\"tempo-bg-color--blue\"><header> Room @mentioned by " + str(originator) + "</header><body>" + mentions + "</body></card>"
                        await self._messages.send_message(streamid, f"<messageML>{mention_card}</messageML>")
                        once = False
                    else:
                        mention_card = "<card iconSrc =\"\" accent=\"tempo-bg-color--blue\"><header></header><body>" + mentions + "</body></card>"
                        await self._messages.send_message(streamid, f"<messageML>{mention_card}</messageML>")

                    counter = 0
                    mentions = ""
                    thereIsMore = True
                    once = False
                elif thereIsMore and (int(totalUsersInRoom) == int(counterAtmentionedOnly) + 2):
                    #logging.debug("Displaying @mention for more users")
                    mention_card = "<card iconSrc =\"\" accent=\"tempo-bg-color--blue\"><header></header><body>" + mentions + "</body></card>"
                    await self._messages.send_message(streamid, f"<messageML>{mention_card}</messageML>")

        if splitter == False:
            #logging.debug("Displaying @mention")
            mention_card = "<card iconSrc =\"\" accent=\"tempo-bg-color--blue\"><header> Room @mentioned by " + str(originator) + "</header><body>" + mentions + "</body></card>"
            await self._messages.send_message(streamid, f"<messageML>{mention_card}</messageML>")