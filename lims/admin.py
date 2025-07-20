"""
Module: admin.py
Description: Django admin configurations for LIMS models, enabling 
customized management and display of Clients, Samples, Parameters, 
Equipment, Reagents, QC metrics, and other related entities.

"""

from django.contrib import admin

# === Importing Models ===
from .models import (
    Client, Sample, ParameterGroup, Parameter, TestAssignment, TestResult,
    QCMetrics, Reagent, ReagentUsage, ReagentIssue, Expense
)
from .models.equipment import Equipment, CalibrationRecord
from .models.ai import LabAIHistory


# ------------------------------------------------------------------------------------------------
# AI Chat History Admin
# ------------------------------------------------------------------------------------------------
@admin.register(LabAIHistory)
class LabAIHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for LabAIHistory model, which stores AI-related queries and answers.
    """
    list_display = ("user", "timestamp", "question")
    search_fields = ("question", "answer", "user__username")


# ------------------------------------------------------------------------------------------------
# Client & Sample Admin
# ------------------------------------------------------------------------------------------------
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Admin configuration for Client records.
    """
    list_display = ('client_id', 'name', 'organization', 'email', 'phone', 'token')
    readonly_fields = ('client_id',)  # Prevent editing the auto-generated client ID
    search_fields = ('client_id', 'name', 'organization', 'email', 'phone')


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    """
    Admin configuration for Sample records.
    """
    list_display = ('sample_code', 'client', 'sample_type', 'status', 'received_date')
    search_fields = ('sample_code', 'client__client_id', 'client__name')
    list_filter = ('status', 'sample_type')


# ------------------------------------------------------------------------------------------------
# Parameter & Parameter Group Admin
# ------------------------------------------------------------------------------------------------
@admin.register(ParameterGroup)
class GroupAdmin(admin.ModelAdmin):
    """
    Admin interface for Parameter Groups, which group related test parameters.
    """
    list_display = ('name', 'is_extension')
    search_fields = ('name',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Admin configuration for individual test parameters.
    """
    list_display = ('name', 'group', 'unit', 'method', 'ref_limit', 'default_equipment')
    autocomplete_fields = ['default_equipment']  # Speeds up equipment selection
    list_filter = ('group',)
    search_fields = ('name', 'method', 'unit')


# ------------------------------------------------------------------------------------------------
# Test Assignments & Results Admin
# ------------------------------------------------------------------------------------------------
@admin.register(TestAssignment)
class AssignmentAdmin(admin.ModelAdmin):
    """
    Admin interface for test assignments, linking samples to analysts.
    """
    list_display = ('sample', 'parameter', 'analyst', 'assigned_date', 'status')
    list_filter = ('status', 'analyst', 'assigned_date')
    search_fields = ('sample__sample_code', 'parameter__name', 'analyst__username')


@admin.register(TestResult)
class ResultAdmin(admin.ModelAdmin):
    """
    Admin configuration for test results.
    """
    list_display = ('test_assignment', 'value', 'source', 'recorded_by', 'recorded_at')
    list_filter = ('source', 'recorded_at')
    search_fields = (
        'test_assignment__sample__sample_code',
        'test_assignment__parameter__name'
    )


@admin.register(QCMetrics)
class QCMetricsAdmin(admin.ModelAdmin):
    """
    Admin interface for Quality Control metrics.
    """
    list_display = (
        'test_assignment', 'expected_value', 'measured_value',
        'recovery_percent', 'status'
    )
    list_filter = ('status',)
    search_fields = ('test_assignment__sample__sample_code',)


# ------------------------------------------------------------------------------------------------
# Equipment & Calibration Admin
# ------------------------------------------------------------------------------------------------
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for laboratory equipment.
    """
    list_display = ('name', 'serial_number', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'serial_number', 'model')


@admin.register(CalibrationRecord)
class CalibrationAdmin(admin.ModelAdmin):
    """
    Admin interface for calibration records of equipment.
    """
    list_display = ('equipment', 'calibration_date', 'expires_on', 'calibrated_by')
    list_filter = ('equipment__category',)
    ordering = ('-calibration_date',)


# ------------------------------------------------------------------------------------------------
# Reagent Management Admin
# ------------------------------------------------------------------------------------------------
@admin.register(Reagent)
class ReagentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Reagents in the laboratory.
    """
    list_display = [
        'name', 'batch_number', 'manufacturer', 'supplier_name',
        'number_of_containers', 'quantity_per_container', 'unit', 'expiry_date'
    ]
    search_fields = ['name', 'batch_number', 'supplier_name']
    list_filter = ['expiry_date']


@admin.register(ReagentUsage)
class ReagentUsageAdmin(admin.ModelAdmin):
    """
    Admin interface for tracking reagent usage.
    """
    list_display = ['reagent', 'analyst', 'quantity_used', 'date_used', 'purpose']
    list_filter = ['reagent', 'analyst', 'date_used']
    search_fields = ['reagent__name', 'analyst__username', 'purpose']


# Direct registration for ReagentIssue (no custom admin)
admin.site.register(ReagentIssue)


# ------------------------------------------------------------------------------------------------
# Expense Management Admin
# ------------------------------------------------------------------------------------------------
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """
    Admin configuration for managing lab expenses.
    """
    list_display = ("date", "description", "category", "amount", "entered_by", "created")
    list_filter = ("category", "date")
    search_fields = ("description", "note")
    date_hierarchy = "date"
