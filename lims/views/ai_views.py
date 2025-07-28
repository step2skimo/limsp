from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from lims.utils.query_dispatcher import detect_and_handle_query
from lims.models.ai import LabAIHistory 
from lims.lab_ai_utils import get_lab_ai_prompt
import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@csrf_exempt
def ask_lab_ai(request):
    if request.method != "POST":
        return JsonResponse({"reply": "Invalid request method."})

    prompt = request.POST.get("prompt", "").strip()
    if not prompt:
        return JsonResponse({"reply": "Please type a question."})

    try:
        # 🔐 Determine role
        user = request.user
        role = "analyst"
        if user.groups.filter(name="Manager").exists():
            role = "manager"
        elif user.groups.filter(name="Clerk").exists():
            role = "clerk"

        # 🔍 Check if it's a DB query
        db_reply = detect_and_handle_query(prompt, user)

        # Build final prompt for Gemini
        final_prompt = f"{db_reply}\n\nUser asked: {prompt}" if db_reply else prompt

        # 💬 Gemini
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=get_lab_ai_prompt(role)
        )
        chat = model.start_chat(history=[])
        response = chat.send_message(final_prompt)
        reply = response.text.strip()

        # 💾 Log interaction
        LabAIHistory.objects.create(user=user, question=prompt, answer=reply)

        return JsonResponse({"reply": reply})

    except Exception as e:
        return JsonResponse({"reply": f"An error occurred: {str(e)}"})
