from django.shortcuts import render
from lims.models import Reagent
from lims.models.reagents import InventoryAudit
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from lims.forms import ReagentForm, UseReagentForm, InventoryAuditForm
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from lims.models import ReagentUsage, ReagentIssue
from django.contrib.auth import get_user_model
import csv
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
from django.http import FileResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.timezone import now
from django.utils.timezone import timedelta
from django.contrib import messages
from django.db.models import Sum
import csv
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.db.models import Count
from django.utils import timezone
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from lims.forms import ReagentUsageForm, ReagentRequestForm, ReagentIssueForm, ReagentRequestItemFormSet, ReagentRequestItem, ReagentRequestEmailForm, ReagentRequestFormSet
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib import messages
from django.core.mail import EmailMessage
from django.template.loader import render_to_string



def generate_csv_response(filename, header, rows):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response

def generate_pdf_response(filename, title, headers, rows):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 40, title)

    y = height - 80
    p.setFont("Helvetica", 10)

    # Write headers
    for i, h in enumerate(headers):
        p.drawString(50 + i * 150, y, h)

    y -= 20
    for row in rows:
        for i, cell in enumerate(row):
            p.drawString(50 + i * 150, y, str(cell))
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{filename}.pdf"'
    })


@login_required
def export_consumption_csv(request):
    data = ReagentUsage.objects.values('reagent__name').annotate(total_used=Sum('quantity_used'))
    rows = [(d['reagent__name'], d['total_used']) for d in data]
    return generate_csv_response("consumption_report", ["Reagent", "Total Used"], rows)

@login_required
def export_consumption_pdf(request):
    data = ReagentUsage.objects.values('reagent__name').annotate(total_used=Sum('quantity_used'))
    rows = [(d['reagent__name'], d['total_used']) for d in data]
    return generate_pdf_response("consumption_report", "Consumption Report", ["Reagent", "Total Used"], rows)

@login_required
def safety_data_sheets(request):
    reagents_with_sds = Reagent.objects.exclude(safety_data_sheet='').exclude(safety_data_sheet=None)
    return render(request, 'lims/reagents/safety_data_sheets.html', {
        'reagents': reagents_with_sds
    })

@login_required
def certificate_analysis(request):
    reagents_with_coa = Reagent.objects.exclude(certificate_of_analysis='').exclude(certificate_of_analysis=None)
    return render(request, 'lims/reagents/certificate_analysis.html', {
        'reagents': reagents_with_coa
    })



@login_required
def inventory_dashboard(request):
    user = request.user
    groups = user.groups.values_list('name', flat=True)

    is_manager = 'Manager' in groups
    is_analyst = 'Analyst' in groups

    now = timezone.now()

    # Statistics
    total_reagents = Reagent.objects.count()

    low_stock = Reagent.objects.filter(
        number_of_containers__lte=5
    ).count()

    expiring_soon = Reagent.objects.filter(
        expiry_date__isnull=False,
        expiry_date__lte=now + timedelta(days=30)
    ).count()

    critical_items = Reagent.objects.filter(
        Q(number_of_containers__lte=2) |
        Q(expiry_date__isnull=False, expiry_date__lte=now + timedelta(days=7))
    ).count()

    context = {
        'is_manager': is_manager,
        'is_analyst': is_analyst,
        'total_reagents': total_reagents,
        'low_stock': low_stock,
        'expiring_soon': expiring_soon,
        'critical_items': critical_items,
    }

    return render(request, 'lims/reagents/inventory_dashboard.html', context)



def download_reagent_pdf(request, pk):
    reagent = get_object_or_404(Reagent, pk=pk)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)

    p.drawString(50, 800, f"Reagent Report: {reagent.name}")
    p.drawString(50, 780, f"Batch Number: {reagent.batch_number}")
    p.drawString(50, 760, f"Manufacturer: {reagent.manufacturer}")
    p.drawString(50, 740, f"Supplier: {reagent.supplier_name}")
    p.drawString(50, 720, f"Contact: {reagent.supplier_contact}")
    p.drawString(50, 700, f"Email: {reagent.supplier_email}")
    p.drawString(50, 680, f"Received: {reagent.date_received}")
    p.drawString(50, 660, f"Expiry: {reagent.expiry_date}")
    p.drawString(50, 640, f"Quantity: {reagent.quantity} {reagent.unit}")
    p.drawString(50, 620, f"Storage: {reagent.storage_condition}")

    sds_status = "Available" if reagent.safety_data_sheet else "Not uploaded"
    coa_status = "Available" if reagent.certificate_of_analysis else "Not uploaded"
    p.drawString(50, 600, f"SDS: {sds_status}")
    p.drawString(50, 580, f"COA: {coa_status}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"{reagent.name}_report.pdf")


def download_inventory_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reagent_inventory.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Name', 'Batch Number', 'Manufacturer',
        'Supplier Name', 'Bottles', 'Qty per Bottle', 'Total Qty', 'Unit',
        'Expiry Date', 'Storage Condition'
    ])

    for reagent in Reagent.objects.all():
        writer.writerow([
            reagent.name, reagent.batch_number, reagent.manufacturer,
            reagent.supplier_name, reagent.number_of_bottles,
            reagent.quantity_per_bottle, reagent.total_quantity,
            reagent.unit, reagent.expiry_date, reagent.storage_condition
        ])

    return response



