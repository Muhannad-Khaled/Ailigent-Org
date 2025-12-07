"""Test Gemini API connection and list available models."""

import os
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key: {api_key[:20]}..." if api_key else "NO API KEY FOUND")

genai.configure(api_key=api_key)

print("\n=== Available Models ===")
for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(f"  - {model.name}")

print("\n=== Testing gemini-1.5-flash ===")
try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Say 'Hello, I am working!'")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Testing gemini-pro ===")
try:
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content("Say 'Hello, I am working!'")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
