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
from manual import Category
import pdb

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

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        await mod_channel.send(self.code_format(scores))

    # ADDED: This event handler detects when a reaction is made and if the author is reporting
    # TODO: Add message checking on author_id to fix double message problem 
    async def on_raw_reaction_add(self, reaction):
        author_id = reaction.user_id
        message_id = reaction.message_id

        # Intialization the manual review flow
        if message_id in self.reports_to_review and reaction.emoji.name == "1️⃣" and self.manual_review == None:
            report_data = self.reports_to_review.pop(message_id)
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
            report_message = await self.mod_channel.send(
                f"New Report: {report.report_data}\n"
                "1️⃣: Review Report\n"
            )
            # Add reactions
            await report_message.add_reaction("1️⃣")
            self.reports_to_review[report_message.id] = report.report_data

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