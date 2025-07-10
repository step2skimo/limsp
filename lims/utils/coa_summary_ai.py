import google.generativeai as genai

def generate_dynamic_summary(summary_data_by_type):
    base_context = (
        "You are a senior food laboratory reporting officer. "
        "Write a single, concise interpretation (max 100 words) based on the sample results below. "
        "Samples belong to different categories (e.g., feed, flour, dairy), and your explanation should intelligently reflect this. "
        "Consider expected standards and acceptable ranges (e.g., from FAO, USDA, Codex) for each sample type when interpreting the data. "
        "Avoid listing raw values or referring to sample codes. "
        "Instead, highlight nutritional quality, abnormal values, and what they imply for use, safety, or consistency."
    )

    prompt = base_context + "\n\nHere are the summarized test results by sample type:\n"

    for sample_type, param_data in summary_data_by_type.items():
        prompt += f"\nSample Type: {sample_type.title()}\n"
        for param, values in param_data.items():
            prompt += f"{param}: {', '.join(str(v) for v in values)}\n"

    model = genai.GenerativeModel("gemini-2.5-flash")
    chat = model.start_chat()
    response = chat.send_message(prompt)

    return response.text.strip()

