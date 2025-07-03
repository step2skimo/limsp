from django import forms
from .models import Client, Sample, Parameter, ParameterGroup, QCMetrics, Equipment, TestResult
from django.forms import formset_factory
from django import forms
from decimal import Decimal, ROUND_HALF_UP
from lims.models import QCMetrics
from .models.reagent import ReagentUsage, ReagentLot
from itertools import groupby


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





class GroupedLotChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"Lot {obj.lot_number} ({obj.quantity}{obj.unit} remaining)"

    def optgroups(self, name, value, attrs=None):
        queryset = self.queryset.select_related("reagent").order_by("reagent__name")
        groups = []
        for reagent_name, lots in groupby(queryset, key=lambda l: l.reagent.name):
            group_lots = list(lots)
            group_choices = [(lot.pk, self.label_from_instance(lot)) for lot in group_lots]
            groups.append((reagent_name, group_choices, 0))
        return groups


class ReagentUsageForm(forms.ModelForm):
    class Meta:
        model = ReagentUsage
        fields = ['parameter', 'lot', 'quantity_used', 'purpose']
        widgets = {
            'parameter': forms.Select(attrs={'class': 'form-select'}),
            'quantity_used': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2.5'
            }),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Grouped reagent lots by reagent name
        self.fields['lot'] = GroupedLotChoiceField(
            queryset=ReagentLot.objects.filter(status='active'),
            widget=forms.Select(attrs={'class': 'form-select'}),
            label='Reagent Lot'
        )

        # Order parameters nicely
        self.fields['parameter'].queryset = Parameter.objects.select_related('group').order_by('group__name', 'name')

    def clean_quantity_used(self):
        quantity = self.cleaned_data.get('quantity_used')
        lot = self.cleaned_data.get('lot')

        if lot and quantity:
            if quantity > lot.quantity:
                raise forms.ValidationError(
                    f"Not enough reagent available. Only {lot.quantity} {lot.unit} left in Lot {lot.lot_number}."
                )
        return quantity
