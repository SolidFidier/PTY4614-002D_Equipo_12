from .datos import datos_sitio

def sitio(request):
    # SITIO: datos del hospedaje (settings.SITIO + lo editado en Panel → Configuraciones avanzadas).
    # huesped: cliente identificado en la sesión (botón «Ingresar» / menú con su nombre).
    return {"SITIO": datos_sitio(), "huesped": request.session.get("huesped")}
