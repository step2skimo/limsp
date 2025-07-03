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


from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Count, Avg, FloatField, DurationField, ExpressionWrapper
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from lims.models import TestAssignment, QCMetrics

@login_required
def analyst_productivity_view(request):
    today = timezone.now().date()
    range_type = request.GET.get("range", "month")

    # Determine start_date and end_date
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

    # Build assignment queryset
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

    # Annotate assignments
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

    # Productivity per analyst
    productivity = (
        assignments
        .values(analyst_name=F("analyst__username"))
        .annotate(
            tests=Count("id"),
            samples=Count("sample", distinct=True),
            params=Count("parameter", distinct=True),
            avg_tat=Avg("tat"),
            avg_duration=Avg("duration"),
            extension_tests=Count("id", filter=Q(parameter__group__is_extension=True))
        )
        .annotate(
            extension_load=ExpressionWrapper(
                100.0 * F("extension_tests") / F("tests"),
                output_field=FloatField()
            )
        )
        .order_by("-tests")
    )

    # QC pass rate from QCMetrics
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

    def format_td(td):
        if not td:
            return "—"
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    for person in productivity:
        person["avg_tat_human"] = format_td(person["avg_tat"])
        person["avg_duration_human"] = format_td(person["avg_duration"])
        person["qc_pass_rate"] = qc_pass_rate_map.get(person["analyst_name"], 100.0)

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
        "avg_tat_human": total_avg_tat,
        "extension_rate": round(
            100.0 * sum(p["extension_tests"] for p in productivity) / (total_tests or 1), 1
        ) if productivity else 0.0,
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

    if range_type == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif range_type == "day":
        start_date = end_date = today
    elif range_type == "last_month":
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1)
        end_date = last_day_last_month
    elif range_type == "all_time":
        start_date = None
        end_date = today
    else:  # current month
        start_date = today.replace(day=1)
        end_date = today

    # Query filters
    sample_filters = {"received_date__lte": end_date}
    test_filters = {"assigned_date__date__lte": end_date, "is_control": False}
    calibration_filters = {"calibration_date__lte": end_date}

    if start_date:
        sample_filters["received_date__gte"] = start_date
        test_filters["assigned_date__date__gte"] = start_date
        calibration_filters["calibration_date__gte"] = start_date

    samples = Sample.objects.filter(**sample_filters).exclude(sample_type__iexact="QC")
    tests = TestAssignment.objects.select_related("parameter", "sample", "analyst").filter(**test_filters)
    equipment = Equipment.objects.all()
    calibrations = CalibrationRecord.objects.filter(**calibration_filters)

    # Report aggregations
    analysis_summary = tests.values(
        date_received=F("sample__received_date"),
        client_name=F("sample__client__name"),
        parameter_group=F("parameter__group__name")
    ).annotate(
        sample_count=Count("sample", distinct=True),
        income=Sum("parameter__default_price")
    ).order_by("-date_received")

    daily_totals = tests.annotate(day=TruncDay("assigned_date")).values("day").annotate(
        income=Sum("parameter__default_price")).order_by("day")

    weekly_totals = tests.annotate(week=TruncWeek("assigned_date")).values("week").annotate(
        income=Sum("parameter__default_price")).order_by("week")

    monthly_totals = tests.annotate(month=TruncMonth("assigned_date")).values("month").annotate(
        income=Sum("parameter__default_price")).order_by("month")

    top_parameters = tests.values(parameter_name=F("parameter__name")).annotate(
        total_tests=Count("id"),
        total_income=Sum("parameter__default_price")
    ).order_by("-total_income")[:10]

    analyst_workload = tests.values(analyst_name=F("analyst__username")).annotate(
        total_tests=Count("id")).order_by("-total_tests")

    sample_per_analyst = tests.values(analyst_name=F("analyst__username")).annotate(
        sample_count=Count("sample", distinct=True))

    parameter_stats = tests.values(parameter_name=F("parameter__name")).annotate(
        test_count=Count("id")).order_by("-test_count")

    today_tests = TestAssignment.objects.filter(assigned_date__date=today, is_control=False)
    today_total_income = today_tests.aggregate(total=Sum("parameter__default_price"))["total"] or 0
    today_test_count = today_tests.count()

    total_income = tests.aggregate(total=Sum("parameter__default_price"))["total"] or 0

    summary = {
        "samples_received": samples.count(),
        "test_assignments": tests.count(),
        "assigned_with_analysts": tests.filter(analyst__isnull=False).count(),
        "active_equipment": equipment.filter(is_active=True).count(),
        "expired_calibrations": CalibrationRecord.objects.filter(expires_on__lt=today).count()
    }

    return {
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
        "analyst_workload": analyst_workload,
        "parameter_stats": parameter_stats,
        "sample_per_analyst": sample_per_analyst,
        "analysis_summary": analysis_summary,
        "total_income": total_income,
        "today_total_income": today_total_income,
        "today_test_count": today_test_count,
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
