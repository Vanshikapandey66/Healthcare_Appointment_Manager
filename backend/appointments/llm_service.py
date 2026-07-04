from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def pre_visit_summary(symptoms):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical assistant. Summarize symptoms before doctor visit."
                },
                {
                    "role": "user",
                    "content": symptoms
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating summary: {str(e)}"


def post_visit_summary(notes):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical assistant. Summarize doctor notes into patient friendly instructions."
                },
                {
                    "role": "user",
                    "content": notes
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating summary: {str(e)}"