import google.generativeai as genai

def generate_dynamic_summary(summary_data):
    

    prompt = (
    "You are an experienced food laboratory reporting officer. "
    "Provide a concise, professional interpretation of the nutritional analysis results below, in 100 words or less. "
    "Highlight key differences between samples, note any elevated or low parameters, "
    "and discuss what these results might indicate about the nutritional quality. "
    "Avoid repeating parameter lists, but summarize their meaning clearly. "
    "If results suggest potential quality issues, mention it. "
    "Do not reference sample codes directly. "
    "Here are the data:\n\n"
)


    for param, values in summary_data.items():
        prompt += f"{param}: {', '.join(str(v) for v in values)}\n"

    model = genai.GenerativeModel("gemini-2.5-flash")
    chat = model.start_chat()
    response = chat.send_message(prompt)

    return response.text.strip()
