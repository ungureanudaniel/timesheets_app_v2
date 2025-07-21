from django.urls import path, include
from django.conf import settings
from .views import MonthlyReportCreateView, MonthlyReportListView
from django.conf.urls.static import static
# from users.views import user_logout
from django.utils.translation import gettext_lazy as _


urlpatterns = [
    # -------Visitor urls------------------
    # path('report', report, name="report"),
    path('reports/', MonthlyReportListView.as_view(), name='report-list'),
    path('reports/create/', MonthlyReportCreateView.as_view(), name='report-create'),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