@login_required
def add_reagent(request):
    if request.method == 'POST':
        form = ReagentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('reagent_list')
    else:
        form = ReagentForm()
    return render(request, 'lims/reagents/add_reagent.html', {'form': form})

@login_required
def upload_documents(request, pk):
    reagent = get_object_or_404(Reagent, pk=pk)
    if request.method == 'POST':
        form = ReagentForm(request.POST, request.FILES, instance=reagent)
        if form.is_valid():
            form.save()
            return redirect('reagent_detail', pk=reagent.pk)
    else:
        form = ReagentForm(instance=reagent)
    return render(request, 'lims/reagents/upload_documents.html', {
        'form': form,
        'reagent': reagent
    })



def use_reagent(request):
    if request.method == "POST":
        form = ReagentUsageForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Reagent usage logged successfully.")
                return redirect('use_reagent')
            except ValidationError as e:
                messages.error(request, e.messages[0])  
    else:
        form = ReagentUsageForm()
    return render(request, 'lims/reagents/use_reagent.html', {'form': form})




def request_reagent(request):
    if request.method == 'POST':
        form = ReagentRequestEmailForm(request.POST)
        formset = ReagentRequestFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            request.session['email'] = form.cleaned_data['email']
            items = []

            for f in formset:
                if f.cleaned_data:
                    items.append(f.cleaned_data)

            request.session['items'] = items
            return redirect('preview_reagent_request')
    else:
        form = ReagentRequestEmailForm()
        formset = ReagentRequestFormSet()

    return render(request, 'lims/reagents/request_reagent.html', {
        'form': form,
        'formset': formset
    })

def preview_reagent_request(request):
    email = request.session.get('email')
    items = request.session.get('items', [])

    total = sum(float(item['amount']) for item in items)

    return render(request, 'lims/reagents/preview_reagent_request.html', {
        'email': email,
        'items': items,
        'total': total,
    })


def send_reagent_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        items_raw = request.POST.getlist('items')
        items = []
        total = 0

        for raw in items_raw:
            name, qty, unit, amt = raw.split("||")
            items.append({'name': name, 'qty': qty, 'unit': unit, 'amt': float(amt)})
            total += float(amt)

        # HTML message via template
        context = {
            'requested_by': request.user.get_full_name() or request.user.username,
            'email': email,
            'reagents': items,
            'total_amount': total
        }

        try:
            html_message = render_to_string('lims/reagents/reagent_request_email.html', context)

            mail = EmailMessage(
                subject='🧪 New Reagent Request',
                body=html_message,
                from_email='noreply@jaageelab.com',
                to=[email]
            )
            mail.content_subtype = 'html'
            mail.send()

            messages.success(request, f'✅ Reagent request sent successfully to {email}')
        except Exception as e:
            messages.error(request, f'❌ Failed to send request: {e}')

        return redirect('request_reagent')



def report_issue(request):
    if request.method == 'POST':
        form = ReagentIssueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Issue reported. QA will review it.')
            return redirect('report_issue')
    else:
        form = ReagentIssueForm()
    return render(request, 'lims/reagents/report_issue.html', {'form': form})

@login_required
def reagent_issue_list(request):
    issues = ReagentIssue.objects.all().order_by('-date_reported')
    return render(request, 'lims/reagents/issue_list.html', {'issues': issues})


@login_required
def reagent_list(request):
    reagents = Reagent.objects.all()
    today = timezone.now().date()
    near_expiry_date = today + timedelta(days=30)

    return render(request, 'lims/reagents/reagent_list.html', {
        'reagents': reagents,
        'today': today,
        'near_expiry_date': near_expiry_date,
    })


def reagent_detail(request, pk):
    reagent = get_object_or_404(Reagent, pk=pk)
    missing_docs = {
        'sds': not reagent.safety_data_sheet,
        'coa': not reagent.certificate_of_analysis
    }
    return render(request, 'lims/reagents/reagent_detail.html', {
        'reagent': reagent,
        'missing_docs': missing_docs
    })


@login_required
def inventory_audit(request):
    if request.method == 'POST':
        form = InventoryAuditForm(request.POST)
        if form.is_valid():
            audit = form.save(commit=False)
            audit.audited_by = request.user
            audit.save()
            messages.success(request, 'Inventory audit completed successfully!')
            return redirect('inventory_dashboard')
    else:
        form = InventoryAuditForm()
    
    recent_audits = InventoryAudit.objects.all().order_by('-date_conducted')[:10]
    return render(request, 'lims/reagents/inventory_audit.html', {
        'form': form,
        'recent_audits': recent_audits
    })

@login_required
def consumption_report(request):
    six_months_ago = timezone.now() - timedelta(days=180)
    consumption_data = ReagentUsage.objects.filter(
        date_used__gte=six_months_ago
    ).values('reagent__name').annotate(
        total_used=Sum('quantity_used')
    ).order_by('-total_used')
    
    return render(request, 'lims/reagents/consumption_report.html', {
        'consumption_data': consumption_data
    })

@login_required
def expiry_report(request):
    upcoming_expiry = timezone.now() + timedelta(days=60)
    expiring_reagents = Reagent.objects.filter(
        expiry_date__lte=upcoming_expiry
    ).order_by('expiry_date')
    
    return render(request, 'lims/reagents/expiry_report.html', {
        'expiring_reagents': expiring_reagents
    })

@login_required
def supplier_evaluation(request):
    suppliers = Reagent.objects.values('supplier_name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return render(request, 'lims/reagents/supplier_evaluation.html', {
        'suppliers': suppliers
    })
