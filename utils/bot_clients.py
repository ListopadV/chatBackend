from openai import OpenAI
import google.generativeai as genai
import requests
from ..config import Config

client = OpenAI(api_key=Config.OPENAI_API_KEY)


def ask_gpt(text, temperature, top_p, max_tokens):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": text}
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )
        response = completion.choices[0].message.content
        return response, 200
    except Exception as e:
        return str(e), 500


def ask_bard(text, temperature, top_p, max_tokens):
    try:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            text,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=max_tokens
            )
        )
        return response.text, 200
    except requests.exceptions.HTTPError as http_err:
        try:
            error_data = http_err.response.json()
            error_message = error_data['error']['message']
            status_code = error_data['error']['code']
            return error_message, status_code
        except Exception:
            return str(http_err), 500
    except Exception as e:
        return str(e), 500
