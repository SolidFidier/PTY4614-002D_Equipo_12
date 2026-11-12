from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from sitio.idioma import L

register = template.Library()


@register.simple_tag
def t(es, en, pt=None, **datos):
    """Texto en el idioma activo:  {% t "Hola {n}" "Hello {n}" "Olá {n}" n=nombre %}  (los datos se escapan)."""
    texto = L(es, en, pt)
    if datos:
        texto = texto.format(**{k: conditional_escape(v) for k, v in datos.items()})
    return mark_safe(texto)
