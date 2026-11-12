from django.utils import translation

class PanelEnEspanol:
    """El panel de administración siempre se muestra en español, sin importar el idioma del sitio público."""
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        if request.path.startswith(("/panel/", "/admin/")): translation.activate("es")
        return self.get_response(request)
