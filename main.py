#!/usr/bin/env python3
from symphony.bdk.core.config.loader import BdkConfigLoader
from symphony.bdk.core.service.datafeed.real_time_event_listener import RealTimeEventListener
from symphony.bdk.core.symphony_bdk import SymphonyBdk
from symphony.bdk.gen.agent_model.v4_initiator import V4Initiator
from symphony.bdk.gen.agent_model.v4_message_sent import V4MessageSent
from src.activities import HelpCommandActivity
from src.mention_activity import MentionCommandActivity
from src.status_activity import StatusCommandActivity
from loader.config import conf

import asyncio
import logging.config
from pathlib import Path

# Configure logging
current_dir = Path(__file__).parent
logging_conf = Path.joinpath(current_dir, './resources', 'logging.conf')
config_path = Path.joinpath(current_dir, './resources', 'config.yaml')
logging.config.fileConfig(logging_conf, disable_existing_loggers=False)

audit_stream = conf.get("bot_audit")

async def run():
    config = BdkConfigLoader.load_from_file(config_path)

    async with SymphonyBdk(config) as bdk:
        datafeed_loop = bdk.datafeed()
        datafeed_loop.subscribe(MessageListener())

        activities = bdk.activities()
        activities.register(HelpCommandActivity(bdk.messages(), bdk.streams()))
        activities.register(MentionCommandActivity(bdk.messages(), bdk.streams(), bdk.users()))
        activities.register(StatusCommandActivity(bdk.messages(), bdk.streams()))

        ## Start the datafeed read loop
        await datafeed_loop.start()

class MessageListener(RealTimeEventListener):
    async def on_message_sent(self, initiator: V4Initiator, event: V4MessageSent):
        logging.debug("Message received from %s %s in %s %s: %s", initiator.user.display_name, initiator.user.user_id, event.message.stream.stream_id, event.message.stream.stream_type, event.message.message)


## Start the main asyncio run
try:
    logging.info("Running bot application...")
    asyncio.run(run())
except KeyboardInterrupt:
    logging.info("Ending bot application")
