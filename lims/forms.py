"""
Module: forms.py
Description: Contains all form classes used in the LIMS application, including
model-based forms for data entry (e.g., Reagents, Equipment, QC Metrics) and 
custom forms for dynamic parameter selection and result entry.

"""

from django import forms
from decimal import Decimal, ROUND_HALF_UP
from itertools import groupby
from django.forms import formset_factory, modelformset_factory

# === Import Models ===
from .models import (
    Client, Sample, Parameter, ParameterGroup, QCMetrics,
    Equipment, TestResult, TestEnvironment, TestAssignment, Expense
)
from lims.models import QCMetrics, Reagent, ReagentUsage, ReagentRequest, ReagentIssue
from .models.reagents import InventoryAudit, ReagentRequestItem
from .models.coa import COAInterpretation
from .models import Equipment, CalibrationRecord

# ------------------------------------------------------------------------------------------------
# Expense Form
# ------------------------------------------------------------------------------------------------
class ExpenseForm(forms.ModelForm):
    """
    Form for creating or updating Expense records.
    """
    class Meta:
        model = Expense
        fields = ['date', 'category', 'description', 'amount']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


# ------------------------------------------------------------------------------------------------
# Equipment Forms
# ------------------------------------------------------------------------------------------------
class EquipmentForm(forms.ModelForm):
    """
    Form for adding or editing Equipment records.
    """
    class Meta:
        model = Equipment
        fields = [
            'name', 'serial_number', 'model', 'category', 'date_installed',
            'manufacturer', 'is_active', 'parameters_supported'
        ]


class CalibrationRecordForm(forms.ModelForm):
    """
    Form for creating or updating Calibration Records linked to Equipment.
    """
    class Meta:
        model = CalibrationRecord
        fields = ['calibration_date', 'calibrated_by', 'expires_on', 'comments', 'certificate']


# ------------------------------------------------------------------------------------------------
# Reagent Management Forms
# ------------------------------------------------------------------------------------------------
class ReagentUsageForm(forms.ModelForm):
    """
    Form for logging reagent usage by an analyst.
    """
    class Meta:
        model = ReagentUsage
        fields = ['reagent', 'quantity_used', 'analyst']


class ReagentRequestForm(forms.ModelForm):
    """
    Form for creating a new reagent request.
    """
    class Meta:
        model = ReagentRequest
        fields = ['requested_by', 'email', 'reason']


class ReagentRequestItemForm(forms.ModelForm):
    """
    Form for specifying individual reagent items in a request.
    """
    class Meta:
        model = ReagentRequestItem
        fields = ['reagent_name', 'quantity', 'unit', 'amount']


# Formset for multiple reagent request items
ReagentRequestItemFormSet = modelformset_factory(
    ReagentRequestItem,
    form=ReagentRequestItemForm,
    extra=1,
    can_delete=True
)


class ReagentRequestEmailForm(forms.Form):
    """
    Form for sending reagent request details via email.
    """
    email = forms.EmailField(
        label="Recipient Email",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )


class ReagentRequestItemForm(forms.Form):
    """
    Custom form (non-model) for adding reagent request details dynamically.
    """
    reagent_name = forms.CharField(
        label="Reagent Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    quantity = forms.FloatField(
        label="Quantity",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"})
    )
    unit = forms.CharField(
        label="Unit",
        max_length=10,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    amount = forms.FloatField(
        label="Amount",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"})
    )


# Non-model formset for dynamic reagent requests
ReagentRequestFormSet = formset_factory(ReagentRequestItemForm, extra=1)


class ReagentIssueForm(forms.ModelForm):
    """
    Form for reporting issues with reagents.
    """
    class Meta:
        model = ReagentIssue
        fields = ['reagent', 'issue_type', 'description', 'reported_by']


class ReagentForm(forms.ModelForm):
    """
    Form for adding or editing Reagent records.
    """
    class Meta:
        model = Reagent
        fields = [
            'name', 'batch_number', 'manufacturer',
            'supplier_name', 'supplier_contact', 'supplier_email',
            'date_received', 'expiry_date',
            'number_of_containers', 'quantity_per_container', 'unit',
            'storage_condition',
            'safety_data_sheet', 'certificate_of_analysis'
        ]
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }


class UseReagentForm(forms.ModelForm):
    """
    Form for recording the usage of reagents.
    """
    class Meta:
        model = ReagentUsage
        fields = ['reagent', 'quantity_used', 'purpose']
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'reagent': 'Select Reagent',
            'quantity_used': 'Containers Used',
            'purpose': 'Purpose of Use',
        }


# ------------------------------------------------------------------------------------------------
# Client & Sample Forms
# ------------------------------------------------------------------------------------------------
class ClientForm(forms.ModelForm):
    """
    Form for adding or editing Client records.
    """
    class Meta:
        model = Client
        fields = ['name', 'organization', 'email', 'phone', 'address']


