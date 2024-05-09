from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    CATEGORY_IDENTIFIED = auto()
    BLOCK_USER = auto()
    REPORT_COMPLETE = auto()
    REPORT_CANCELLED = auto()

class Level(Enum):
    L1 = auto()
    L2 = auto()
    L3 = auto()
    L4 = auto()
    L5 = auto()

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

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            if self.state == State.REPORT_COMPLETE:
                return ["The report has already been completed."]
            self.state = State.REPORT_CANCELLED
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

        # Collect additional context for sexual threat reports.
        if self.state == State.CATEGORY_IDENTIFIED and self.report_data["category"] == Category.SEXUAL_THREAT and self.level == Level.L5:
            self.report_data["context_content"] = message.content
            await self.block_option(message.channel)

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
        if self.state == State.REPORT_COMPLETE:
            return ["The report has already been completed."]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            await channel.send(await self.store_category(reaction))
            self.state = State.CATEGORY_IDENTIFIED
        
        if self.state == State.BLOCK_USER:
            await self.complete_report(reaction, channel)
        
        ## Category: Sexual Threat ##
        if self.report_data["category"] == Category.SEXUAL_THREAT:
            if self.level == Level.L1:
                self.level = Level.L2
                await self.sexual_threat_l1(channel) 
            elif self.level == Level.L2:
                self.level = Level.L3
                await channel.send(await self.store_demand(reaction))
                await self.sexual_threat_l2(channel)
            elif self.level == Level.L3:
                self.level = Level.L4
                await channel.send(await self.store_threat(reaction))
                await self.sexual_threat_l3(channel)
            elif self.level == Level.L4:
                self.level = Level.L5
                await self.collect_context_decision(reaction, channel)
                # Context (if any) collected as a message. 

        ## Category: Offensive Content ##
        elif self.report_data["category"] == Category.OFFENSIVE_CONTENT:
            if self.level == Level.L1:
                self.level = Level.L2
                await self.offensive_content_l1(channel) 
            elif self.level == Level.L2:
                self.level = Level.L3
                await channel.send(await self.store_offensive_content_type(reaction))
                await self.block_option(channel)
                

        ## Category: Spam/Scam ##
        elif self.report_data["category"] == Category.SPAM_SCAM:
            if self.level == Level.L1:
                self.level = Level.L2
                await self.spam_scam_content_l1(channel) 
            elif self.level == Level.L2:
                self.level = Level.L3
                await channel.send(await self.store_spam_scam_content_type(reaction))
                await self.block_option(channel)

        ## Category: Danger ##
        elif self.report_data["category"] == Category.DANGER:
            if self.level == Level.L1:
                self.level = Level.L2
                await self.danger_l1(channel)
            elif self.level == Level.L2:
                self.level = Level.L3
                await channel.send(await self.collect_danger_type(reaction))
                if self.report_data["danger_type"] == "Safety Threat":
                    await self.danger_l2_threat(channel)        
                else: 
                    await self.danger_l2_criminal(channel)
            elif self.level == Level.L3: 
                self.level = Level.L4
                if self.report_data["danger_type"] == "Safety Threat":
                    await channel.send(await self.store_safety_threat_type(reaction))
                else: 
                    await channel.send(await self.store_criminal_behavior_type(reaction))
                await self.block_option(channel)
                
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
        
        return f"Thank you. We've logged the category as \"{self.category_to_string()}.\""
    
    ## Sexual Threat Flow ##
    async def sexual_threat_l1(self, channel):
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
        
        return f"Thank you. We've logged the demand as \"{self.report_data['demand']}\"."
    
    async def sexual_threat_l2(self, channel):
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
        
        return f"Thank you. We've logged the threat as \"{self.report_data['threat']}\"."


    async def sexual_threat_l3(self, channel):
        '''
        Called in category SEXUAL_THREAT and state L3.
        Asks user if they want to give additional context. 
        '''
        context_message = await channel.send(
            "Would you like to tell us anything else before submitting?\n"
            "✅: Yes\n" + 
            "❌: No\n"
        )
        await context_message.add_reaction("✅")
        await context_message.add_reaction("❌")

    async def collect_context_decision(self, reaction, channel):
        '''
        This function is called in category SEXUAL_THREAT and state L4.
        It stores the user's response to the context question (L3).
        The next user action if any is a message with additional context. 
        '''
        if reaction.emoji.name == "✅":
            self.report_data["context"] = "Yes"
            await channel.send("Please provide additional context in your next message. After you enter your message, we will submit the report.")
            
        elif reaction.emoji.name == "❌":
            self.report_data["context"] = "No"
            await self.block_option(channel)

    ## Danger Flow ##
    async def danger_l1(self, channel):
        '''
        Called in category DANGER and state L1.
        This function asks the user to provide more detail; specifically, for the nature of the danger. 
        '''
        danger_message = await channel.send(
            "If someone is in immediate danger, please get help before reporting. Don't wait.\n" +
            "When you are ready to continue, please select the nature of the danger.\n" +
            "1️⃣: Safety Threat\n" +
            "2️⃣: Criminal Behavior\n"
        )
        await danger_message.add_reaction("1️⃣")
        await danger_message.add_reaction("2️⃣")

    async def collect_danger_type(self, reaction):
        '''
        This function is called in category DANGER and state L2.
        It stores the user's response to the danger question (L1). 
        '''
        if reaction.emoji.name == "1️⃣":
            self.report_data["danger_type"] = "Safety Threat"
        elif reaction.emoji.name == "2️⃣":
            self.report_data["danger_type"] = "Criminal Behavior"
        
        return f"Thank you. We've logged the danger type as \"{self.report_data['danger_type']}\"."

    async def danger_l2_threat(self, channel):
        '''
        This function is called in category DANGER and state L2 if the user clicked Safety Threat.
        '''
        safety_message = await channel.send(
            "Please select the type of safety threat.\n" +
            "1️⃣: Suicide/Self-Harm\n" +
            "2️⃣: Violence\n"
        )
        await safety_message.add_reaction("1️⃣")
        await safety_message.add_reaction("2️⃣")
            
    async def danger_l2_criminal(self, channel):
        '''
        This function is called in category DANGER and state L2 if the user clicked Criminal Behavior.
        '''
        criminal_message = await channel.send(
            "Please select the type of criminal behavior.\n" +
            "1️⃣: Theft/Robbery\n" +
            "2️⃣: Child Abuse\n" +
            "3️⃣: Human Exploitation"
        )
        await criminal_message.add_reaction("1️⃣")
        await criminal_message.add_reaction("2️⃣")
        await criminal_message.add_reaction("3️⃣")
        
    async def store_safety_threat_type(self, reaction): 
        '''
        This function is called in category DANGER and state L3.
        It stores the user's response to the type of safety threat question (L2). 
        '''
        if reaction.emoji.name == "1️⃣":
            self.report_data["safety_threat_type"] = "Suicide/Self-Harm"
        elif reaction.emoji.name == "2️⃣":
            self.report_data["safety_threat_type"] = "Violence"
            
        return f"Thank you. We've logged the threat as \"{self.report_data['safety_threat_type']}\"."
    
    async def store_criminal_behavior_type(self, reaction): 
        '''
        This function is called in category DANGER and state L3.
        It stores the user's response to the type of criminal behavior question (L2). 
        '''
        if reaction.emoji.name == "1️⃣":
            self.report_data["criminal_behavior_type"] = "Theft/Robbery"
        elif reaction.emoji.name == "2️⃣":
            self.report_data["criminal_behavior_type"] = "Child Abuse"
        elif reaction.emoji.name == "3️⃣":
            self.report_data["criminal_behavior_type"] = "Human Exploitation"
            
        return f"Thank you. We've logged the threat as \"{self.report_data['criminal_behavior_type']}\"."
            
    
    ## Offensive Content ## 
    async def offensive_content_l1(self, channel): 
        content_message = await channel.send(
            "Please select the type of offensive content.\n"
            "1️⃣: Violent Content\n" +
            "2️⃣: Hateful Content\n" +
            "3️⃣: Pornography\n"
        )
        
        await content_message.add_reaction("1️⃣")
        await content_message.add_reaction("2️⃣")
        await content_message.add_reaction("3️⃣")
        
        
    async def store_offensive_content_type(self, reaction):
        '''
        This function is called in category OFFENSIVE_CONTENT and state L2.
        It stores the user's response to the type of offensive content question (L1). 
        '''
        if reaction.emoji.name == "1️⃣":
            self.report_data["offensive_content_type"] = "Violent Content"
        elif reaction.emoji.name == "2️⃣":
            self.report_data["offensive_content_type"] = "Hateful Content"
        elif reaction.emoji.name == "3️⃣":
            self.report_data["offensive_content_type"] = "Pornography"
        
        return f"Thank you. We've logged the threat as \"{self.report_data['offensive_content_type']}\"."
        
        
    ## Spam/Scam ##
    async def spam_scam_content_l1(self, channel): 
        content_message = await channel.send(
            "Please select the type of spam/scam.\n"
            "1️⃣: Spam\n" +
            "2️⃣: Fraud\n" +
            "3️⃣: Impersonation or Fake Account\n"
        )
        
        await content_message.add_reaction("1️⃣")
        await content_message.add_reaction("2️⃣")
        await content_message.add_reaction("3️⃣")
        
    async def store_spam_scam_content_type(self, reaction):
        '''
        This function is called in category SPAM_SCAM and state L2.
        It stores the user's response to the type of spam/scam content question (L1). 
        '''
        if reaction.emoji.name == "1️⃣":
            self.report_data["spam_scam_content_type"] = "Spam"
        elif reaction.emoji.name == "2️⃣":
            self.report_data["spam_scam_content_type"] = "Fraud"
        elif reaction.emoji.name == "3️⃣":
            self.report_data["spam_scam_content_type"] = "Impersonation or Fake Account"
        
        return f"Thank you. We've logged the threat as \"{self.report_data['spam_scam_content_type']}\"."
            
        
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
    
    def report_cancelled(self):
        return self.state == State.REPORT_CANCELLED

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
    async def block_option(self, channel):
        '''
        This is the last step; ask user if they want to block the author of the message.
        '''
        await channel.send("If you are not ready to submit at this point, please type 'cancel' to cancel the report now. \n")

        block_message = await channel.send(
            "One final question before we submit: would you like to block the author of the message?\n"
            "✅: Yes\n" + 
            "❌: No\n"
        )
        await block_message.add_reaction("✅")
        await block_message.add_reaction("❌")
        self.state = State.BLOCK_USER

    async def complete_report(self, reaction, channel):
        '''
        This function is called in state BLOCK_USER.
        It completes the report and sends the final message. 
        '''
        if reaction.emoji.name == "✅":
            self.report_data["block"] = "Yes"
            await channel.send("The author will be blocked.")
        elif reaction.emoji.name == "❌":
            self.report_data["block"] = "No"
            await channel.send("The author will not be blocked.")

        await channel.send("Thank you for your report. The content moderation team will decide the appropriate next steps given the severity of the content nature, including contacting crisis hotline, escalating to law enforcement, and/or removal of the post and/or account.")
        # await channel.send("Here is a summary of the report: " + str(self.report_data))
        self.state = State.REPORT_COMPLETE
