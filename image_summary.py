
from google import genai
from google.genai import types
import time
import random
import os

def extract_text_from_image(image_path, api_key, model_gemini):
    client = genai.Client(api_key=api_key)
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    prompt = """Extract all visible text from this image. Present the text clearly, preserving line breaks and structure where possible. Do not include any descriptions or summaries, only the extracted text.
Also If this image contains any diagrams, graphs, charts, or tables, then at the end of your response, for each such element, provide its name prefixed with a '#hashtag'. Below this tag, provide a proper step-by-step summary of that specific element."""
    
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
        prompt
    ]
    
    config = types.GenerateContentConfig(
        temperature=0.0
    )
    
    max_retries = 5             # fewer retries for faster failure
    max_total_wait = 120        # max 2 minutes total wait
    attempt = 0
    total_wait = 0
    
    while attempt < max_retries and total_wait < max_total_wait:
        try:
            response = client.models.generate_content(
                model=model_gemini,
                contents=contents,
                config=config
            )
            return response.text
        except Exception as e:
            err_str = str(e).lower()
            if '503' in err_str or 'overloaded' in err_str:
                wait_time = min(2 ** attempt + random.random(), 15)  # max wait per retry 15 seconds for faster retries with jitter
                print(f"Attempt {attempt + 1} failed due to model overload (503). Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                total_wait += wait_time
                attempt += 1
            else:
                print(f"Non-retryable error encountered: {e}")
                break
    
    print("Exceeded max retries or sustained overload. Returning empty response.")
    return ""

