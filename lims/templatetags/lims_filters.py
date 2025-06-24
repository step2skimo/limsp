from django import template

register = template.Library()

@register.filter
def assigned_to(sample, parameter):
    assignment = sample.testassignment_set.filter(parameter=parameter).first()
    return assignment.analyst.get_full_name() if assignment and assignment.analyst else ''
