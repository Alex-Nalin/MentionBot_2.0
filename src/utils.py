from loader.config import conf
import logging
import re
from datafile.messageid import MessageID
from src.audit import Audit

audit_stream = conf.get("bot_audit")

async def messageidWriteToFile(self, streamid, messageid):
    logging.debug("writeToFile")

    try:
        MessageID.update({str(streamid): str(messageid)})

        Store = {}
        for key in MessageID.keys():
            Store.update({key: MessageID[key]})

        updatedMessageID = 'MessageID = ' + str(Store)
        file = open("datafile/messageid.py", "w+")
        file.write(updatedMessageID)
        file.close()
        return logging.debug("Finished Writing to messageid.py")
    except:
        message = "Writing to messageid.py did not work"
        logging.debug(message)
        await Audit.audit_systemMessage(self, message)

async def getmessageid(self, streamid):
    # Check for previous messageid to update with
    for key in list(MessageID.keys()):
        if str(key) == str(streamid):
            messageid = str(MessageID[key])
            logging.debug(f"Current Message ID {messageid}")
            return messageid

async def check_mentions(input_string):
    return "@MentionBot" in input_string, "/all" in input_string

def match_command(text_content, bot_display_name, command_name):
    """
    Check if a command matches for the given bot.
    Returns (mention, command) tuple where:
    - mention: True if the bot is @mentioned in the text
    - command: True if this specific command was invoked (not merely present in a URL or unrelated text)
    """
    if not text_content or not bot_display_name or not command_name:
        return False, False

    bot_mention = "@" + bot_display_name
    mention = bot_mention.lower() in text_content.lower()

    command = False
    if command_name == "/team":
        bot_pattern = rf"{re.escape(bot_mention)}[:,]?\s*/team(?!\/)"
        im_pattern = r"(?:^|\s)/team(?!\/)"
        if mention:
            command = bool(re.search(bot_pattern, text_content, re.IGNORECASE) or re.search(im_pattern, text_content, re.IGNORECASE))
        else:
            command = bool(re.search(im_pattern, text_content, re.IGNORECASE))
    elif command_name in ("/all", "/status", "/help"):
        cmd = command_name[1:]  # e.g. "all", "status", "help"
        bot_pattern = rf"{re.escape(bot_mention)}[:,]?\s*/{cmd}(?!\w)"
        im_pattern = rf"(?:^|\s)/{cmd}(?!\w)"
        if mention:
            command = bool(re.search(bot_pattern, text_content, re.IGNORECASE) or re.search(im_pattern, text_content, re.IGNORECASE))
        else:
            command = bool(re.search(im_pattern, text_content, re.IGNORECASE))

    return mention, command
