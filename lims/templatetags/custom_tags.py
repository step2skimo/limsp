from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)



@register.filter
def calc_percentage(value, max_value):
    try:
        return round((value / max_value) * 100, 1) if max_value else 0
    except:
        return 0
