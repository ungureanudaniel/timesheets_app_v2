from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# from users.views import user_logout
from django.utils.translation import gettext_lazy as _

from registries.views import DocumentCreateView, DocumentListView, DocumentUpdateView


urlpatterns = [
    path('document_registry/', DocumentListView.as_view(), name='registry_list'),
    path('document_registry/new/', DocumentCreateView.as_view(), name='registry_create'),
    path('document_registry/edit/<int:pk>/', DocumentUpdateView.as_view(), name='registry_update'),



]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
