from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Q
from lims.models import Sample, TestAssignment, Equipment, CalibrationRecord
from django.template.loader import get_template
from django.http import HttpResponse
from weasyprint import HTML
import openpyxl
from django.http import HttpResponse
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.db.models import Count, Sum, F


def manager_report_view(request):
    today = timezone.now().date()
    range_type = request.GET.get("range", "month")

    # ⏳ Determine date range
    if range_type == "week":
        start_date = today - timedelta(days=today.weekday())  # Monday
        end_date = start_date + timedelta(days=6)
    elif range_type == "day":
        start_date = end_date = today
    else:
        start_date = today.replace(day=1)
        end_date = today

    # 📦 Samples & Tests
    samples = Sample.objects.filter(received_date__range=(start_date, end_date))
    tests = TestAssignment.objects.filter(assigned_date__range=(start_date, end_date))
    equipment = Equipment.objects.all()
    calibrations = CalibrationRecord.objects.filter(calibration_date__range=(start_date, end_date))

    # 📊 Revenue Summaries
    daily_totals = (
        tests.annotate(day=TruncDay("assigned_date"))
             .values("day")
             .annotate(income=Sum("parameter__default_price"))
             .order_by("day")
    )
    weekly_totals = (
        TestAssignment.objects.annotate(week=TruncWeek("assigned_date"))
                              .values("week")
                              .annotate(income=Sum("parameter__default_price"))
                              .order_by("week")
    )
    monthly_totals = (
        TestAssignment.objects.annotate(month=TruncMonth("assigned_date"))
                              .values("month")
                              .annotate(income=Sum("parameter__default_price"))
                              .order_by("month")
    )

    top_parameters = (
        tests.values(parameter_name=F("parameter__name"))
             .annotate(total_tests=Count("id"), total_income=Sum("parameter__default_price"))
             .order_by("-total_income")[:10]
    )

    # 🎯 Today's Highlight
    today_tests = TestAssignment.objects.filter(assigned_date=today)
    today_total_income = today_tests.aggregate(total=Sum("parameter__default_price"))["total"] or 0
    today_test_count = today_tests.count()

    summary = {
        "samples_received": samples.count(),
        "test_assignments": tests.count(),
        "active_equipment": equipment.filter(is_active=True).count(),
        "expired_calibrations": CalibrationRecord.objects.filter(expires_on__lt=today).count()
    }

    context = {
        "samples": samples,
        "tests": tests,
        "equipment": equipment,
        "calibrations": calibrations,
        "summary": summary,
        "start_date": start_date,
        "end_date": end_date,
        "range_type": range_type,
        "daily_totals": daily_totals,
        "weekly_totals": weekly_totals,
        "monthly_totals": monthly_totals,
        "top_parameters": top_parameters,
        "today_total_income": today_total_income,
        "today_test_count": today_test_count,
    }

    return render(request, "lims/report_view.html", context)




def export_report_pdf(request):
    from .reports import manager_report_view  # optional reuse

    # replicate the context from manager_report_view
    response = manager_report_view(request)
    html = get_template("lims/manager/reports/report_pdf.html").render(response.context_data)
    pdf = HTML(string=html).write_pdf()

    return HttpResponse(pdf, content_type='application/pdf')



def export_report_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lab Report"

    ws.append(["Parameter", "Tests Run", "Revenue (₦)"])

    from .reports import manager_report_view
    response = manager_report_view(request)
    for row in response.context_data["top_parameters"]:
        ws.append([
            row["parameter__name"],
            row["total_tests"],
            float(row["total_income"]),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=lab_report.xlsx"
    wb.save(response)
    return response
