from django.urls import path
from django.conf import settings
from .views import ExportPDFView, ReportGeneratorView, ReportResultsView, get_next_registration_number
from django.conf.urls.static import static
from django.utils.translation import gettext_lazy as _


urlpatterns = [
    path('generate/', ReportGeneratorView.as_view(), name='generate_report'),
    path('results/', ReportResultsView.as_view(), name='report_results'),
    path('export-pdf/', ExportPDFView.as_view(), name='export_pdf'),
    path('get-next-reg-number/', get_next_registration_number, name='get_next_reg_number'),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
