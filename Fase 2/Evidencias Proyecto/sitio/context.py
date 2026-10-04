from django.conf import settings

def sitio(request):
    return {"SITIO": settings.SITIO}
