from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Q
from lims.models import Sample, TestAssignment, Equipment, CalibrationRecord, QCMetrics, TestResult
from django.template.loader import get_template
from django.http import HttpResponse
from weasyprint import HTML
import openpyxl
from django.http import HttpResponse
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.db.models import Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, F
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
import pprint 
from django.db.models import Count, Avg, ExpressionWrapper, F, DurationField, Q, FloatField
from django.utils.timezone import now
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Count, Avg, FloatField, DurationField, ExpressionWrapper
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from lims.models import TestAssignment, QCMetrics
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import JsonResponse
from weasyprint import HTML
import tempfile
from django.urls import reverse
from django.utils.http import urlencode
import os
from lims.forms import ExpenseForm
from django.db.models import Sum
from lims.models import Expense
from django.utils.timezone import now
from django.templatetags.static import static
from django.db.models import F, Sum, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from django.utils.http import urlencode
from weasyprint import HTML
import tempfile
import os

@login_required
def send_manager_report(request):
    if request.method == "POST":
        email = request.POST.get("email")
        # Preserve selected range for data consistency in email vs dashboard
        range_type = request.POST.get("range") or request.GET.get("range", "month")

        if email:
            # Inject range into request.GET-like context (optional)
            # If you want clean range handling, rebuild a GET QueryDict copy:
            mutable_get = request.GET.copy()
            mutable_get["range"] = range_type
            request.GET = mutable_get

            # ----- Get report data -----
            context = get_manager_report_context(request)

            # Human-friendly numbers for subject
            gross = context.get("gross_income") or context.get("total_income") or 0
            expenses = context.get("total_expenses") or 0
            net = context.get("net_income") or 0

            # Subject line w/ quick finance readout
            subject = (
                f"Manager Report ({context.get('range_label', range_type.title())}): "
                f"Gross ₦{gross:,.2f} | Expenses ₦{expenses:,.2f} | Net ₦{net:,.2f}"
            )

            # ----- Render HTML email body (with expenses table) -----
            # Use a dedicated, lightweight email template that includes all expenses
            html_content = render_to_string(
                "lims/manager/manager_report.html",
                context
            )
            text_content = strip_tags(html_content)

            # ----- Generate PDF attachment (full report layout) -----
            # Reuse your printable PDF template (showing income + expenses)
            pdf_html = render_to_string("lims/manager/report_pdf.html", context)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                HTML(string=pdf_html, base_url=request.build_absolute_uri()).write_pdf(tmp_pdf.name)
                pdf_path = tmp_pdf.name

            # ----- Build & send message -----
            from_email = "jaageelab@gmail.com"  # TODO: use settings.DEFAULT_FROM_EMAIL
            msg = EmailMultiAlternatives(subject, text_content, from_email, [email])
            msg.attach_alternative(html_content, "text/html")

            # Attach PDF
            filename = f"Manager_Report_{context.get('range_type','range')}_{context.get('end_date')}.pdf"
            with open(pdf_path, "rb") as f:
                msg.attach(filename, f.read(), "application/pdf")

            msg.send()

            # Clean up temp file
            os.remove(pdf_path)

            return JsonResponse({"message": "Report sent successfully!"})

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def analyst_productivity_view(request):
    today = timezone.now().date()
    range_type = request.GET.get("range", "month")

    # Determine date range
    if range_type == "day":
        start_date = end_date = today
    elif range_type == "week":
        start_date = today - timedelta(days=7)
        end_date = today
    elif range_type == "month":
        start_date = today.replace(day=1)
        end_date = today
    elif range_type == "last_month":
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1)
        end_date = last_day_last_month
    elif range_type == "all_time":
        start_date = None
        end_date = today
    else:
        start_date = end_date = today

    # Filter assignments within range
    if start_date:
        assignments = TestAssignment.objects.filter(
            status="completed",
            is_control=False,
            testresult__recorded_at__date__range=(start_date, end_date)
        )
        qc_range_filter = {"created_at__date__range": (start_date, end_date)}
    else:
        assignments = TestAssignment.objects.filter(
            status="completed",
            is_control=False,
            testresult__recorded_at__date__lte=end_date
        )
        qc_range_filter = {"created_at__date__lte": end_date}

    # Add time fields (TAT and Duration)
    assignments = assignments.annotate(
        tat=ExpressionWrapper(
            F("testresult__recorded_at") - F("sample__received_date"),
            output_field=DurationField()
        ),
        duration=ExpressionWrapper(
            F("testresult__recorded_at") - F("testresult__started_at"),
            output_field=DurationField()
        )
    )

    # Productivity metrics per analyst
    productivity = (
        assignments
        .values(analyst_name=F("analyst__username"))
        .annotate(
            tests=Count("id"),
            samples=Count("sample", distinct=True),
            params=Count("parameter", distinct=True),
            avg_tat=Avg("tat"),
            avg_duration=Avg("duration")
        )
        .order_by("-tests")
    )

    # QC pass rate
    qc_results = (
        QCMetrics.objects
        .filter(**qc_range_filter)
        .annotate(analyst_username=F("test_assignment__analyst__username"))
        .values("analyst_username")
        .annotate(
            total_qc=Count("id"),
            pass_qc=Count("id", filter=Q(status="pass"))
        )
    )

    qc_pass_rate_map = {
        row["analyst_username"]: round(100.0 * row["pass_qc"] / row["total_qc"], 1)
        if row["total_qc"] else 100.0
        for row in qc_results
    }

    # Helper to format durations
    def format_td(td):
        if not td:
            return "—"
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    # Add readable fields
    for person in productivity:
        person["avg_tat_human"] = format_td(person["avg_tat"])
        person["avg_duration_human"] = format_td(person["avg_duration"])
        person["qc_pass_rate"] = qc_pass_rate_map.get(person["analyst_name"], 100.0)

    # Totals
    total_tests = sum(p["tests"] for p in productivity)
    total_samples = sum(p["samples"] for p in productivity)

    if productivity:
        total_avg_tat_seconds = sum(
            p["avg_tat"].total_seconds() if p["avg_tat"] else 0
            for p in productivity
        ) / len(productivity)
        total_avg_tat = format_td(timedelta(seconds=total_avg_tat_seconds))
    else:
        total_avg_tat = "—"

    total_metrics = {
        "tests": total_tests,
        "samples": total_samples,
        "avg_tat_human": total_avg_tat
    }

    return render(request, "lims/analyst_productivity.html", {
        "productivity": productivity,
        "total_metrics": total_metrics,
        "start_date": start_date,
        "end_date": end_date,
        "range_type": range_type,
    })


