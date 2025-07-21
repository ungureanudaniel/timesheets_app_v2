from django.urls import path, include
from django.conf import settings
from .views import ReportGeneratorView, ReportResultsView
from django.conf.urls.static import static
# from users.views import user_logout
from django.utils.translation import gettext_lazy as _


urlpatterns = [
    # -------Visitor urls------------------
    path('generate/', ReportGeneratorView.as_view(), name='generate_report'),
    path('results/', ReportResultsView.as_view(), name='report_results'),

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
