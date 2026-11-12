from django.utils.functional import lazy
from django.utils.translation import get_language

def idioma():
    """Código del idioma activo del sitio: es, en o pt."""
    c = (get_language() or "es")[:2]
    return c if c in ("es", "en", "pt") else "es"

def es_ingles():
    return idioma() == "en"

def L(es, en, pt=None):
    """Devuelve el texto en el idioma activo (es/en/pt). Si falta el portugués, se usa el español."""
    c = idioma()
    return en if c == "en" else (pt if c == "pt" and pt else es)

L_lazy = lazy(L, str)  # para etiquetas de formularios definidas al importar
