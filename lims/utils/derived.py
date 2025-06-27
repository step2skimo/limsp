from lims.models import Parameter, TestAssignment, TestResult

def _note_for(param):
    return {
        "Carbohydrate": "Calculated as: 100 – (Protein + Fat + Ash + Moisture + Fiber)",
        "ME": "ME = (Protein × 4) + (Fat × 9) + (Carbohydrate × 4)"
    }.get(param, "")


def _inject_derived_result(param_name, value, sample, recorded_by=None):

    try:
        param = Parameter.objects.get(name=param_name)
        assignment = TestAssignment.objects.get(sample=sample, parameter=param)
        TestResult.objects.update_or_create(
            test_assignment=assignment,
            defaults={
                'value': round(value, 2),
                'source': 'system',
                'calculation_note': _note_for(param_name),
                'recorded_by': recorded_by
            }
        )
        assignment.status = 'completed'
        assignment.save()
    except (Parameter.DoesNotExist, TestAssignment.DoesNotExist):
        pass
