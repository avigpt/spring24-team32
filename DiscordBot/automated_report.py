import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
from report import Category

class AutomatedReport:

    def __init__(self, message, author, category):
        self.message = message
        self.author = author
        self.report_data = {'name': author, 'content': message, 'category': category}

    async def generate_report(self):
        '''
        Automatically populates self.report_data using Gemini
        '''

        ## Category: Sexual Threat ##
        if self.report_data["category"] == Category.SEXUAL_THREAT:
            await self.sexual_threat_l1() 
            await self.sexual_threat_l2()
            await self.sexual_threat_l3()

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
        This function asks the model to provide more detail; specifically, for sender demand. 
        '''

        prompt = "What is the sender demanding or asking for? \n" \
            "1️⃣: Nude Content\n" + \
            "2️⃣: Financial Payment\n" + \
            "3️⃣: Sexual Service\n" + \
            "4️⃣: Other\n"

        response = await self.query_gemini(self.message, prompt)

        if "1️⃣" in response:
            self.report_data["demand"] = "Nude Content"
        elif "2️⃣" in response:
            self.report_data["demand"] = "Financial Payment"
        elif "3️⃣" in response:
            self.report_data["demand"] = "Sexual Service"
        elif "4️⃣" in response:
            self.report_data["demand"] = "Other"
    
    async def sexual_threat_l2(self):
        '''
        Called in category SEXUAL_THREAT and state L2.
        This function asks the model to provide more detail; specifically, for sender threat. 
        '''
        prompt = "What is the sender threatening to do? Please return the emoji.\n" \
            "1️⃣: Physical Harm\n" + \
            "2️⃣: Public Exposure\n" + \
            "3️⃣: Unclear\n"

        response = await self.query_gemini(self.message, prompt)

        if "1️⃣" in response:
            self.report_data["threat"] = "Physical Harm"
        elif "2️⃣" in response:
            self.report_data["threat"] = "Public Exposure"
        elif "3️⃣" in response:
            self.report_data["threat"] = "Unclear"


    # Do we add context using gen AI

    async def sexual_threat_l3(self):
        '''
        Makes the model provide additional context
        '''
        prompt = "Please additional context for the report in 10 words or less"
        
        response = await self.query_gemini(self.message, prompt)

        self.report_data["context"] = "Yes"
        self.report_data["context_content"] = response

    ## Danger Flow ##
    async def danger_l1(self):
        '''
        Called in category DANGER and state L1.
        This function asks the model to provide more detail; specifically, for the nature of the danger. 
        '''
        prompt = "Please select the nature of the danger.\n" + \
            "1️⃣: Safety Threat\n" + \
            "2️⃣: Criminal Behavior\n"

        response = await self.query_gemini(self.message, prompt)
        if "1️⃣" in response:
            self.report_data["danger_type"] = "Safety Threat"
        elif "2️⃣" in response:
            self.report_data["danger_type"] = "Criminal Behavior"

    async def danger_l2_threat(self):
        '''
        This function is called in category DANGER and state L2 if the model clicked Safety Threat.
        '''
        prompt = "Please select the type of safety threat.\n" + \
            "1️⃣: Suicide/Self-Harm\n" + \
            "2️⃣: Violence\n"

        response = await self.query_gemini(self.message, prompt)

        if "1️⃣" in response:
            self.report_data["safety_threat_type"] = "Suicide/Self-Harm"
        elif "2️⃣" in response:
            self.report_data["safety_threat_type"] = "Violence"
            
    async def danger_l2_criminal(self):
        '''
        This function is called in category DANGER and state L2 if the model clicked Criminal Behavior.
        '''
        prompt = "Please select the type of criminal behavior.\n" + \
            "1️⃣: Theft/Robbery\n" + \
            "2️⃣: Child Abuse\n" + \
            "3️⃣: Human Exploitation"
    
        response = await self.query_gemini(self.message, prompt)

        if "1️⃣" in response:
            self.report_data["criminal_behavior_type"] = "Theft/Robbery"
        elif "2️⃣" in response:
            self.report_data["criminal_behavior_type"] = "Child Abuse"
        elif "3️⃣" in response:
            self.report_data["criminal_behavior_type"] = "Human Exploitation"
        
    ## Offensive Content ## 
    async def offensive_content_l1(self): 
        prompt = "Please select the type of offensive content.\n" \
            "1️⃣: Violent Content\n" + \
            "2️⃣: Hateful Content\n" + \
            "3️⃣: Pornography\n"       

        response = await self.query_gemini(self.message, prompt)

        if "1️⃣" in response:
            self.report_data["offensive_content_type"] = "Violent Content"
        elif "2️⃣" in response:
            self.report_data["offensive_content_type"] = "Hateful Content"
        elif "3️⃣" in response:
            self.report_data["offensive_content_type"] = "Pornography" 
        
    ## Spam/Scam ##
    async def spam_scam_content_l1(self): 
        prompt = "Please select the type of spam/scam.\n" \
            "1️⃣: Spam\n" + \
            "2️⃣: Fraud\n" + \
            "3️⃣: Impersonation or Fake Account\n"
        
        response = await self.query_gemini(self.message, prompt)

        if "1️⃣" in response:
            self.report_data["spam_scam_content_type"] = "Spam"
        elif "2️⃣" in response:
            self.report_data["spam_scam_content_type"] = "Fraud"
        elif "3️⃣" in response:
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
        Queries gemini for content moderation.
        """
        
        context = "I want to help categorize certain example messages on a social media platform as different kind of policy abuse types." + \
        "You answers will help in populating report data to help simulate content moderation."
        f"Here is the current state of the report: {self.report_data}" + \
        "I am going to ask a question about a message. Please respond."
        

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
            context + prompt + "\n Here's the message: " + message,
            safety_settings = safety_settings,
            generation_config = {
                'temperature': 0.0
            }
        )

        return response.candidates[0].content.parts[0].text