import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
import requests

async def detect_sextortion_gemini(message, prompt):
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

    if response.candidates[0].content.parts[0].text.lower().startswith("yes"):
        return True
    return False

async def detect_sextortion_openai(message, prompt, key):
    """ 
    Template for making GPT request.
    """
    openai_api_key = key
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": message.content}],
        "temperature": 1,
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data).json()
    if response['choices'][0]['message']['content'] == 'yes':
         return True
    return False

async def detect_sextortion(message, model, key=None):
    """
    Called by the bot to detect sextortion in a message.
    """
    prompt = "Please tell me if you detect any sextortion in the message below. \
              Sextortion occurs when the message contains both a request for explicit material and a threat if the receiver does not comply. \
              For example, asking for nude images alone is not sufficient for sextortion; the message must also include a threat, such as releasing \
              potentially incriminating or sensitive content, or physical harm. Respond in the following format: \
              Please only say 'yes' or 'no' to indiciate if you detect sextortion."
    
    if model == "gemini":
        return await detect_sextortion_gemini(message, prompt)
    elif model == "gpt":
        return await detect_sextortion_openai(message, prompt, key)
    return False

async def detect(message, prompt):
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

    if response.candidates[0].content.parts[0].text.lower().startswith("yes"):
        return True
    return False

async def detect_spamscam(message):
    prompt = "Please tell me if you detect any spam or scam in the message below. \
              Please only say 'yes' or 'no' to indiciate if you detect spam or scam."
    
    detected = await detect(message, prompt)
    return detected

async def detect_offensive_content(message):
    prompt = "Please tell me if you detect any offensive content in the message below. \
              Please only say 'yes' or 'no' to indiciate if you detect offensive content."
    
    detected = await detect(message, prompt)
    return detected
    
async def detect_danger(message):
    prompt = "Please tell me if you detect any dangerous content in the message below. \
              Please only say 'yes' or 'no' to indiciate if you detect dangerous content."
    
    detected = await detect(message, prompt)
    return detected