@login_required
def get_manager_report_context(request):
    today = timezone.now().date()
    range_type = request.GET.get("range", "month")

    # ----- Date range selection -----
    if range_type == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        range_label = f"{start_date:%b %d} – {end_date:%b %d, %Y}"
    elif range_type == "day":
        start_date = end_date = today
        range_label = f"{today:%b %d, %Y}"
    elif range_type == "last_month":
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1)
        end_date = last_day_last_month
        range_label = f"{start_date:%B %Y}"
    elif range_type == "all_time":
        start_date = None
        end_date = today
        range_label = "All Time"
    else:  # current month
        start_date = today.replace(day=1)
        end_date = today
        range_label = f"{start_date:%B %Y}"

    # ----- Filters -----
    sample_filters = {"received_date__lte": end_date}
    test_filters = {"assigned_date__date__lte": end_date, "is_control": False}
    calibration_filters = {"calibration_date__lte": end_date}
    expense_filters = {"date__lte": end_date}

    if start_date:
        sample_filters["received_date__gte"] = start_date
        test_filters["assigned_date__date__gte"] = start_date
        calibration_filters["calibration_date__gte"] = start_date
        expense_filters["date__gte"] = start_date

    # ----- Querysets -----
    samples = Sample.objects.filter(**sample_filters).exclude(sample_type__iexact="QC")

    tests = (
        TestAssignment.objects
        .select_related("parameter", "sample", "analyst")
        .filter(**test_filters)
    )

    equipment = Equipment.objects.all()
    calibrations = CalibrationRecord.objects.filter(**calibration_filters)
    expenses_qs = Expense.objects.filter(**expense_filters)

    # ----- Aggregations -----
    analysis_summary = (
        tests.values(
            date_received=F("sample__received_date"),
            client_name=F("sample__client__name"),
            parameter_group=F("parameter__group__name"),
        )
        .annotate(
            sample_count=Count("sample", distinct=True),
            income=Sum("parameter__default_price"),
        )
        .order_by("-date_received")
    )

    daily_totals = (
        tests.annotate(day=TruncDay("assigned_date"))
        .values("day")
        .annotate(income=Sum("parameter__default_price"))
        .order_by("day")
    )

    weekly_totals = (
        tests.annotate(week=TruncWeek("assigned_date"))
        .values("week")
        .annotate(income=Sum("parameter__default_price"))
        .order_by("week")
    )

    monthly_totals = (
        tests.annotate(month=TruncMonth("assigned_date"))
        .values("month")
        .annotate(income=Sum("parameter__default_price"))
        .order_by("month")
    )

    top_parameters = (
        tests.values(parameter_name=F("parameter__name"))
        .annotate(
            total_tests=Count("id"),
            total_income=Sum("parameter__default_price"),
        )
        .order_by("-total_income")[:10]
    )

    analyst_workload = (
        tests.values(analyst_name=F("analyst__username"))
        .annotate(total_tests=Count("id"))
        .order_by("-total_tests")
    )

    sample_per_analyst = (
        tests.values(analyst_name=F("analyst__username"))
        .annotate(sample_count=Count("sample", distinct=True))
    )

    parameter_stats = (
        tests.values(parameter_name=F("parameter__name"))
        .annotate(test_count=Count("id"))
        .order_by("-test_count")
    )

    # ----- Today stats -----
    today_tests = TestAssignment.objects.filter(
        assigned_date__date=today,
        is_control=False,
    )
    today_total_income = (
        today_tests.aggregate(total=Sum("parameter__default_price"))["total"] or 0
    )
    today_test_count = today_tests.count()

    # ----- Finance: gross, expenses, net -----
    gross_income_val = (
        tests.aggregate(total=Sum("parameter__default_price"))["total"] or Decimal("0")
    )
    total_expenses_val = (
        expenses_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    )
    # ensure Decimal math
    gross_income = Decimal(gross_income_val)
    total_expenses = Decimal(total_expenses_val)
    net_income = gross_income - total_expenses

    # ----- Summary counts -----
    summary = {
        "samples_received": samples.count(),
        "test_assignments": tests.count(),
        "assigned_with_analysts": tests.filter(analyst__isnull=False).count(),
        "active_equipment": equipment.filter(is_active=True).count(),
        "expired_calibrations": CalibrationRecord.objects.filter(expires_on__lt=today).count(),
    }

    # ----- Optional UI-friendly summary card data -----
    summary_cards = [
        {"title": "Samples Received", "value": summary["samples_received"], "icon": "🧪", "class": "card-received"},
        {"title": "Tests Assigned", "value": summary["test_assignments"], "icon": "🔍", "class": "card-assigned"},
        {"title": "With Analysts", "value": summary["assigned_with_analysts"], "icon": "👩‍🔬", "class": "card-analysts"},
        {"title": "Active Equipment", "value": summary["active_equipment"], "icon": "⚙️", "class": "card-equipment"},
        {"title": "Expired Calibrations", "value": summary["expired_calibrations"], "icon": "⏰", "class": "card-calibrations"},
    ]

    logo_url = request.build_absolute_uri(static("images/logo.jpg"))

    # slice for dashboard (avoid loading large tables in page)
    recent_expenses = expenses_qs.order_by("-date", "-created")[:10] if hasattr(Expense, "created") else expenses_qs.order_by("-date")[:10]

    return {
        # raw objects
        "samples": samples,
        "tests": tests,
        "equipment": equipment,
        "calibrations": calibrations,
        "expenses": expenses_qs,          # full queryset (PDF/Excel)
        "recent_expenses": recent_expenses,  # lightweight for dashboard

        # summaries
        "summary": summary,
        "summary_cards": summary_cards,

        # date range
        "start_date": start_date,
        "end_date": end_date,
        "range_type": range_type,
        "range_label": range_label,

        # breakdowns
        "daily_totals": daily_totals,
        "weekly_totals": weekly_totals,
        "monthly_totals": monthly_totals,
        "top_parameters": top_parameters,
        "analyst_workload": analyst_workload,
        "parameter_stats": parameter_stats,
        "sample_per_analyst": sample_per_analyst,
        "analysis_summary": analysis_summary,

        # finance (backward compatibility: total_income == gross)
        "gross_income": gross_income,
        "total_income": gross_income,  # keep old key
        "total_expenses": total_expenses,
        "net_income": net_income,

        # today
        "today_total_income": today_total_income,
        "today_test_count": today_test_count,

        # misc
        "now": now(),
        "logo_url": logo_url,
    }





