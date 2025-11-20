from django.urls import path, include
from django.conf import settings
from .views import ActivityProgramCreateView, ActivityProgramListView, ActivityProgramUpdateView, ActivityProgramDeleteView, PALActivityCreateView, dashboard, AnalyticsView, \
    worked_hours_per_member, yearly_statistics, activity_program, PALActivitiesListView, PALActivityUpdateView, PALActivityDeleteView, PALActivitiesUploadView, \
    FundsSourceListView, NewFundsSourceView
from .utils import upload_activities
from django.conf.urls.static import static
from django.utils.translation import gettext_lazy as _


urlpatterns = [
    # -------Visitor urls------------------
    path('dashboard/', dashboard, name="dashboard"),
    path('analytics/', AnalyticsView.as_view(), name="analytics"),
    path('plan-de-lucru-anual/', PALActivitiesListView.as_view(), name="pal"),
    path('pal_activity/create/', PALActivityCreateView.as_view(), name='pal_activity_create'),
    path('pal_activity/upload/', PALActivitiesUploadView.as_view(), name='pal_activity_upload'),
    path('pal_activity/<int:pk>/edit/', PALActivityUpdateView.as_view(), name='pal_activity_edit'),
    path('pal_activity/<int:pk>/delete/', PALActivityDeleteView.as_view(), name='pal_activity_delete'),
    path('upload_pal_activities/', upload_activities, name="upload_activities"),
    path('analytics/worked_hours_per_member', worked_hours_per_member, name="worked_hours_per_member"),
    path('analytics/yearly_statistics', yearly_statistics, name="yearly_statistics"),
    path('activity-program/create/', ActivityProgramCreateView.as_view(), name='activity_program_create'),
    path('activity-program/list/', ActivityProgramListView.as_view(), name='activity_program_list'),
    path('activity-program/<int:pk>/edit/', ActivityProgramUpdateView.as_view(), name='activity_program_edit'),
    path('activity-program/<int:pk>/delete/', ActivityProgramDeleteView.as_view(), name='activity_program_delete'),
    path('funds_source/', FundsSourceListView.as_view(), name='funds_source'),
    path('new_funds_source/', NewFundsSourceView.as_view(), name='new_funds_source'),

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
