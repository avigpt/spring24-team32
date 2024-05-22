import vertexai
from vertexai.generative_models import GenerativeModel

async def detect_sextortion(message):
    # Step 1: Use LLM to detect if message is sextortion.

    project_id = "cs-152-discord-bot"

    vertexai.init(project=project_id, location="us-west1")

    model = GenerativeModel(model_name="gemini-1.0-pro-002")
    print(message.content)
    response = model.generate_content(
        "Tell me what is 1 + 1?",
    )

    print(response)
    
    # Step 2: Potentially can extend this to check if someone has sent a nude image; could delete the message if so.


