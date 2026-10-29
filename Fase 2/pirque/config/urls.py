from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # RUTA OBLIGATORIA PARA EL CAMBIO DE IDIOMA (set_language)
    path("i18n/", include("django.conf.urls.i18n")),
    
    # Rutas de tu app
    path("", include("sitio.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)