class SampleFormWithParameters(forms.ModelForm):
    """
    Form for submitting samples with parameter selections.
    """
    parameters = forms.ModelMultipleChoiceField(
        queryset=Parameter.objects.select_related('group').all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Sample
        fields = ['sample_type', 'weight', 'sample_code', 'parameters']

    def __init__(self, *args, **kwargs):
        """
        Custom initialization (reserved for future customization).
        """
        super().__init__(*args, **kwargs)


class ParameterSelectionForm(forms.Form):
    """
    Form for dynamically displaying parameters grouped by parameter group.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        groups = ParameterGroup.objects.prefetch_related('parameter_set')
        for group in groups:
            parameters = group.parameter_set.all()
            self.fields[f'group_{group.id}'] = forms.MultipleChoiceField(
                label=group.name,
                required=False,
                choices=[
                    (p.id, f"{p.name} ({p.method}) ₦{p.default_price}") for p in parameters
                ],
                widget=forms.CheckboxSelectMultiple
            )


# ------------------------------------------------------------------------------------------------
# Inventory Audit Form
# ------------------------------------------------------------------------------------------------
class InventoryAuditForm(forms.ModelForm):
    """
    Form for recording physical inventory audits.
    """
    class Meta:
        model = InventoryAudit
        fields = ['reagent', 'actual_containers', 'notes']


# ------------------------------------------------------------------------------------------------
# QC Metrics Form
# ------------------------------------------------------------------------------------------------
class QCMetricsForm(forms.ModelForm):
    """
    Form for recording Quality Control (QC) metrics and validating measured values.
    """
    min_acceptable = forms.DecimalField(disabled=True, required=False, label="Min Acceptable")
    max_acceptable = forms.DecimalField(disabled=True, required=False, label="Max Acceptable")

    measured_value = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01'}),
        required=True,
        label="Measured Value"
    )

    tolerance = forms.DecimalField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = QCMetrics
        fields = [
            'measured_value', 'expected_value', 'tolerance',
            'min_acceptable', 'max_acceptable', 'notes'
        ]
        widgets = {
            'expected_value': forms.NumberInput(attrs={
                'step': '0.01',
                'readonly': 'readonly'
            }),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        """
        Initializes QC Metrics form with control specifications from the associated test parameter.
        """
        self.test_assignment = kwargs.pop('test_assignment', None)
        super().__init__(*args, **kwargs)

        if not self.test_assignment:
            self.test_assignment = getattr(self.instance, 'test_assignment', None)

        if self.test_assignment:
            spec = getattr(self.test_assignment.parameter, 'control_spec', None)
            if spec:
                self.fields['min_acceptable'].initial = spec.min_acceptable
                self.fields['max_acceptable'].initial = spec.max_acceptable

                if not self.instance.expected_value and spec.expected_value is not None:
                    self.fields['expected_value'].initial = spec.expected_value
                    self.instance.expected_value = spec.expected_value

                if not self.instance.tolerance and spec.default_tolerance is not None:
                    self.fields['tolerance'].initial = spec.default_tolerance
                    self.instance.tolerance = spec.default_tolerance

    def clean(self):
        """
        Cleans and validates measured values against acceptable control limits.
        """
        cleaned = super().clean()

        measured = cleaned.get("measured_value")
        min_val = self.fields['min_acceptable'].initial
        max_val = self.fields['max_acceptable'].initial

        if measured is not None:
            measured = Decimal(measured).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cleaned['measured_value'] = measured
            self.instance.measured_value = measured

            try:
                if float(measured) < float(min_val) or float(measured) > float(max_val):
                    self.instance.status = "fail"
                else:
                    self.instance.status = "pass"
            except (TypeError, ValueError):
                self.instance.status = None

        return cleaned


# ------------------------------------------------------------------------------------------------
# Test Results & Environment Forms
# ------------------------------------------------------------------------------------------------
class ResultEntryForm(forms.ModelForm):
    """
    Form for entering test results for a sample parameter.
    """
    class Meta:
        model = TestResult
        fields = ['value']


class TestEnvironmentForm(forms.ModelForm):
    """
    Form for recording environmental conditions (e.g., temperature, humidity)
    during testing.
    """
    class Meta:
        model = TestEnvironment
        fields = ['temperature', 'humidity', 'instrument']
        labels = {
            'temperature': 'Temperature (°C)',
            'humidity': 'Humidity (%)',
            'instrument': 'Equipment Used',
        }

    def clean(self):
        """
        Validate temperature and humidity ranges to ensure test reliability.
        """
        cleaned = super().clean()
        temp = cleaned.get("temperature")
        humidity = cleaned.get("humidity")

        errors = {}
        if temp is not None and not (10 <= temp <= 40):
            errors['temperature'] = "Temperature should be between 10°C and 40°C"
        if humidity is not None and not (10 <= humidity <= 90):
            errors['humidity'] = "Humidity should be between 10% and 90%"

        if errors:
            raise forms.ValidationError(errors)

        return cleaned


# ------------------------------------------------------------------------------------------------
# COA Forms
# ------------------------------------------------------------------------------------------------
class COAInterpretationForm(forms.ModelForm):
    """
    Form for creating or updating Certificate of Analysis (COA) interpretation summaries.
    """
    class Meta:
        model = COAInterpretation
        fields = ['summary_text']
        widgets = {
            'summary_text': forms.Textarea(attrs={'rows': 6, 'cols': 80}),
        }
