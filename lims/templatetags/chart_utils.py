from django import template
register = template.Library()



@register.filter
def mapcolor(ownership_list, arg):
    color_map = dict(pair.split(":") for pair in arg.split(","))
    return [color_map.get(role, "#ccc") for role in ownership_list]

@register.filter
def times(count, value):
    return [value] * count

@register.filter
def to_list(value):
    return value  
