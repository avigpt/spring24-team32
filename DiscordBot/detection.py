import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold

async def detect_sextortion(message):
    # Step 1: Use LLM to detect if message is sextortion.
    project_id = "cs-152-discord-bot"
    vertexai.init(project=project_id, location="us-west1")
    model = GenerativeModel(model_name="gemini-1.0-pro-002")
    
    print(message.content)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    prompt = "Please tell me if you detect any sextortion in this message, and respond in one word (yes or no): " + message.content
    
    response = model.generate_content(
        prompt,
        safety_settings = safety_settings
    )

    if response.candidates[0].content.parts[0].text == "Yes":
        return True
    return False

