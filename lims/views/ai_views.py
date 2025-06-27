import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os
from lims.models.ai import LabAIHistory 
from lims.lab_ai_utils import get_lab_ai_prompt

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY")) 


@csrf_exempt
def ask_lab_ai(request):
    if request.method == "POST":
        prompt = request.POST.get("prompt", "").strip()
        if not prompt:
            return JsonResponse({"reply": "Please type a question."})

        try:
            # 🔐 Determine user role
            user_role = "analyst"  # default role
            if request.user.groups.filter(name="Manager").exists():
                user_role = "manager"
            elif request.user.groups.filter(name="Clerk").exists():
                user_role = "clerk"

            # 🧠 Load system prompt
            system_prompt = get_lab_ai_prompt(user_role)

            # ✅ Gemini: Use system_instruction (NOT history role="system")
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",  # or "gemini-2.5-flash" if enabled for your API key
                system_instruction=system_prompt
            )

            chat = model.start_chat(history=[])
            response = chat.send_message(prompt)
            reply = response.text.strip()

            # 💾 Save to database
            LabAIHistory.objects.create(
                user=request.user,
                question=prompt,
                answer=reply
            )

            return JsonResponse({"reply": reply})

        except Exception as e:
            return JsonResponse({"reply": f"Sorry, I hit an error: {str(e)}"})

    return JsonResponse({"reply": "Invalid request method."})
