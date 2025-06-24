from django import template
from lims.models import TestAssignment

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)


@register.filter
def assigned_count(samples, parameter):
    assigned_ids = TestAssignment.objects.filter(
        sample__in=samples,
        parameter=parameter
    ).values_list('sample_id', flat=True).distinct()
    
    return samples.filter(id__in=assigned_ids).count()



@register.filter
def assigned_to(sample, parameter):
    try:
        assignment = TestAssignment.objects.get(sample=sample, parameter=parameter)
        if assignment.analyst:
            return assignment.analyst.get_full_name()
        else:
            return None
    except TestAssignment.DoesNotExist:
        return None


