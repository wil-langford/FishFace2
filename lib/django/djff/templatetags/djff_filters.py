import re

from django import template as djtemplate
from django.template.defaultfilters import stringfilter
import django.utils.safestring as dus

register = djtemplate.Library()

@register.filter(is_safe=True)
@stringfilter
def mark_safe(value):
    return dus.mark_safe(value)


@register.filter(is_safe=True)
@stringfilter
def replace_width(value, replacement):
    return re.sub(
        r'width="?\d+%?"?',
        r'width="{}"'.format(str(replacement)),
        value
    )