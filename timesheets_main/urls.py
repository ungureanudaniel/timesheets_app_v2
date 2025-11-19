from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path("__debug__/", include("debug_toolbar.urls")),
]


urlpatterns += i18n_patterns(
    path('', include('general.urls')),
    path('timesheets/', include('timesheet.urls')),
    path('administration/', include('dashboard.urls')),
    path('reports/', include('reports.urls')),
    path('accounts/', include('users.urls')),
)

# ------------add custom media path for production mode-----------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Option B: For production with custom view
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)