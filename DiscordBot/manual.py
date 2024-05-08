from enum import Enum, auto
import discord
import re

'''
Known issues that need to be addressed but should be ignored until flow is done:

1. Report reviews can only happen one at a time. If a second report is attempted to be reviewed it should not happen.
There is some logic on destroying ManualReview instances but it is not complete.
2. Reactions should only be valid if they were on the right message. This is currently a problem in both flows. 
One idea could be to keep track of a pointer to the message_id of the next message sent out and then return it to the client in
bot.py to use in on_raw_reaction_add().
3. Reports that are canceled should be ignored. Cannot be done until user flow is finished.
4. Format incoming reports in group-32-mod channel. Show priority.
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
        self.next_message_id = None # TODO: For ensuring only the reactions on the next message work


    async def perform_manual_review(self, reaction):
        '''
        Core logic of the manual review. First the report is determined to be abuse or not. Then it is classified.
        TODO: Once classification is complete, self.level is used to fine-grain states.
        '''
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
        
        if self.state == State.REVIEW_COMPLETE:
            await self.mod_channel.send(await self.determine_action())
            return True
        
        # Runs once self.state is State.CATEGORY_INDENFIFIED
        if self.state == State.CATEGORY_IDENTIFIED:
            if self.review_data["category"] == Category.SEXUAL_THREAT:
                # TODO: Follow flow
                # DELETE WHEN ABOVE IS IMPLEMENTED
                await self.mod_channel.send(f"To implement: Sexual Threat")
            elif self.review_data["category"] == Category.OFFENSIVE_CONTENT:
                # TODO: Follow flow
                # DELETE WHEN ABOVE IS IMPLEMENTED
                await self.mod_channel.send(f"To implement: Offensive Content")
            elif self.review_data["category"] == Category.SPAM_SCAM:
                # TODO: Follow flow
                # DELETE WHEN ABOVE IS IMPLEMENTED
                await self.mod_channel.send(f"To implement: Spam/Scam")
            elif self.review_data["category"] == Category.DANGER:
                # TODO: Follow flow
                # DELETE WHEN ABOVE IS IMPLEMENTED
                await self.mod_channel.send(f"To implement: Danger")


        return False

    async def reply_legitimate_abuse(self):
        '''
        This function is called in state AWAITING_ABUSE_IDENTIFICATION.
        It asks the question of whether the message is legitimate abuse AKA is the report real.
        '''
        legitimate_abuse_message = await self.mod_channel.send(
            "Question #?: Is this legitimate abuse? \n"
            "👍: Yes\n\n" +
            "👎: No\n"
        )

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
            "What type of abuse is this message?\n" +
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
    
    async def determine_action(self):
        '''
        This function is called in state REVIEW_COMPLETE.
        It returns the right message for the end of the manual flow.
        '''
        if self.review_data == {}: # Report is not real
            return "Manual review complete. No abuse found. No action taken."
    
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