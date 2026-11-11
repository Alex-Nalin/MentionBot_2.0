import html
import re
from symphony.bdk.core.activity.command import CommandActivity, CommandContext
from symphony.bdk.core.service.message.message_service import MessageService
from symphony.bdk.core.service.user.user_service import UserService
from symphony.bdk.core.service.stream.stream_service import StreamService
from symphony.bdk.core.service.message.model import Message
from src.audit import Audit
from symphony.bdk.gen.agent_model.v4_message import V4Message
from loader.config import conf, teams_conf
import logging.config
import src.utils as utils
import asyncio

audit_stream = conf.get("bot_audit")

class TeamCommandActivity(CommandActivity):

    command_name = "/team"
    isReplyForward = False

    def __init__(self, messages: MessageService, streams: StreamService, users: UserService):
        self._messages = messages
        self._streams = streams
        self._users = users
        super().__init__()

    def matches(self, context: CommandContext) -> bool:
        return utils.match_command(context.text_content, context.bot_display_name, self.command_name)

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

            # Prevent processing on replies and forwards to avoid duplicate notifications
            isReplyForward = False
            
            try:
                # Check if this is a reply or forward message
                if hasattr(context.source_event.message, 'parent_message_id') and context.source_event.message.parent_message_id:
                    logging.debug(f"This is a reply or forward message of {context.source_event.message.parent_message_id}")
                    isReplyForward = True

                    parent_message_content = (await self._messages.get_message(context.source_event.message.parent_message_id))["message"]
                    check_parent_message_content = await utils.check_mentions(parent_message_content)

                    if str(check_parent_message_content) == "(False, False)":
                        isReplyForward = False

                    elif str(check_parent_message_content) == "(True, True)":
                        new_message_content = (await self._messages.get_message(context.source_event.message.message_id))["message"]

                        forwarded_message = "<br/><b>Forwarded Message:</b>Posted by"

                        # Forwarded message
                        if forwarded_message in new_message_content:
                            isReplyForward = True

                            fwd_message_content = str(new_message_content).split(forwarded_message)
                            check_fwd_message_content = await utils.check_mentions(fwd_message_content[0])

                            if str(check_fwd_message_content) == "(True, True)":
                                isReplyForward = False

                        # Replied message
                        else:
                            if "</i>———————————" in str(new_message_content):
                                new_message_content_split = str(new_message_content).split("</i>———————————")
                            elif "_———————————" in str(new_message_content):
                                new_message_content_split = str(new_message_content).split("_———————————")
                            else:
                                new_message_content_split = [new_message_content]

                            if len(new_message_content_split) > 1:
                                check_new_message_content = await utils.check_mentions(new_message_content_split[1])

                                if str(check_new_message_content) == "(True, True)":
                                    isReplyForward = False

            except Exception as e:
                logging.debug(f"Error checking reply/forward status: {e}")
                isReplyForward = False

            if isReplyForward:
                logging.info(f"Skipping team command processing for reply/forward message from {displayName}")
                return

            if audit_stream != "":
                botaudit = "Function /team called by <b>" + str(displayName) + " " + str(userid) + " </b> in " + str(streamid) + " (" + str(stream_type) + ")"
                await self._messages.send_message(audit_stream, f"<messageML>{botaudit}</messageML>")
                logging.debug("Function /team called by " + str(displayName) + " " + str(userid) + "  in " + str(streamid) + " (" + str(stream_type) + ")")

            try:
                originator = "<mention uid=\"" + str(userid) + "\"/>"
                botuserid = str(conf['bot']['id'])

                stream_type = (await self._streams.get_stream(streamid))["stream_type"]["type"]

                ## Extract all team names from command
                command_text = context.text_content
                team_names = self.extract_all_team_names(command_text)

                if str(stream_type) == "IM" and team_names:
                    IMmention = ("There is only you and me, " + str(originator) + " <emoji shortcode=\"smile\" />")
                    return await self._messages.send_message(streamid, f"<messageML>{IMmention}</messageML>")

                elif str(stream_type) == "ROOM" or str(stream_type) == "MIM" or str(stream_type) == "IM":

                    if not team_names:
                        # Show available teams
                        await self.show_available_teams(streamid)
                        return

                    # Debug command to check room member structure
                    if len(team_names) == 1 and team_names[0].lower() == "debug":
                        await self.debug_room_members(streamid)
                        return

                    # Process each team separately
                    for team_name in team_names:
                        await self.process_single_team(streamid, originator, botuserid, team_name, context)

            except Exception as ex:
                logging.error("/team did not run")
                logging.exception("Message Command Processor Exception: {}".format(ex))
                await Audit.auditLoggingCommand(self, ex, context)

        else:
            logging.debug("Pod is not in allowed list, " + str(user_pod_info))

    def extract_all_team_names(self, command_text):
        """Extract all team names from the command text after /team"""
        if "/team" not in command_text.lower():
            return []

        team_names = []
        pattern = re.compile(
            r"(?:^|\s|(?:@\S+\s*))/team(?!\/)(?P<arg>[^\n\r]*)",
            re.IGNORECASE
        )

        for m in pattern.finditer(command_text):
            arg = m.group("arg").strip()
            if not arg:
                continue

            if "/team" in arg.lower():
                sub_parts = [p.strip() for p in re.split(r"(?:^|\s)/team(?!\/)", arg, flags=re.IGNORECASE) if p.strip()]
                for sub in sub_parts:
                    team_names.append(sub)
            else:
                team_names.append(arg)

        return team_names

    def extract_team_name(self, command_text):
        """Extract team name from the command text after /team (legacy method)"""
        team_names = self.extract_all_team_names(command_text)
        return team_names[0] if team_names else None

    def get_team_members(self, team_name):
        """Get team members from configuration with fuzzy matching"""
        teams = teams_conf.get("teams", {})
        
        # First try exact match
        if team_name in teams:
            team_data = teams[team_name]
            # Extract member names from the new structure
            members = []
            for member in team_data.get("members", []):
                if isinstance(member, dict):
                    members.append(member.get("name", ""))
                else:
                    # Fallback for old format
                    members.append(str(member))
            return members, team_name
        
        # Try case-insensitive match
        for key in teams.keys():
            if key.lower() == team_name.lower():
                team_data = teams[key]
                members = []
                for member in team_data.get("members", []):
                    if isinstance(member, dict):
                        members.append(member.get("name", ""))
                    else:
                        members.append(str(member))
                return members, key
        
        # Try partial match
        for key in teams.keys():
            if team_name.lower() in key.lower() or key.lower() in team_name.lower():
                team_data = teams[key]
                members = []
                for member in team_data.get("members", []):
                    if isinstance(member, dict):
                        members.append(member.get("name", ""))
                    else:
                        members.append(str(member))
                return members, key
        
        return [], None

    def get_team_member_user_ids(self, team_name):
        """Get user IDs for team members from configuration"""
        teams = teams_conf.get("teams", {})
        
        # First try exact match
        if team_name in teams:
            team_data = teams[team_name]
            user_ids = []
            
            for member in team_data.get("members", []):
                if isinstance(member, dict):
                    user_id = member.get("user_id")
                    if user_id:
                        user_ids.append(user_id)
            
            return user_ids, [], team_name
        
        # Try case-insensitive match
        for key in teams.keys():
            if key.lower() == team_name.lower():
                team_data = teams[key]
                user_ids = []
                
                for member in team_data.get("members", []):
                    if isinstance(member, dict):
                        user_id = member.get("user_id")
                        if user_id:
                            user_ids.append(user_id)
                
                return user_ids, [], key
        
        # Try partial match
        for key in teams.keys():
            if team_name.lower() in key.lower() or key.lower() in team_name.lower():
                team_data = teams[key]
                user_ids = []
                
                for member in team_data.get("members", []):
                    if isinstance(member, dict):
                        user_id = member.get("user_id")
                        if user_id:
                            user_ids.append(user_id)
                
                return user_ids, [], key
        
        return [], [], None

    def find_matching_teams(self, partial_name):
        """Find teams that match a partial name"""
        teams = teams_conf.get("teams", {})
        matching_teams = []
        
        for team_name in teams.keys():
            if partial_name.lower() in team_name.lower():
                matching_teams.append(team_name)
        
        return matching_teams

    def escape_messageml(self, text):
        """Escape special characters for MessageML"""
        if not text:
            return text
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

    async def process_single_team(self, streamid, originator, botuserid, team_name, context):
        """Process a single team mention"""
        try:
            # Get team members with fuzzy matching
            team_members, matched_team_name = self.get_team_members(team_name)

            if not team_members:
                # Try to find similar team names
                similar_teams = self.find_matching_teams(team_name)
                if similar_teams:
                    await self.show_similar_teams(streamid, team_name, similar_teams)
                else:
                    # Escape special characters for MessageML
                    escaped_team_name = self.escape_messageml(team_name)
                    await self._messages.send_message(streamid, f"<messageML>{originator}, Team '{escaped_team_name}' not found. Use @{context.bot_display_name} /team to see available teams.</messageML>")
                return

            # Get user IDs directly from configuration (new approach)
            user_ids_from_config, member_names_needing_lookup, matched_team_name = self.get_team_member_user_ids(team_name)

            logging.info(f"Processing team mention for '{matched_team_name}' with {len(team_members)} team members")
            logging.info(f"Found {len(user_ids_from_config)} user IDs from configuration: {user_ids_from_config}")

            try:
                roominfo = await self._streams.get_room_info(streamid)
                roomname = html.escape(roominfo['room_attributes']['name'])
            except:
                roomname = streamid

            # Only use user IDs from configuration - no name-based lookup
            all_user_ids = user_ids_from_config

            logging.info(f"All user IDs to process: {all_user_ids}")

            if not all_user_ids:
                # Escape special characters for MessageML
                escaped_team_name = self.escape_messageml(matched_team_name)
                await self._messages.send_message(streamid, f"<messageML>{originator}, Could not find any users for team '{escaped_team_name}'. Please check the team configuration and add user IDs.</messageML>")
                return

            # Separate team members who are in the room vs not in the room
            room_members_response = await self._streams.list_room_members(streamid)
            room_member_ids = [member.id for member in room_members_response.value]

            logging.info(f"Room member IDs: {room_member_ids}")

            team_members_in_room = []
            team_members_not_in_room = []

            # Use a set to track processed user IDs to avoid duplicates
            processed_user_ids = set()

            for user_id in all_user_ids:
                if str(user_id) == str(botuserid) or str(user_id) == str(context.initiator.user.user_id):
                    logging.debug(f"ignored id: {user_id}")
                    continue

                # Skip if we've already processed this user ID
                if user_id in processed_user_ids:
                    logging.debug(f"skipping duplicate user id: {user_id}")
                    continue

                processed_user_ids.add(user_id)

                if user_id in room_member_ids:
                    team_members_in_room.append(user_id)
                else:
                    team_members_not_in_room.append(user_id)

            logging.info(f"Final results - Team members in room: {team_members_in_room}")
            logging.info(f"Final results - Team members not in room: {team_members_not_in_room}")

            # Mention team members who are in the room directly
            if team_members_in_room:
                try:
                    mentions = " ".join([f'<mention uid="{user_id}"/>' for user_id in team_members_in_room])
                    escaped_team_name = self.escape_messageml(matched_team_name)
                    room_mention_message = f"<messageML>{originator} has mentioned team '{escaped_team_name}' members: {mentions}</messageML>"
                    await self._messages.send_message(streamid, room_mention_message)
                    logging.info(f"Mentioned {len(team_members_in_room)} team members who are in the room")
                except Exception as e:
                    logging.warning(f"Failed to send room mention message: {e}")
                    # Send a simpler message without mentions
                    escaped_team_name = self.escape_messageml(matched_team_name)
                    simple_message = f"<messageML>{originator} has mentioned team '{escaped_team_name}' members who are in the room.</messageML>"
                    await self._messages.send_message(streamid, simple_message)
                    logging.info(f"Sent simple mention message for team '{escaped_team_name}'")

            # Send individual messages to team members who are not in the room
            successful_ims = 0
            failed_ims = 0
            invalid_user_ids = []

            # Get the names of team members not in the room for the card
            team_members_not_in_room_names = []

            for user_id in team_members_not_in_room:
                try:
                    # Get user details to display their name
                    user_detail = await self._users.get_user_detail(user_id)
                    user_attributes = user_detail.get("user_attributes", {})
                    first_name = user_attributes.get("first_name", "Unknown")
                    last_name = user_attributes.get("last_name", "Unknown")
                    display_name = user_attributes.get("display_name", f"{first_name} {last_name}")

                    team_members_not_in_room_names.append(display_name)

                    # Create IM and send notification
                    try:
                        createIM = (await self._streams.create_im_or_mim([int(user_id)]))['id']
                        # createIM = (await self._streams.create_im([int(user_id)]))['id'] # PBDK 2.11.0
                        logging.debug(f"createIM: {createIM}")

                        # Construct the message with the correct user mention
                        escaped_team_name = self.escape_messageml(matched_team_name)
                        blastmessage = f'''Hi, <mention uid="{str(context.initiator.user.user_id)}"/> has @mentioned you, <mention uid="{str(user_id)}"/>, in <b><i>{roomname}</i></b> as part of team '{escaped_team_name}' <a href="https://open.symphony.com/?streamId={str(streamid).replace("-", "%2B").replace("_", "%2F")}%3D%3D&#38;messageId={str(context.message_id).replace("-", "%2B").replace("_", "%2F")}%3D%3D"><b>View message now</b></a>'''

                        # Send the message to the corresponding stream ID
                        await self._messages.send_message(createIM, Message(content=blastmessage, data=None, attachments=None))
                        successful_ims += 1
                        logging.info(f"Successfully sent IM to user {user_id}")

                    except Exception as e:
                        failed_ims += 1
                        logging.warning(f"Failed to send IM to user {user_id}: {e}")
                        # Continue with other users instead of crashing
                        continue

                except Exception as e:
                    # Check if this is an invalid user ID error (HTTP 400)
                    error_str = str(e)
                    if "400" in error_str and "Invalid user" in error_str:
                        invalid_user_ids.append(user_id)
                        logging.warning(f"Invalid user ID in configuration: {user_id}")
                    else:
                        failed_ims += 1
                        logging.warning(f"Failed to get user details for {user_id}: {e}")
                        # Add a placeholder name for other types of errors
                        team_members_not_in_room_names.append(f"User {user_id}")
                    continue

            logging.info(f"Sent IMs to {successful_ims} team members, failed for {failed_ims} members")

            # Create a card for team members not in the room (to reduce noise)
            if team_members_not_in_room_names or invalid_user_ids:
                try:
                    escaped_team_name = self.escape_messageml(matched_team_name)
                    total_mentioned = len(team_members_in_room) + successful_ims
                    
                    # Determine card accent color based on content
                    if invalid_user_ids:
                        card_accent = "tempo-bg-color--red"  # Red for configuration errors
                        card_title = "Team Configuration Issues"
                    else:
                        card_accent = "tempo-bg-color--orange"  # Orange for normal not-in-room
                        card_title = "Team Members Not in Room"
                    
                    card_message = f'''<card accent='{card_accent}' iconSrc=''>
                        <header><h2>{card_title}</h2></header>
                        <body>'''

                    if invalid_user_ids:
                        # Show invalid user IDs as configuration errors
                        card_message += f'''<p><b>{originator}</b> has mentioned team '<b>{escaped_team_name}</b>', but the following user IDs in the configuration are <b>invalid</b>:</p>
                            <ul>'''
                        
                        for user_id in invalid_user_ids:
                            card_message += f"<li><b>User ID {user_id}</b> (Invalid - please check configuration)</li>"
                        
                        card_message += f'''</ul>
                            <p><i>These invalid user IDs need to be corrected in the teams.yaml configuration file.</i></p>'''
                        
                        if team_members_not_in_room_names:
                            card_message += f'''<p><b>Additionally, these team members are not in this room:</b></p>
                                <ul>'''
                            
                            for name in team_members_not_in_room_names:
                                escaped_name = self.escape_messageml(name)
                                card_message += f"<li><b>{escaped_name}</b></li>"
                            
                            card_message += f'''</ul>
                                <p><i>Found {total_mentioned} team members ({len(team_members_in_room)} in room, these {len(team_members_not_in_room_names)} team members have been notified individually)</i></p>'''
                    else:
                        # Normal case - just team members not in room
                        card_message += f'''<p><b>{originator}</b> has mentioned team '<b>{escaped_team_name}</b>' members who are <b>not in this room</b>:</p>
                            <ul>'''

                        for name in team_members_not_in_room_names:
                            escaped_name = self.escape_messageml(name)
                            card_message += f"<li><b>{escaped_name}</b></li>"

                        card_message += f'''</ul>
                            <p><i>Found {total_mentioned} team members ({len(team_members_in_room)} in room, these {len(team_members_not_in_room_names)} team members have been notified individually)</i></p>'''

                    card_message += f'''</body>
                    </card>'''

                    await self._messages.send_message(streamid, f"<messageML>{card_message}</messageML>")
                    logging.info(f"Sent card with {len(team_members_not_in_room_names)} team members not in room and {len(invalid_user_ids)} invalid user IDs")
                except Exception as e:
                    logging.warning(f"Failed to send card message: {e}")
                    # Send a simpler message
                    try:
                        escaped_team_name = self.escape_messageml(matched_team_name)
                        if invalid_user_ids:
                            simple_message = f"<messageML>{originator} has mentioned team '{escaped_team_name}', but some user IDs in the configuration are invalid. Please check the teams.yaml file.</messageML>"
                        else:
                            simple_message = f"<messageML>{originator} has mentioned team '{escaped_team_name}' members who are not in this room.</messageML>"
                        await self._messages.send_message(streamid, simple_message)
                    except Exception as e2:
                        logging.error(f"Failed to send even simple not-in-room message: {e2}")

            # Final confirmation message removed to reduce noise
            logging.info(f"Team mention completed for '{matched_team_name}'. Found {len(team_members_in_room) + successful_ims} team members ({len(team_members_in_room)} in room, {successful_ims} notified individually)")

        except Exception as ex:
            logging.error(f"Error processing team '{team_name}': {ex}")
            logging.exception("Team processing exception")

    async def show_available_teams(self, streamid):
        """Show available teams in a formatted message"""
        teams = teams_conf.get("teams", {})
        
        if not teams:
            await self._messages.send_message(streamid, "<messageML>No teams configured.</messageML>")
            return
        
        teams_list = "<card accent='tempo-bg-color--blue' iconSrc=''> \
                        <header><h2>Available Teams</h2></header> \
                        <body> \
                          <p>Use @MentionBot /team [Team Name] to mention a specific team:</p> \
                          <ul>"
        
        for team_name in teams.keys():
            # Escape special characters for MessageML
            escaped_team_name = self.escape_messageml(team_name)
            teams_list += f"<li><b>{escaped_team_name}</b></li>"
        
        teams_list += "</ul></body></card>"
        
        await self._messages.send_message(streamid, f"<messageML>{teams_list}</messageML>")

    async def show_similar_teams(self, streamid, search_term, similar_teams):
        """Show similar teams when exact match is not found"""
        # Escape special characters for MessageML
        escaped_search_term = self.escape_messageml(search_term)
        teams_list = f"<card accent='tempo-bg-color--orange' iconSrc=''> \
                        <header><h2>Team Not Found</h2></header> \
                        <body> \
                          <p>Team '{escaped_search_term}' not found. Did you mean one of these?</p> \
                          <ul>"
        
        for team_name in similar_teams:
            # Escape special characters for MessageML
            escaped_team_name = self.escape_messageml(team_name)
            teams_list += f"<li><b>{escaped_team_name}</b></li>"
        
        teams_list += "</ul></body></card>"
        
        await self._messages.send_message(streamid, f"<messageML>{teams_list}</messageML>")

    async def debug_room_members(self, streamid):
        """Debug function to show room member structure"""
        try:
            room_members_response = await self._streams.list_room_members(streamid)
            room_member_ids = [member.id for member in room_members_response.value]
            
            debug_info = f"<card accent='tempo-bg-color--red' iconSrc=''> \
                            <header><h2>Room Member Debug Info</h2></header> \
                            <body> \
                              <p>Found {len(room_member_ids)} members in room</p>"
            
            if room_member_ids:
                # Show first few member IDs and their details
                debug_info += f"<p><b>First 5 member IDs:</b> {room_member_ids[:5]}</p>"
                
                # Get details for first member as example
                try:
                    first_user_detail = await self._users.get_user_detail(room_member_ids[0])
                    user_attributes = first_user_detail.get("user_attributes", {})
                    display_name = user_attributes.get("display_name", "Unknown")
                    first_name = user_attributes.get("first_name", "Unknown")
                    last_name = user_attributes.get("last_name", "Unknown")
                    
                    debug_info += f"<p><b>First member details:</b></p>"
                    debug_info += f"<p>- Display Name: {display_name}</p>"
                    debug_info += f"<p>- First Name: {first_name}</p>"
                    debug_info += f"<p>- Last Name: {last_name}</p>"
                    debug_info += f"<p>- ID: {room_member_ids[0]}</p>"
                    
                    # Show name combinations that would be checked
                    name_combinations = []
                    if display_name:
                        name_combinations.append(display_name)
                    if first_name and last_name:
                        name_combinations.append(f"{first_name} {last_name}")
                        name_combinations.append(f"{last_name} {first_name}")
                    if first_name:
                        name_combinations.append(first_name)
                    if last_name:
                        name_combinations.append(last_name)
                    
                    debug_info += f"<p><b>Name combinations checked:</b> {name_combinations}</p>"
                    
                except Exception as e:
                    debug_info += f"<p><b>Error getting first member details:</b> {str(e)}</p>"
                
                # Show how many team members we're looking for
                debug_info += f"<p><b>Looking for team members:</b> Mario Orphanou, Jonathan Zhou, Shohei Shida, PF Vilquin</p>"
            
            debug_info += "</body></card>"
            
            await self._messages.send_message(streamid, f"<messageML>{debug_info}</messageML>")
            
        except Exception as e:
            error_msg = f"<messageML>Error getting room members: {str(e)}</messageML>"
            await self._messages.send_message(streamid, error_msg)
