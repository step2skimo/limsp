import re
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from lims.models import (
    Sample, Expense, Reagent, ReagentIssue, Client,
    TestResult, TestAssignment
)
from lims.models.coa import COAInterpretation
from lims.models.parameter import Parameter  # Ensure this is imported

def contains_all(terms, text):
    return all(any(t in word for word in text.split()) for t in terms)

def contains_any(terms, text):
    return any(t in text for t in terms)

def detect_and_handle_query(prompt, user):
    prompt_lower = prompt.lower()
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    is_manager = user.groups.filter(name="Manager").exists()

    # ==== Sample Queries ====
    if contains_all(["sample", "week"], prompt_lower) and contains_any(["how many", "received", "processed", "count"], prompt_lower):
        count = Sample.objects.filter(received_date__gte=start_of_week).count()
        return f"We’ve received {count} samples this week."

    if contains_all(["sample", "month"], prompt_lower) and contains_any(["how many", "received", "processed", "count"], prompt_lower):
        count = Sample.objects.filter(received_date__gte=start_of_month).count()
        return f"We’ve received {count} samples this month."

    # ==== Financials: Revenue ====
    if contains_any(["revenue", "income", "earned", "made"], prompt_lower):
        if not is_manager:
            return "Sorry, only managers can access financial data like revenue or income."

        period = None
        if "today" in prompt_lower:
            period = ("today", today)
        elif "week" in prompt_lower:
            period = ("week", start_of_week)
        elif "month" in prompt_lower:
            period = ("month", start_of_month)

        if period:
            assignments = TestAssignment.objects.filter(assigned_date__gte=period[1]).select_related("parameter")
            total = sum(a.parameter.default_price for a in assignments if a.parameter)
            return f"Estimated revenue for this {period[0]} is ₦{total:,.2f}."

    # ==== Financials: Expenses & Breakdown ====
    if "expenses" in prompt_lower or "spending" in prompt_lower:
        if not is_manager:
            return "Sorry, only managers can access expense information."

        if "breakdown" in prompt_lower or "category" in prompt_lower:
            breakdown = Expense.objects.filter(date__gte=start_of_month).values("category").annotate(total=Sum("amount"))
            if not breakdown:
                return "No expenses recorded this month."
            response = "Expense breakdown by category for this month:\n"
            for item in breakdown:
                response += f"• {item['category'] or 'Uncategorized'}: ₦{item['total']:,.2f}\n"
            return response.strip()

        total = Expense.objects.filter(date__gte=start_of_month).aggregate(Sum("amount"))["amount__sum"] or 0
        return f"Lab expenses this month are ₦{total:,.2f}."

    # ==== Average Revenue Per Sample / Test ====
    if "average" in prompt_lower and contains_any(["revenue", "income", "earned"], prompt_lower):
        if not is_manager:
            return "Sorry, only managers can access financial metrics like averages."

        assignments = TestAssignment.objects.filter(assigned_date__gte=start_of_month).select_related("parameter")
        total_revenue = sum(a.parameter.default_price for a in assignments if a.parameter)
        total_tests = assignments.count()
        total_samples = Sample.objects.filter(received_date__gte=start_of_month).count()

        if "sample" in prompt_lower and total_samples:
            avg = total_revenue / total_samples
            return f"Average revenue per sample this month is ₦{avg:,.2f}."
        elif "test" in prompt_lower and total_tests:
            avg = total_revenue / total_tests
            return f"Average revenue per test this month is ₦{avg:,.2f}."
        else:
            return "Not enough data to calculate average revenue."

    # ==== Reagents ====
    if contains_any(["low stock", "below threshold", "running low"], prompt_lower) and "reagent" in prompt_lower:
        low_stock = Reagent.objects.filter(number_of_containers__lte=F("low_stock_threshold")).count()
        return f"There are {low_stock} reagents below stock threshold."

    if contains_any(["expired", "past expiry", "bad"], prompt_lower) and "reagent" in prompt_lower:
        expired = Reagent.objects.filter(expiry_date__lte=today).count()
        return f"There are {expired} expired reagents in inventory."

    if contains_any(["issue", "problem", "fault"], prompt_lower) and "reagent" in prompt_lower:
        count = ReagentIssue.objects.filter(date_reported__gte=start_of_month).count()
        return f"There have been {count} reagent issues reported this month."

    # ==== Test Results ====
    if contains_all(["test", "week"], prompt_lower) and contains_any(["recorded", "done", "completed"], prompt_lower):
        count = TestResult.objects.filter(recorded_at__date__gte=start_of_week).count()
        return f"{count} test results have been recorded this week."

    if contains_any(["pending", "unassigned", "not started"], prompt_lower) and "test" in prompt_lower:
        pending = TestAssignment.objects.filter(status='pending').count()
        return f"There are {pending} pending test assignments."

    # ==== Clients / COAs ====
    if "client" in prompt_lower and "month" in prompt_lower and contains_any(["new", "added", "registered"], prompt_lower):
        count = Client.objects.filter(created__date__gte=start_of_month).count()
        return f"{count} new clients were added this month."

    if contains_any(["coa", "interpretation"], prompt_lower) and "month" in prompt_lower:
        count = COAInterpretation.objects.filter(created_at__date__gte=start_of_month).count()
        return f"{count} COA interpretations were written this month."

    return None
