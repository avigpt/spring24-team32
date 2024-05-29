# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from manual import ManualReview
from report import Category
import pdb
from detection import detect_sextortion

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        # Add reactions
        intents.reactions = True
        self.group_32_guild_id = 1211760623969370122
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.reports_to_review = {} # Map from message_id in mod channel to respective report
        self.mod_channel = None
        self.manual_review = None # Current instance of ManualReview. It is None until report is complete

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        # ADDED: Populates mod_channel attribute
        self.mod_channel = self.mod_channels[self.group_32_guild_id]
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Make report based on the detection result. 
        if await detect_sextortion(message, "gemini") == True:
            print("Sextortion detected. Creating report.")
            if author_id not in self.reports:
                self.reports[author_id] = Report(self)
            responses = await self.reports[author_id].handle_sextortion_detection(message)

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)


        # If the report is complete or cancelled, remove it from our map and add it to reports to review
        if self.reports[author_id].report_cancelled():
            self.reports.pop(author_id)


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # # Forward the message to the mod channel
        # mod_channel = self.mod_channels[message.guild.id]
        # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        # scores = self.eval_text(message.content)
        # await mod_channel.send(self.code_format(scores))

    # ADDED: This event handler detects when a reaction is made and if the author is reporting
    # TODO: Add message checking on author_id to fix double message problem 
    async def on_raw_reaction_add(self, reaction):
        author_id = reaction.user_id
        message_id = reaction.message_id

        # Intialization the manual review flow
        if message_id in self.reports_to_review and reaction.emoji.name == "1️⃣" and self.manual_review == None:
            report_data = self.reports_to_review.pop(message_id)
            await self.mod_channel.send(
                "Current " + self.format_report(report_data)
            )
            self.manual_review = ManualReview(self, report_data, self.mod_channel)
            await self.manual_review.perform_manual_review(reaction)
        # Continuation of manual review flow
        elif self.manual_review and self.group_32_guild_id == reaction.guild_id and author_id != self.user.id:
            is_review_complete = await self.manual_review.perform_manual_review(reaction)
            if is_review_complete: # reset self.manual_review
                self.manual_review = None
        # Otherwise report flow is handled
        elif author_id in self.reports:
            await self.reports[author_id].handle_reaction(reaction)

        # When the report is complete it is removed from self.reports and the data is sent to self.reports_to_review
        # The mod channel then gets forwarded the data and is given the option to review it.
        if author_id in self.reports and self.reports[author_id].report_complete() and not self.reports[author_id].report_cancelled():
            report = self.reports.pop(author_id)
            # Adds urgent report to sexual threat or danger reports
            accept_message = "===========================\nPress 1️⃣ to accept and review this report."
            if report.report_data["category"] != Category.DANGER and report.report_data["category"] != Category.SEXUAL_THREAT:
                report_message = await self.mod_channel.send(self.format_report(report.report_data) + "\n" + accept_message)
            else:
                report_message = await self.mod_channel.send("‼️Urgent Report‼️\n" + self.format_report(report.report_data) + "\n" + accept_message)
            # Add reactions
            await report_message.add_reaction("1️⃣")
            self.reports_to_review[report_message.id] = report.report_data

# Helper functions

    def format_report(self, report_data):
        '''
        This function takes in report_data and formats it so that it can be displayed
        for moderators before the select to review it.
        '''
        if report_data["category"] == Category.SEXUAL_THREAT:
            return self.format_sexual_threat(report_data)
        elif report_data["category"] == Category.OFFENSIVE_CONTENT:
            return self.format_offesive_content(report_data)
        elif report_data["category"] == Category.SPAM_SCAM:
            return self.format_spam_scam(report_data)    
        elif report_data["category"] == Category.DANGER:
            return self.format_danger(report_data)

    def format_sexual_threat(self, report_data):
        '''
        Format function for sexual threat reports
        '''
        reply = "Report Summary\n" + \
                "===========================\n"
        
        reply += "Abuse Type: Sexual Threat Content\n"
        reply += f'Reported User: {report_data["name"]}\n'
        reply += f'Message: {report_data["content"]}\n'
        reply += f'Demand Made: {report_data["demand"]}\n'
        reply += f'Threat Made: {report_data["threat"]}\n'
        reply += "Addtional Content: NONE" if report_data["context"] == "No" else f'Addtional Content: {report_data["context_content"]}'
        return reply
    
    def format_offesive_content(self, report_data):
        '''
        Format function for offensive content reports
        '''
        reply = "Report Summary\n" + \
                "===========================\n"
        
        reply += "Abuse Type: Offensive Content\n"
        reply += f'Reported User: {report_data["name"]}\n'
        reply += f'Message: {report_data["content"]}\n'
        reply += f'Offensive Content Type: {report_data["offensive_content_type"]}'

        return reply
    def format_spam_scam(self, report_data):
        '''
        Format function for spam/scam reports
        '''
        reply = "Report Summary\n" + \
                "===========================\n"
        
        reply += "Abuse Type: Spam/Scam Content\n"
        reply += f'Reported User: {report_data["name"]}\n'
        reply += f'Message: {report_data["content"]}\n'
        reply += f'Spam/Scam Content Type: {report_data["spam_scam_content_type"]}'

        return reply
    def format_danger(self, report_data):
        '''
        Format function for danger reports
        '''
        reply = "Report Summary\n" + \
                "===========================\n"
        
        reply += "Abuse Type: Imminent Danger Content\n"
        reply += f'Reported User: {report_data["name"]}\n'
        reply += f'Message: {report_data["content"]}\n'
        reply += f'Imminent Danger Type: {report_data["danger_type"]}\n'
        if "safety_threat_type" in report_data:
            reply += f'Safety Threat Type: {report_data["safety_threat_type"]}'
        elif "criminal_behavior_type" in report_data:
            reply += f'Criminal Behavior Type: {report_data["criminal_behavior_type"]}'

        return reply

    def category_to_string(self):
        '''
        Convert states in Category to strings
        '''
        if self.review_data["category"] == Category.SEXUAL_THREAT:
            return "Sexual Threat"
        elif self.review_data["category"] == Category.OFFENSIVE_CONTENT:
            return "Offensive Content"
        elif self.review_data["category"] == Category.SPAM_SCAM:
            return "Spam/Scam"
        elif self.review_data["category"] == Category.DANGER:
            return "Danger"
        else:
            return "Unknown"

    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)