import os
from django.conf import settings

def get_lab_ai_prompt(role="analyst"):
    prompt_path = os.path.join(settings.BASE_DIR, "ai_prompts/lab_ai_prompt.txt")

    with open(prompt_path, "r", encoding="utf-8") as f:
        base_prompt = f.read()

    role = role.lower()

    if role == "manager":
        base_prompt += (
            "\n\nThe current user is a Lab Manager. Provide strategic insights such as productivity tracking, QC analytics, task delegation, compliance monitoring, and audit readiness tips."
        )
    elif role == "clerk":
        base_prompt += (
            "\n\nThe current user is a Lab Clerk. Focus on helping with data entry, sample tracking, client communications, report generation, and lab recordkeeping practices."
        )
    else:  # analyst or fallback
        base_prompt += (
            "\n\nThe current user is an Analyst. Focus on test execution, lab methods, SOPs, turnaround times, QC validation, and result documentation guidance."
        )

    return base_prompt
