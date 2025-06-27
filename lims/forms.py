from django import forms
from .models import Client, Sample, Parameter, ParameterGroup, QCMetrics, Equipment, TestResult
from django.forms import formset_factory
from django import forms
from decimal import Decimal, ROUND_HALF_UP
from lims.models import QCMetrics

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'organization', 'email', 'phone', 'address']

class SampleFormWithParameters(forms.ModelForm):
    parameters = forms.ModelMultipleChoiceField(
        queryset=Parameter.objects.select_related('group').all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Sample
        fields = ['sample_type', 'weight', 'sample_code', 'parameters']


class ParameterSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        groups = ParameterGroup.objects.prefetch_related('parameter_set')
        for group in groups:
            parameters = group.parameter_set.all()
            self.fields[f'group_{group.id}'] = forms.MultipleChoiceField(
                label=group.name,
                required=False,
                choices=[(p.id, f"{p.name} ({p.method}) ₦{p.default_price}") for p in parameters],
                widget=forms.CheckboxSelectMultiple
            )


class QCMetricsForm(forms.ModelForm):
    min_acceptable = forms.DecimalField(
        disabled=True, required=False, label="Min Acceptable"
    )
    max_acceptable = forms.DecimalField(
        disabled=True, required=False, label="Max Acceptable"
    )

    measured_value = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01'}),
        required=True,
        label="Measured Value"
    )

    class Meta:
        model = QCMetrics
        fields = [
            'expected_value', 'measured_value', 'tolerance',
            'min_acceptable', 'max_acceptable', 'notes'
        ]
        widgets = {
            'expected_value': forms.NumberInput(attrs={'step': '0.01'}),
            'tolerance': forms.NumberInput(attrs={'step': '0.01'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        test_assignment = kwargs.pop('test_assignment', None)
        super().__init__(*args, **kwargs)

        self.test_assignment = test_assignment or getattr(self.instance, "test_assignment", None)

        if self.test_assignment and hasattr(self.test_assignment.parameter, 'control_spec'):
            spec = self.test_assignment.parameter.control_spec

            self.fields['min_acceptable'].initial = spec.min_acceptable
            self.fields['max_acceptable'].initial = spec.max_acceptable

            if not self.instance.expected_value and getattr(spec, 'expected_value', None):
                self.fields['expected_value'].initial = spec.expected_value

            if not self.instance.tolerance and getattr(spec, 'default_tolerance', None):
                self.fields['tolerance'].initial = spec.default_tolerance

    def clean(self):
        cleaned = super().clean()
        val = cleaned.get("measured_value")

        if val is not None:
            val = Decimal(val).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cleaned["measured_value"] = val
            self.instance.measured_value = val

            min_val = self.fields['min_acceptable'].initial
            max_val = self.fields['max_acceptable'].initial

            try:
                if float(val) < float(min_val) or float(val) > float(max_val):
                    self.instance.status = "fail"
                else:
                    self.instance.status = "pass"
            except (TypeError, ValueError):
                self.instance.status = None

        return cleaned


class ResultEntryForm(forms.ModelForm):
    temp = forms.DecimalField(required=False, max_digits=5, decimal_places=2)
    humidity = forms.DecimalField(required=False, max_digits=5, decimal_places=2)
    pressure = forms.DecimalField(required=False, max_digits=6, decimal_places=2)
    equipment_used = forms.ModelChoiceField(
        queryset=Equipment.objects.filter(is_active=True),
        required=False,
        empty_label="— Select —"
    )

    class Meta:
        model = TestResult
        fields = ['value', 'temp', 'humidity', 'pressure', 'equipment_used']  
