import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def generate_efficiency_nudge(analyst_name, my_avg_sec, percentile_rank, test_count):
    prompt = (
        f"Create a short, positive message addressed to {analyst_name} who completed {test_count} lab tests this week. "
        f"Their average test duration was {int(my_avg_sec)} seconds, placing them in the top {percentile_rank} percentile. "
        "Encourage them with enthusiasm but keep it professional and human. Limit to 2–3 sentences."
    )

    model = genai.GenerativeModel("gemini-2.5-flash")  

    response = model.generate_content(prompt)

    try:
        return response.text.strip()
    except AttributeError:
        return response.candidates[0].content.parts[0].text.strip()
