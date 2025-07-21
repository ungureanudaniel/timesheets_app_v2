from django.urls import path, include
from django.conf import settings
from .views import report
from django.conf.urls.static import static
# from users.views import user_logout
from django.utils.translation import gettext_lazy as _


urlpatterns = [
    # -------Visitor urls------------------
    # path('report', report, name="report"),

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
