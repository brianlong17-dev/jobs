import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()
#os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("--- Available Models ---")
models = client.models
for model in models.list():
    # 'generateContent' is the capability you need for Instructor
    if "generateContent" in model.supported_actions:
        print(f"Name: {model.name}")