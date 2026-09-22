from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    # ------- urls------------------
    

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
