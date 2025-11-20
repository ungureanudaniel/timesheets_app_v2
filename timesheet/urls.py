from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import TimesheetListView, GetTimesheetsView, CreateTimesheetView, UpdateTimesheetView, DeleteTimesheetView
from django.utils.translation import gettext_lazy as _


urlpatterns = [
    path('', TimesheetListView.as_view(), name="timesheet_list"),
    path('get_timesheets/', GetTimesheetsView.as_view(), name='get_timesheets'),
    path('timesheet/create/', CreateTimesheetView.as_view(), name='create_timesheet'),
    path('timesheet/<int:id>/edit', UpdateTimesheetView.as_view(), name='update_timesheet'),
    path('timesheet/<int:id>/delete', DeleteTimesheetView.as_view(), name='delete_timesheet'),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
