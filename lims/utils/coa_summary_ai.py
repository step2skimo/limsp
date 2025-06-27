import google.generativeai as genai

def generate_dynamic_summary(samples):
    import google.generativeai as genai

    prompt = (
        "You are a food science expert. "
        "In no more than 30 words, give a concise overall assessment of the following grain/nutritional results. "
        "Do not list parameters or sample IDs. Give one general verdict.\n\n"
    )

    for sample in samples:
        prompt += f"{sample.sample_type} sample results:\n"
        for param, val in sample.results.items():
            prompt += f"{param}: {val}\n"
        prompt += "\n"

    model = genai.GenerativeModel("gemini-2.5-flash")
    chat = model.start_chat()
    response = chat.send_message(prompt)

    return response.text.strip()
