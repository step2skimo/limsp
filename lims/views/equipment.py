from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
import csv
from lims.models import Equipment, CalibrationRecord
from lims.forms import EquipmentForm, CalibrationRecordForm
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from users.models import User


def is_manager(user):
    return user.is_manager

@user_passes_test(is_manager)
def add_calibration(request, equipment_id):
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    if request.method == "POST":
        form = CalibrationRecordForm(request.POST, request.FILES)
        if form.is_valid():
            calibration = form.save(commit=False)
            calibration.equipment = equipment
            calibration.save()
            return redirect('equipment_detail', pk=equipment.id)
    else:
        form = CalibrationRecordForm()
    return render(request, 'lims/equipment/calibration_form.html', {'form': form, 'equipment': equipment})


@user_passes_test(is_manager)
def export_equipment_pdf(request):
    equipments = Equipment.objects.all()
    template_path = 'lims/equipment/equipment_pdf.html'
    context = {'equipments': equipments}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="equipment_list.pdf"'
    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF generation error')
    return response




@user_passes_test(is_manager)
def equipment_dashboard(request):
    equipments = Equipment.objects.prefetch_related('parameters_supported', 'calibrations').all()
    
    filter_type = request.GET.get('filter')
    today = timezone.now().date()

    if filter_type == 'expired':
        equipments = [eq for eq in equipments if any(not cal.is_valid() for cal in eq.calibrations.all())]
    elif filter_type == 'due_soon':
        equipments = [eq for eq in equipments if any(cal.expires_on <= today + timedelta(days=30) and cal.is_valid() for cal in eq.calibrations.all())]

    return render(request, 'lims/equipment/equipment_dashboard.html', {'equipments': equipments})

@user_passes_test(is_manager)
def equipment_detail(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    calibrations = equipment.calibrations.all()
    return render(request, 'lims/equipment/equipment_detail.html', {'equipment': equipment, 'calibrations': calibrations})

@user_passes_test(is_manager)
def add_equipment(request):
    if request.method == "POST":
        form = EquipmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('equipment_dashboard')
    else:
        form = EquipmentForm()
    return render(request, 'lims/equipment/equipment_form.html', {'form': form})

@user_passes_test(is_manager)
def edit_equipment(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == "POST":
        form = EquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            form.save()
            return redirect('equipment_dashboard')
    else:
        form = EquipmentForm(instance=equipment)
    return render(request, 'lims/equipment/equipment_form.html', {'form': form})

@user_passes_test(is_manager)
def delete_equipment(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    equipment.delete()
    return redirect('equipment_dashboard')

@user_passes_test(is_manager)
def export_equipment_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="equipment.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Serial Number', 'Model', 'Category', 'Date Installed', 'Manufacturer'])
    for eq in Equipment.objects.all():
        writer.writerow([eq.name, eq.serial_number, eq.model, eq.category, eq.date_installed, eq.manufacturer])
    return response
