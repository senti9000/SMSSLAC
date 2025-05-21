from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def has_grade_value(dictionary, key):
    return key in dictionary and dictionary[key] is not None

import builtins

@register.filter(name='getattr')
def getattr_filter(obj, attr_name):
    return builtins.getattr(obj, attr_name, None)

@register.filter
def split(value, delimiter=" "):

    Usage: {{ value|split:"delimiter" }}
    
    if not isinstance(value, str):
        return value
    return value.split(delimiter)
