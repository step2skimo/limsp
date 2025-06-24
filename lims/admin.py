from django.contrib import admin
from .models import Client, Sample, ParameterGroup, Parameter, TestAssignment, TestResult
from .models import QCMetrics
from .models.equipment import Equipment, CalibrationRecord

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'name', 'organization', 'email', 'phone', 'token')
    readonly_fields = ('client_id',)
    search_fields = ('client_id', 'name', 'organization', 'email', 'phone')

@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ('sample_code', 'client', 'sample_type', 'status', 'received_date')
    search_fields = ('sample_code', 'client__client_id', 'client__name')
    list_filter = ('status', 'sample_type')

@admin.register(ParameterGroup)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_extension')
    search_fields = ('name',)

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'unit', 'method', 'ref_limit', 'default_equipment')
    autocomplete_fields = ['default_equipment']
    list_filter = ('group',)
    search_fields = ('name', 'method', 'unit')

@admin.register(TestAssignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('sample', 'parameter', 'analyst', 'assigned_date', 'status')
    list_filter = ('status', 'analyst', 'assigned_date')
    search_fields = ('sample__sample_code', 'parameter__name', 'analyst__username')

@admin.register(TestResult)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('test_assignment', 'value', 'source', 'recorded_by', 'recorded_at')
    list_filter = ('source', 'recorded_at')
    search_fields = ('test_assignment__sample__sample_code', 'test_assignment__parameter__name')

@admin.register(QCMetrics)
class QCMetricsAdmin(admin.ModelAdmin):
    list_display = ('test_assignment', 'expected_value', 'measured_value', 'recovery_percent', 'status')
    list_filter = ('status',)
    search_fields = ('test_assignment__sample__sample_code',)

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'serial_number', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'serial_number', 'model')

@admin.register(CalibrationRecord)
class CalibrationAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'calibration_date', 'expires_on', 'calibrated_by')
    list_filter = ('equipment__category',)
    ordering = ('-calibration_date',)
