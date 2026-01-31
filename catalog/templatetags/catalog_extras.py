import json

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def jsonify(value):
    try:
        return mark_safe(escape(json.dumps(value)))
    except (TypeError, ValueError):
        return mark_safe('{}')
