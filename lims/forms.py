from django import forms
from .models import Client, Sample, Parameter, ParameterGroup, QCMetrics, Equipment, TestResult
from django.forms import formset_factory


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
    min_acceptable = forms.DecimalField(disabled=True, required=False, label="Min Acceptable")
    max_acceptable = forms.DecimalField(disabled=True, required=False, label="Max Acceptable")

    class Meta:
        model = QCMetrics
        fields = ['expected_value', 'measured_value', 'tolerance', 'min_acceptable', 'max_acceptable', 'notes']
        widgets = {
            'expected_value': forms.NumberInput(attrs={'step': '0.01'}),
            'measured_value': forms.NumberInput(attrs={'step': '0.01'}),
            'tolerance': forms.NumberInput(attrs={'step': '0.01'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        test_assignment = kwargs.pop('test_assignment', None)
        super().__init__(*args, **kwargs)

        self.fields['measured_value'].required = True

        if test_assignment and hasattr(test_assignment.parameter, 'control_spec'):
            spec = test_assignment.parameter.control_spec
            self.fields['min_acceptable'].initial = spec.min_acceptable
            self.fields['max_acceptable'].initial = spec.max_acceptable

            if not self.instance.expected_value and spec.expected_value is not None:
                self.fields['expected_value'].initial = spec.expected_value

            if not self.instance.tolerance and spec.default_tolerance is not None:
                self.fields['tolerance'].initial = spec.default_tolerance

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
