from enum import Enum, auto
import discord
import re
from report import Category as ReportCategory

'''
Known issues that need to be addressed but should be ignored until flow is done:

0. When accepting a report it should repeat what report is being done.
1. Report reviews can only happen one at a time. If a second report is attempted to be reviewed it should not happen.
There is some logic on destroying ManualReview instances but it is not complete.
2. Reactions should only be valid if they were on the right message. This is currently only a problem in USER FLOW. 
The idea used was to keep track of a pointer to the message_id of the next message sent out and then return it to the client in
bot.py to use in on_raw_reaction_add().
4. Format incoming reports in group-32-mod channel. Show priority.
5. The severity 1 flow is simplifed to just return no abuse instead of checking for fake report and looping. Should revisit.
'''

class State(Enum):
    REVIEW_START = auto()
    AWAITING_ABUSE_IDENTIFICATION = auto()
    ABUSE_IDENTIFIED = auto()
    CATEGORY_IDENTIFIED = auto()
    REVIEW_COMPLETE = auto()

class Level(Enum):
    L1 = auto()
    L2 = auto()
    L3 = auto()

class Category(Enum):
    SEXUAL_THREAT = auto()
    OFFENSIVE_CONTENT = auto()
    SPAM_SCAM = auto()
    DANGER = auto()

