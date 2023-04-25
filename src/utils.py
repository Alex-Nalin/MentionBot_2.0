from loader.config import conf
import logging
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