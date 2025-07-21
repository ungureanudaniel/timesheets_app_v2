from django.urls import path, include
from django.conf import settings
from .views import dashboard, analytics, worked_hours_per_member, yearly_statistics, activity_program, pal_activities
from .utils import upload_activities
from django.conf.urls.static import static
from django.utils.translation import gettext_lazy as _


urlpatterns = [
    # -------Visitor urls------------------
    path('dashboard/', dashboard, name="dashboard"),
    path('analytics/', analytics, name="analytics"),
    path('plan-de-lucru-anual/', pal_activities, name="pal"),
    path('upload_pal_activities/', upload_activities, name="upload_activities"),
    path('activity-program/', activity_program, name="program"),
    path('analytics/worked_hours_per_member', worked_hours_per_member, name="worked_hours_per_member"),
    path('analytics/yearly_statistics', yearly_statistics, name="yearly_statistics"),



]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
