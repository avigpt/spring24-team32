from enum import Enum, auto
import asyncio
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    CLASSIFIED_1 = auto() # For first level of flow
    CLASSIFIED_2 = auto() # For second level of flow
    FURTHEST_IMPLEMENTATION = auto()

class Report():
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report_data = {} # Keeps track of report's message, the person who sent it, and all report classifiers

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                reported_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            self.state = State.MESSAGE_IDENTIFIED
            # ADDED: Sends a message with the instructions for classifying part 1
            reaction_message = await message.channel.send(
                "This is the author and their message we found:" + "```" + reported_message.author.name + ": " + reported_message.content + "```" +
                "\nWhy are you reporting this message?\n" +
                "1️⃣: Sexual Threat\n" +
                "2️⃣: Offensive Content\n" +
                "3️⃣: Spam/Scam\n" +
                "4️⃣: Imminent Danger\n"
            )

            self.report_data["name"] = reported_message.author.name
            self.report_data["content"] = reported_message.content

            # Add reactions
            await reaction_message.add_reaction("1️⃣")
            await reaction_message.add_reaction("2️⃣")
            await reaction_message.add_reaction("3️⃣")
            await reaction_message.add_reaction("4️⃣")

            return []
        if self.state == State.FURTHEST_IMPLEMENTATION:
            return [f"This is the furthest the bot has been implemented.\nCurrent Report: {self.report_data}"]
        return []

    # TODO: Function that handles reactions. 
    # When a reaction is sent to a report bot.py routes that logic here (refer to on_raw_reaction_add() in bot.py).
    # It first classifies identified messages and then goes layer by layer following the user flow. Each if/elif clause
    # captures the following step in the user flow and is represented by State constant.

    # Things are in the past tense. So State.MESSAGE_INDENTIFIED means that classifying part 1 is being worked on. State.CLASSIFIED_1 means
    # classifying part 1 is done and classifying part 2 is happening. I (Cristobal) did not make this convention it is part of the assignment.
    async def handle_reaction(self, reaction):
        # TODO: All of them call self.reply_sexual_threat because that is the only classifying part 2 function implemented. 
        # They should all call their respective reply functions.
        if self.state == State.MESSAGE_IDENTIFIED: # Classifying Part 1
            if reaction.emoji.name == "1️⃣":
                self.report_data["report_reason"] = "Sexual Threat"
                await self.reply_sexual_threat(reaction)
            elif reaction.emoji.name == "2️⃣":
                self.report_data["report_reason"] = "Offensive Content"
                await self.reply_offensive_content(reaction)
            elif reaction.emoji.name == "3️⃣":
                self.report_data["report_reason"] = "Spam/Scam"
                await self.reply_scam_spam_content(reaction)
            elif reaction.emoji.name == "4️⃣":
                return
            else:
                return
            self.state = State.CLASSIFIED_1

        elif self.state == State.CLASSIFIED_1: # Classifying Part 2
            if self.report_data["report_reason"] == "Sexual Threat":
                await self.classify_sexual_threat(reaction)
            elif self.report_data["report_reason"] == "Offensive Content":
                await self.classify_offensive_content(reaction)
            elif self.report_data["report_reason"] == "Spam/Scam": 
                await self.classify_spam_scam_content(reaction)
            else:
                return #TODO: Update based on the other classifications.
            self.state = State.FURTHEST_IMPLEMENTATION
            
    ################################################################################################
    # Below is the code that makes all the function calls for each respective classification, which is 
    # called above when the user specifies why they are reporting the content. 
    ################################################################################################
    
    # TODO: Sends the message that asks to classify Sexual Threats
    # This is the second classification for Sexual Threats. All classifications will need
    # a classification like this
    async def reply_sexual_threat(self, reaction):
        channel = await self.client.fetch_channel(reaction.channel_id)

        # Request further details.
        cont = await self.sender_demand(channel)
        if not cont: return
        await self.sender_threat(channel)

    # TODO: All of these need to be implemented to mimic the branching in the user flow and
    # send out messages. reply_sexual_threat() is an example.
    async def reply_offensive_content(self, reaction):
        channel = await self.client.fetch_channel(reaction.channel_id)
        
        # Request further details.
        cont = await self.offensive_content_type(channel)
        # TODO: do we need to store the type of content they specified? As of now, it just detects if the 
        # user specifies a content type and then immediately displays the message below
        reply = "The content moderation team will review the content. Further actions may include removal of the post and/or account."
        await channel.send(reply)
        
    async def reply_scam_spam_content(self, reaction):
        channel = await self.client.fetch_channel(reaction.channel_id)
        
        # Request further details.
        cont = await self.spam_scam_content_type(channel)
        reply = "The content moderation team will review the content. Further actions may include removal of the post and/or account."
        await channel.send(reply)
        
    async def reply_imminent_danger_content(self, reaction):
        pass
    
    ################################################################################################
    # Below is code for the Offensive Content classification:
    ################################################################################################
    
    # Called for "Offensive Content" classification to understand the type of content seen.
    async def offensive_content_type(self, channel): 
        reply = "Selected Category: "
        reply += "Offensive Content"
        await channel.send(reply)
        
        content_message = await channel.send(
            "Please select the type of offensive content.\n"
            "1️⃣: Violent Content\n" +
            "2️⃣: Hateful Content\n" +
            "3️⃣: Pornography\n"
        )
        
        await content_message.add_reaction("1️⃣")
        await content_message.add_reaction("2️⃣")
        await content_message.add_reaction("3️⃣")
        
        try:
            reaction = await self.client.wait_for('reaction_add', check = None, timeout = 30.0)
            if reaction[0].emoji == "1️⃣":
                self.report_data["offensive_content_type"] = "Violent Content"
                print(self.report_data)
            elif reaction[0].emoji == "2️⃣":
                self.report_data["offensive_content_type"] = "Hateful Content"
            elif reaction[0].emoji == "3️⃣":
                self.report_data["offensive_content_type"] = "Pornography"
            else: 
                return False
        except asyncio.TimeoutError:
            await channel.send("No reaction detected. Cancelling report.")
            self.state = State.REPORT_COMPLETE
            return False
        return True
    
    
    ################################################################################################
    # Below is the code for the Spam/Scam classification
    ################################################################################################
    
    # Called for "Spam/Scam" classification to understand the type of content seen.
    async def spam_scam_content_type(self, channel): 
        reply = "Selected Category: "
        reply += "Spam/Scam"
        await channel.send(reply)
        
        content_message = await channel.send(
            "Please select the type of spam/scam.\n"
            "1️⃣: Spam\n" +
            "2️⃣: Fraud\n" +
            "3️⃣: Impersonation or Fake Account\n"
        )
        
        await content_message.add_reaction("1️⃣")
        await content_message.add_reaction("2️⃣")
        await content_message.add_reaction("3️⃣")
        
        try:
            reaction = await self.client.wait_for('reaction_add', check = None, timeout = 30.0)
            if reaction[0].emoji == "1️⃣":
                self.report_data["spam_scam_content_type"] = "Spam"
                print(self.report_data)
            elif reaction[0].emoji == "2️⃣":
                self.report_data["spam_scam_content_type"] = "Fraud"
            elif reaction[0].emoji == "3️⃣":
                self.report_data["spam_scam_content_type"] = "Impersonation or Fake Account"
            else: 
                return False
        except asyncio.TimeoutError:
            await channel.send("No reaction detected. Cancelling report.")
            self.state = State.REPORT_COMPLETE
            return False
        return True
        
    
    ################################################################################################
    # Below is the code for the Sexual Threat classification
    ################################################################################################

    # Called for "Sexual Threat" classification to understand sender's demand. 
    async def sender_demand(self, channel):
        reply = "Selected Category: "
        reply += "Sexual Threat"
        await channel.send(reply)

        demand_message = await channel.send(
            "What is the sender's demand? \n"
            "1️⃣: Nude Content\n" +
            "2️⃣: Financial Payment\n" +
            "3️⃣: Sexual Service\n" +
            "4️⃣: Other\n"
        )
        await demand_message.add_reaction("1️⃣")
        await demand_message.add_reaction("2️⃣")
        await demand_message.add_reaction("3️⃣")
        await demand_message.add_reaction("4️⃣")

        try:
            reaction = await self.client.wait_for('reaction_add', check = None, timeout = 30.0)
            if reaction[0] == "1️⃣":
                self.report_data["sender_demand"] = "Nude Content"
                print(self.report_data)
            elif reaction[0] == "2️⃣":
                self.report_data["sender_demand"] = "Financial Payment"
            elif reaction[0] == "3️⃣":
                self.report_data["sender_demand"] = "Sexual Service"
            elif reaction[0] == "4️⃣":
                self.report_data["sender_demand"] = "Other"
            else: 
                return False
        except asyncio.TimeoutError:
            await channel.send("No reaction detected. Cancelling report.")
            self.state = State.REPORT_COMPLETE
            return False
        return True
    
    # Called for "Sexual Threat" classification to understand sender's threat.
    async def sender_threat(self, channel):
        threat_message = await channel.send(
            "Got it, thanks. One more question: what is the sender's threat? \n"
            "1️⃣: Physical Threat \n" +
            "2️⃣: Release Sensitive or Explicit Material \n" +
            "3️⃣: Unclear \n"
        )
        await threat_message.add_reaction("1️⃣")
        await threat_message.add_reaction("2️⃣")
        await threat_message.add_reaction("3️⃣")

        try:
            reaction = await self.client.wait_for('reaction_add', check = None, timeout = 30.0)
            if reaction.emoji.name == "1️⃣":
                self.report_data["sender_threat"] = "Physical Threat"
            elif reaction.emoji.name == "2️⃣":
                self.report_data["sender_threat"] = "Release Sensitive or Explicit Material"
            elif reaction.emoji.name == "3️⃣":
                self.report_data["sender_threat"] = "Unclear"
            else:
                return
        except asyncio.TimeoutError:
            await channel.send("No reaction detected. Please select one of the options or type 'cancel'.")
            
    
        
    # ADDED: Current just sends a message saying that this is the furthest implementation
    # Should classify between Nude Content and Financial Payment
    
    # Note from Riley: it's still unclear to me when the "this is the furthest..." message gets called?
    async def classify_sexual_threat(self, reaction):
        channel = await self.client.fetch_channel(reaction.channel_id)
        await channel.send(f"This is the furthest the bot has been implemented.\nCurrent Report: {self.report_data}")

    async def classify_offensive_content(self, reaction):
        channel = await self.client.fetch_channel(reaction.channel_id)
        await channel.send(f"This is the furthest the bot has been implemented.\nCurrent Report: {self.report_data}")
    
    async def classify_spam_scam_content(self, reaction):
        channel = await self.client.fetch_channel(reaction.channel_id)
        await channel.send(f"This is the furthest the bot has been implemented.\nCurrent Report: {self.report_data}")

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

