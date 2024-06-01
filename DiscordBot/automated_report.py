import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
from enum import Enum, auto

class Category(Enum):
    SEXUAL_THREAT = auto()
    OFFENSIVE_CONTENT = auto()
    SPAM_SCAM = auto()
    DANGER = auto()

class Report:

    def __init__(self, message):
        self.message = None
        self.report_data = {}
    
    async def categorize_abuse_type(self):
        '''
        Called in State: MESSAGE_IDENTIFIED.
        This function asks the user to categorize the message. 
        '''
        prompt = "We found this author and message:" + "```" + self.author_name + ": " + self.message + "```" + \
            "\nWhy are you reporting this message?\n" + \
            "1️⃣: Sexual Threat\n" + \
            "2️⃣: Offensive Content\n" +\
            "3️⃣: Spam/Scam\n" + \
            "4️⃣: Imminent Danger\n"

        response = await self.query_gemini(self.message, prompt)

        if response == "1️⃣":
            self.report_data["category"] = Category.SEXUAL_THREAT
        elif response == "2️⃣":
            self.report_data["category"] = Category.OFFENSIVE_CONTENT
        elif response == "3️⃣":
            self.report_data["category"] = Category.SPAM_SCAM
        elif response == "4️⃣":
            self.report_data["category"] = Category.DANGER

    async def generate_report(self, reaction):
        '''
        This function is called whenever a reaction is added to a message.
        It is first called in state MESSAGE_IDENTIFIED. 
        '''
        await self.categorize_abuse_type()

        ## Category: Sexual Threat ##
        if self.report_data["category"] == Category.SEXUAL_THREAT:
            await self.sexual_threat_l1() 
            await self.sexual_threat_l2()
            await self.sexual_threat_l3()
            # We could have genAI generate context for mod to consider
            # await self.collect_context()

        ## Category: Offensive Content ##
        elif self.report_data["category"] == Category.OFFENSIVE_CONTENT:
            await self.offensive_content_l1() 

        ## Category: Spam/Scam ##
        elif self.report_data["category"] == Category.SPAM_SCAM:
            await self.spam_scam_content_l1() 

        ## Category: Danger ##
        elif self.report_data["category"] == Category.DANGER:
            await self.danger_l1()
            if self.report_data["danger_type"] == "Safety Threat":
                await self.danger_l2_threat()        
            else: 
                await self.danger_l2_criminal()

    
    ## Sexual Threat Flow ##
    async def sexual_threat_l1(self):
        '''
        Called in category SEXUAL_THREAT and state L1.
        This function asks the user to provide more detail; specifically, for sender demand. 
        '''

        prompt = "What is the sender demanding or asking for? \n" \
            "1️⃣: Nude Content\n" + \
            "2️⃣: Financial Payment\n" + \
            "3️⃣: Sexual Service\n" + \
            "4️⃣: Other\n"

        response = await self.query_gemini(self.message, prompt)

        if response == "1️⃣":
            self.report_data["demand"] = "Nude Content"
        elif response == "2️⃣":
            self.report_data["demand"] = "Financial Payment"
        elif response == "3️⃣":
            self.report_data["demand"] = "Sexual Service"
        elif response == "4️⃣":
            self.report_data["demand"] = "Other"
    
    async def sexual_threat_l2(self, channel):
        '''
        Called in category SEXUAL_THREAT and state L2.
        This function asks the user to provide more detail; specifically, for sender threat. 
        '''
        prompt = "What is the sender threatening to do? \n" \
            "1️⃣: Physical Harm\n" + \
            "2️⃣: Public Exposure\n" + \
            "3️⃣: Unclear\n"

        response = await self.query_gemini(self.message, prompt)

        if response == "1️⃣":
            self.report_data["threat"] = "Physical Harm"
        elif response == "2️⃣":
            self.report_data["threat"] = "Public Exposure"
        elif response == "3️⃣":
            self.report_data["threat"] = "Unclear"


    # Do we add context using gen AI

    async def sexual_threat_l3(self, channel):
        '''
        Called in category SEXUAL_THREAT and state L3.
        Asks user if they want to give additional context. 
        '''
        prompt = "Please additional context for the report in 50 words or less"
        
        response = await self.query_gemini(self.message, prompt)

        self.report_data["context"] = "Yes"
        self.report_data["context_content"] = response

    ## Danger Flow ##
    async def danger_l1(self, channel):
        '''
        Called in category DANGER and state L1.
        This function asks the user to provide more detail; specifically, for the nature of the danger. 
        '''
        prompt = "If someone is in immediate danger, please get help before reporting. Don't wait.\n" + \
            "When you are ready to continue, please select the nature of the danger.\n" + \
            "1️⃣: Safety Threat\n" + \
            "2️⃣: Criminal Behavior\n"

        response = await self.query_gemini(self.message, prompt)

        if response == "1️⃣":
            self.report_data["danger_type"] = "Safety Threat"
        elif response == "2️⃣":
            self.report_data["danger_type"] = "Criminal Behavior"

    async def danger_l2_threat(self, channel):
        '''
        This function is called in category DANGER and state L2 if the user clicked Safety Threat.
        '''
        prompt = "Please select the type of safety threat.\n" + \
            "1️⃣: Suicide/Self-Harm\n" + \
            "2️⃣: Violence\n"

        response = await self.query_gemini(self.message, prompt)

        if response == "1️⃣":
            self.report_data["safety_threat_type"] = "Suicide/Self-Harm"
        elif response == "2️⃣":
            self.report_data["safety_threat_type"] = "Violence"
            
    async def danger_l2_criminal(self, channel):
        '''
        This function is called in category DANGER and state L2 if the user clicked Criminal Behavior.
        '''
        prompt = "Please select the type of criminal behavior.\n" + \
            "1️⃣: Theft/Robbery\n" + \
            "2️⃣: Child Abuse\n" + \
            "3️⃣: Human Exploitation"
    
        response = await self.query_gemini(self.message, prompt)

        if response == "1️⃣":
            self.report_data["criminal_behavior_type"] = "Theft/Robbery"
        elif response == "2️⃣":
            self.report_data["criminal_behavior_type"] = "Child Abuse"
        elif response == "3️⃣":
            self.report_data["criminal_behavior_type"] = "Human Exploitation"
        
    ## Offensive Content ## 
    async def offensive_content_l1(self): 
        prompt = "Please select the type of offensive content.\n" \
            "1️⃣: Violent Content\n" + \
            "2️⃣: Hateful Content\n" + \
            "3️⃣: Pornography\n"       

        response = await self.query_gemini(self.message, prompt)

        if response == "1️⃣":
            self.report_data["offensive_content_type"] = "Violent Content"
        elif response == "2️⃣":
            self.report_data["offensive_content_type"] = "Hateful Content"
        elif response == "3️⃣":
            self.report_data["offensive_content_type"] = "Pornography" 
        
    ## Spam/Scam ##
    async def spam_scam_content_l1(self): 
        prompt = "Please select the type of spam/scam.\n" \
            "1️⃣: Spam\n" + \
            "2️⃣: Fraud\n" + \
            "3️⃣: Impersonation or Fake Account\n"
        
        response = await self.query_gemini(self.message, prompt)

        if response == "1️⃣":
            self.report_data["spam_scam_content_type"] = "Spam"
        elif response == "2️⃣":
            self.report_data["spam_scam_content_type"] = "Fraud"
        elif response == "3️⃣":
            self.report_data["spam_scam_content_type"] = "Impersonation or Fake Account"
            
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

    async def query_gemini(self, message, prompt):
        """
        Detects sextortion using the Gemini model.
        """
        
        project_id = "cs-152-discord-bot"
        vertexai.init(project=project_id, location="us-west1")
        model = GenerativeModel(model_name="gemini-1.0-pro-002")
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        response = model.generate_content(
            prompt + "\n Here's the message: " + message.content,
            safety_settings = safety_settings
        )

        return response.candidates[0].content.parts[0].text