class ManualReview:
    def __init__(self, client, report_data, mod_channel):
        self.state = State.REVIEW_START
        self.level = Level.L1
        self.client = client
        self.report_data = report_data
        self.mod_channel = mod_channel
        self.review_data = {}
        self.next_message_id = None # Used to keep track of the next message that needs reactions


    async def perform_manual_review(self, reaction):
        '''
        Core logic of the manual review. First the report is determined to be abuse or not. Then it is classified.
        TODO: Once classification is complete, self.level is used to fine-grain states.
        '''
        # Returns early if the reaction is not for the right message.
        if self.next_message_id != None and reaction.message_id != self.next_message_id:
            return False

        if self.state == State.REVIEW_START:
            await self.reply_legitimate_abuse()
            self.state = State.AWAITING_ABUSE_IDENTIFICATION
        elif self.state == State.AWAITING_ABUSE_IDENTIFICATION:
            abuse_found, is_abuse_message = await self.is_abuse(reaction)
            await self.mod_channel.send(is_abuse_message)
            # Might want to move this logic elsewhere
            if abuse_found:
                await self.reply_message_id()
                self.state = State.ABUSE_IDENTIFIED
            else:
                self.state = State.REVIEW_COMPLETE
        elif self.state == State.ABUSE_IDENTIFIED:
            await self.mod_channel.send(await self.store_category(reaction))
            self.state = State.CATEGORY_IDENTIFIED

        # Returns early if State.CATEGORY_IDENTIFIED is not the current state
        if self.state != State.CATEGORY_IDENTIFIED:
            return False
        
        # Runs once self.state is State.CATEGORY_INDENFIFIED
        if self.review_data["category"] == Category.SEXUAL_THREAT:
            if self.level == Level.L1: # asks specific sexual threat type
                await self.reply_sexual_threat_type()
                self.level = Level.L2
            elif self.level == Level.L2: # records response for specific sexual threat type + rate severity
                await self.mod_channel.send(await self.store_sexual_threat_type(reaction))
                await self.reply_severity()
                self.level = Level.L3
            elif self.level == Level.L3: # record severity 
                await self.mod_channel.send(await self.store_severity(reaction))
                self.state = State.REVIEW_COMPLETE

        elif self.review_data["category"] == Category.OFFENSIVE_CONTENT:
            if self.level == Level.L1:
                await self.reply_severity()
                self.level = Level.L2
            elif self.level == Level.L2:
                await self.mod_channel.send(await self.store_severity(reaction))
                self.state = State.REVIEW_COMPLETE

        elif self.review_data["category"] == Category.SPAM_SCAM:
            if self.level == Level.L1:
                await self.reply_severity()
                self.level = Level.L2
            elif self.level == Level.L2:
                await self.mod_channel.send(await self.store_severity(reaction))
                self.state = State.REVIEW_COMPLETE

        elif self.review_data["category"] == Category.DANGER:
            if self.level == Level.L1:
                await self.reply_severity()
                self.level = Level.L2
            elif self.level == Level.L2:
                await self.mod_channel.send(await self.store_severity(reaction))
                self.state = State.REVIEW_COMPLETE
        
        # Runs when Review is complete and it outputs the determined actions
        if self.state == State.REVIEW_COMPLETE:
            await self.mod_channel.send(await self.determine_action())
            return True

        return False

    async def reply_legitimate_abuse(self):
        '''
        This function is called in state AWAITING_ABUSE_IDENTIFICATION.
        It asks the question of whether the message is legitimate abuse AKA is the report real.
        '''
        legitimate_abuse_message = await self.mod_channel.send(
            "Is this legitimate abuse? \n"
            "👍: Yes\n\n" +
            "👎: No\n"
        )
        self.next_message_id = legitimate_abuse_message.id

        # Add reactions
        await legitimate_abuse_message.add_reaction("👍")
        await legitimate_abuse_message.add_reaction("👎")

    async def is_abuse(self, reaction):
        '''
        This function is called in state AWAITING_ABUSE_IDENTIFICATION.
        It returns a tuple where the first element is a bool representing whether abuse was found
        and the second element is the string response.
        '''
        if reaction.emoji.name == "👍":
            return (True, "Thank you. We've logged this as legitmate abuse.")
        elif reaction.emoji.name == "👎":
            return (False, "Thank you. This report will be discarded.")
        else:
            # NOTE: Not Correct fix later
            return (None, "Invalid reaction. Please try again.")
        
    async def reply_message_id(self):
        '''
        Called in State: ABUSE_IDENTIFIED.
        This function asks the user to categorize the message. 
        '''
        reaction_message = await self.mod_channel.send(    
            f'The reporter categorized this as \"{self.category_to_string_manual(self.report_data["category"])}\"\n'
            "What type of abuse is this message?\n" +
            "1️⃣: Sexual Threat\n" +
            "2️⃣: Offensive Content\n" +
            "3️⃣: Spam/Scam\n" +
            "4️⃣: Imminent Danger\n"
            )
        
        self.next_message_id = reaction_message.id

        # Add reactions
        await reaction_message.add_reaction("1️⃣")
        await reaction_message.add_reaction("2️⃣")
        await reaction_message.add_reaction("3️⃣")
        await reaction_message.add_reaction("4️⃣")

    async def store_category(self, reaction):
        '''
        This function is called in state ABUSE_IDENTIFIED.
        It stores the user's categorization and sets the category.
        '''
        if reaction.emoji.name == "1️⃣":
            self.review_data["category"] = Category.SEXUAL_THREAT
        elif reaction.emoji.name == "2️⃣":
            self.review_data["category"] = Category.OFFENSIVE_CONTENT
        elif reaction.emoji.name == "3️⃣":
            self.review_data["category"] = Category.SPAM_SCAM
        elif reaction.emoji.name == "4️⃣":
            self.review_data["category"] = Category.DANGER
        else:
            return "Invalid reaction. Please try again."
        
        return f"Thank you. We've logged the category as \"{self.category_to_string()}.\""
    
    async def reply_sexual_threat_type(self):
        '''
        Called in category SEXUAL_THREAT and state L1.
        This function asks the moderator to identify the specific type of sexual threat (1 of 6). 
        '''
        sexual_threat_type = await self.mod_channel.send(
            "What is the specific type of sexual threat involved?\n"
            "1️⃣: Fake Explicit Image\n" +
            "2️⃣: Financial Extortion\n" +
            "3️⃣: Reputation Damage\n" + 
            "4️⃣: Physical Threats\n" + 
            "5️⃣: Compromising Material\n" + 
            "6️⃣: Other\n" 
        )

        self.next_message_id = sexual_threat_type.id

        # Add reactions 
        await sexual_threat_type.add_reaction("1️⃣")
        await sexual_threat_type.add_reaction("2️⃣")
        await sexual_threat_type.add_reaction("3️⃣")
        await sexual_threat_type.add_reaction("4️⃣")
        await sexual_threat_type.add_reaction("5️⃣")
        await sexual_threat_type.add_reaction("6️⃣")

    async def store_sexual_threat_type(self, reaction):
        '''
        This function is called in category SEXUAL_THREAT and state L2. 
        It stores the moderator's response to what kind of sexual threat the abuse is.
        '''
        if reaction.emoji.name == "1️⃣":
            self.review_data["sexual_threat_type"] = "Fake Explicit Image"
        elif reaction.emoji.name == "2️⃣":
            self.review_data["sexual_threat_type"] = "Financial Extortiont"
        elif reaction.emoji.name == "3️⃣":
            self.review_data["sexual_threat_type"] = "Reputational Damage"
        elif reaction.emoji.name == "4️⃣":
            self.review_data["sexual_threat_type"] = "Physical Threats"
        elif reaction.emoji.name == "5️⃣":
            self.review_data["sexual_threat_type"] = "Compromising Material"
        elif reaction.emoji.name == "6️⃣":
            self.review_data["sexual_threat_type"] = "Other"
        else:
            return "Invalid reaction. Please try again."
        
        return f"Thank you. We've logged the specific sexual threat type as \"{self.review_data['sexual_threat_type']}\"."


    async def determine_action(self):
        '''
        This function is called in state REVIEW_COMPLETE.
        It returns the right message for the end of the manual flow.
        '''
        if "severity" not in self.review_data or self.review_data["severity"] == 1: # Report is not real
            return "Manual review complete. No abuse found. No action taken."
        elif self.review_data["severity"] == 2:
            return f'Severity level 2 determined. User {self.report_data["name"]} has been kicked.'
        elif self.review_data["severity"] == 3:
            return f'Severity level 3 determined. Report has been rescalted to law enforcement. User {self.report_data["name"]} has been kicked.'
    
    async def reply_severity(self):
        '''
        This function is called in the L1 state of most abuse types to ask for severity type.
        It asks for the level of severity of the message.
        '''
        threat_message = await self.mod_channel.send(
            "What level of severity is the message?\n"
            "1️⃣: Severity 1 - Not abuse\n" +
            "2️⃣: Severity 2 - Bannable Offense\n" +
            "3️⃣: Severity 3 - Egregious Offense\n"
        )

        await threat_message.add_reaction("1️⃣")
        await threat_message.add_reaction("2️⃣")
        await threat_message.add_reaction("3️⃣")    

        self.next_message_id = threat_message.id

    # changed function name from severity_l2 to be more general 
    async def store_severity(self, reaction):
        '''
        This function is called in the L2 state of most abuse types to ask for severity type
        Exception: for sexual abuse, it is called during L3. 
        It records the response for the severity rating.
        '''
        if reaction.emoji.name == "1️⃣":
            self.review_data["severity"] = 1
        elif reaction.emoji.name == "2️⃣":
            self.review_data["severity"] = 2
        elif reaction.emoji.name == "3️⃣":
            self.review_data["severity"] = 3
        else:
            return "Invalid reaction. Please try again."
        
        return f"Thank you. We've logged the severity as \"Severity {self.review_data['severity']}\"."

    ### Helper Functions ###

    def category_to_string(self):
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
        
    def category_to_string_manual(self, category):
        '''
        A manual version of category_to_string that takes the category as input.
        '''
        if category == ReportCategory.SEXUAL_THREAT:
            return "Sexual Threat"
        elif category == ReportCategory.OFFENSIVE_CONTENT:
            return "Offensive Content"
        elif category == ReportCategory.SPAM_SCAM:
            return "Spam/Scam"
        elif category == ReportCategory.DANGER:
            return "Danger"
        else:
            return "Unknown"