@login_required
def manager_report_view(request):
    context = get_manager_report_context(request)
    return render(request, "lims/report_view.html", context)


@login_required
def export_report_pdf(request):
    context = get_manager_report_context(request)
    html = get_template("lims/manager/report_pdf.html").render(context)
    pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()
    return HttpResponse(pdf, content_type="application/pdf")



@login_required
def export_report_excel(request):
    context = get_manager_report_context(request)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lab Report"

    ws.append(["Parameter", "Tests Run", "Revenue (₦)"])
    for row in context["top_parameters"]:
        ws.append([
            row["parameter_name"],
            row["total_tests"],
            float(row["total_income"] or 0),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=lab_report.xlsx"
    wb.save(response)
    return response




@login_required
def expense_create(request):
    # Get current dashboard range to preserve navigation after save
    range_type = request.GET.get("range", "month")

    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.entered_by = request.user
            expense.save()
            messages.success(request, "Expense recorded successfully.")

            # Redirect back to Manager Dashboard with preserved range
            base_url = reverse("manager_dashboard")
            query_string = urlencode({"range": range_type})
            return redirect(f"{base_url}?{query_string}")
    else:
        form = ExpenseForm()

    return render(request, "lims/expense_form.html", {
        "form": form,
        "range_type": range_type,  # pass to template if needed for UI
    })
