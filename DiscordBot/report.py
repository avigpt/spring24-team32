from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    CATEGORY_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

class Level(Enum):
    L1 = auto()
    L2 = auto()
    L3 = auto()

class Category(Enum):
    SEXUAL_THREAT = auto()
    OFFENSIVE_CONTENT = auto()
    SPAM_SCAM = auto()
    DANGER = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.level = Level.L1
        self.client = client
        self.message = None
        self.report_data = {}
        self.canceled = False # A flag for if the report was canceled. Used to prevent canceled reports from going to review.

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            self.canceled = True
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
                fetched_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message
            self.report_data["name"] = fetched_message.author.name
            self.report_data["content"] = fetched_message.content
            self.state = State.MESSAGE_IDENTIFIED
            await self.reply_message_id(message, fetched_message)

        return []
    
    async def reply_message_id(self, message, fetched_message):
        '''
        Called in State: MESSAGE_IDENTIFIED.
        This function asks the user to categorize the message. 
        '''
        reaction_message = await message.channel.send(
            "We found this author and message:" + "```" + fetched_message.author.name + ": " + fetched_message.content + "```" +
            "\nWhy are you reporting this message?\n" +
            "1️⃣: Sexual Threat\n" +
            "2️⃣: Offensive Content\n" +
            "3️⃣: Spam/Scam\n" +
            "4️⃣: Imminent Danger\n"
            )

        # Add reactions
        await reaction_message.add_reaction("1️⃣")
        await reaction_message.add_reaction("2️⃣")
        await reaction_message.add_reaction("3️⃣")
        await reaction_message.add_reaction("4️⃣")

    async def handle_reaction(self, reaction):
        '''
        This function is called whenever a reaction is added to a message.
        It is first called in state MESSAGE_IDENTIFIED. 
        '''
        channel = await self.client.fetch_channel(reaction.channel_id)

        if self.state == State.MESSAGE_IDENTIFIED:
            await channel.send(await self.store_category(reaction))
            self.state = State.CATEGORY_IDENTIFIED
        # Now, we ask follow-up questions based on the category.

        ## Category: Sexual Threat ##
        if self.report_data["category"] == Category.SEXUAL_THREAT:
            if self.level == Level.L1:
                await self.sexual_threat_l1(reaction, channel) 
                self.level = Level.L2
            elif self.level == Level.L2:
                await channel.send(await self.store_demand(reaction))
                await self.sexual_threat_l2(reaction, channel)
                self.level = Level.L3
            elif self.level == Level.L3:
                await channel.send(await self.store_threat(reaction))
                print("To do: ask to add further messages, etc.")
                print("Report so far: ", self.report_data)

        ## Category: Offensive Content ##
        elif self.report_data["category"] == Category.OFFENSIVE_CONTENT:
            print("To implement: Offensive Content flow.")

        ## Category: Spam/Scam ##
        elif self.report_data["category"] == Category.SPAM_SCAM:
            print("To implement: Spam/Scam flow.")

        ## Category: Danger ##
        elif self.report_data["category"] == Category.DANGER:
            print("To implement: Danger flow.")

        else:
            channel.send("Invalid reaction. Please answer the most recent question. Type 'cancel' to start over.")

    async def store_category(self, reaction):
        '''
        This function is called in state MESSAGE_IDENTIFIED.
        It stores the user's categorization and sets the category.
        '''
        if reaction.emoji.name == "1️⃣":
            self.report_data["category"] = Category.SEXUAL_THREAT
        elif reaction.emoji.name == "2️⃣":
            self.report_data["category"] = Category.OFFENSIVE_CONTENT
        elif reaction.emoji.name == "3️⃣":
            self.report_data["category"] = Category.SPAM_SCAM
        elif reaction.emoji.name == "4️⃣":
            self.report_data["category"] = Category.DANGER
        else:
            return "Invalid reaction. Please try again."
        
        return f"Thank you. We've logged the category as \"{self.category_to_string()}.\""
    
    async def sexual_threat_l1(self, reaction, channel):
        '''
        Called in category SEXUAL_THREAT and state L1.
        This function asks the user to provide more detail; specifically, for sender demand. 
        '''
        await channel.send("We have two clarification questions about the nature of the sexual threat.")

        demand_message = await channel.send(
            "First question: what is the sender demanding or asking for? \n"
            "1️⃣: Nude Content\n" +
            "2️⃣: Financial Payment\n" +
            "3️⃣: Sexual Service\n" +
            "4️⃣: Other\n"
        )
        await demand_message.add_reaction("1️⃣")
        await demand_message.add_reaction("2️⃣")
        await demand_message.add_reaction("3️⃣")
        await demand_message.add_reaction("4️⃣")
    
    async def store_demand(self, reaction):
        '''
        This function is called in category SEXUAL_THREAT and state L2.
        It stores the user's response to the demand question (L1). 
        '''
        if reaction.emoji.name == "1️⃣":
            self.report_data["demand"] = "Nude Content"
        elif reaction.emoji.name == "2️⃣":
            self.report_data["demand"] = "Financial Payment"
        elif reaction.emoji.name == "3️⃣":
            self.report_data["demand"] = "Sexual Service"
        elif reaction.emoji.name == "4️⃣":
            self.report_data["demand"] = "Other"
        else:
            return "Invalid reaction. Please try again."
        
        return f"Thank you. We've logged the demand as \"{self.report_data['demand']}\"."
    
    async def sexual_threat_l2(self, reaction, channel):
        '''
        Called in category SEXUAL_THREAT and state L2.
        This function asks the user to provide more detail; specifically, for sender threat. 
        '''
        threat_message = await channel.send(
            "Second question: what is the sender threatening to do? \n"
            "1️⃣: Physical Harm\n" +
            "2️⃣: Public Exposure\n" +
            "3️⃣: Unclear\n"
        )

        await threat_message.add_reaction("1️⃣")
        await threat_message.add_reaction("2️⃣")
        await threat_message.add_reaction("3️⃣")

    async def store_threat(self, reaction):
        '''
        This function is called in category SEXUAL_THREAT and state L3.
        It stores the user's response to the threat question (L2). 
        '''
        if reaction.emoji.name == "1️⃣":
            self.report_data["threat"] = "Physical Harm"
        elif reaction.emoji.name == "2️⃣":
            self.report_data["threat"] = "Public Exposure"
        elif reaction.emoji.name == "3️⃣":
            self.report_data["threat"] = "Unclear"
        else:
            return "Invalid reaction. Please try again."
        
        return f"Thank you. We've logged the threat as \"{self.report_data['threat']}\"."

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    

    ### Helper Functions ###

    def category_to_string(self):
        if self.report_data["category"] == Category.SEXUAL_THREAT:
            return "Sexual Threat"
        elif self.report_data["category"] == Category.OFFENSIVE_CONTENT:
            return "Offensive Content"
        elif self.report_data["category"] == Category.SPAM_SCAM:
            return "Spam/Scam"
        elif self.report_data["category"] == Category.DANGER:
            return "Danger"
        else:
            return "Unknown"
    


    

