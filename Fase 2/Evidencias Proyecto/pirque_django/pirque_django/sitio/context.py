from django.conf import settings

def sitio(request):
    # SITIO: datos del hospedaje. huesped: cliente identificado en la sesión (botón «Ingresar» / menú con su nombre).
    return {"SITIO": settings.SITIO, "huesped": request.session.get("huesped")}
