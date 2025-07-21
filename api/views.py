from django.shortcuts import render
from django.db.models import Q
# API IMPORTS
from rest_framework.response import Response
from rest_framework import generics, permissions, status
from rest_framework.filters import SearchFilter, OrderingFilter, DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
# MODEL IMPORTS
from reports.models import MonthlyReport
# SERIALIZER IMPORTS
from .serializers import MonthlyReportSerializer
# CACHING
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class MonthlyReportPagination(PageNumberPagination):
    """
    Custom pagination class for Monthly
    """
    page_size = 10  # Customize page size
    page_size_query_param = 'page_size'
    max_page_size = 100


class MonthlyReportCreateView(generics.CreateAPIView):
    """
    This class handles the creation of MonthlyReport instances.
    """
    serializer_class = MonthlyReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Auto-assign user"""
        serializer.save(user=self.request.user)
        # Consider adding audit logging here


@method_decorator(cache_page(60 * 15), name='dispatch')
class MonthlyReportListView(generics.ListAPIView):
    """
    This class handles the listing of MonthlyReport instances.
    """
    serializer_class = MonthlyReportSerializer
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]  # Added
    search_fields = ['user__username', 'month', 'status']
    ordering_fields = ['created_at', 'updated_at', 'month']
    filterset_fields = ['status', 'user']  # New filtering capability
    pagination_class = MonthlyReportPagination

    def get_queryset(self):
        """
        Returns:
        - All reports for admin users
        - Own reports + team reports for managers
        - Only own reports for regular users
        """
        user = self.request.user
        queryset = MonthlyReport.objects.select_related('user')
        if user.is_superuser:
            return queryset
        elif user.groups.filter(name='Managers').exists():
            return queryset.filter(
                Q(user=user) | Q(user__teams__in=user.managed_teams.all())
            )
        return queryset.filter(user=user)


class MonthlyReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    This class handles the retrieval, update, and deletion of a MonthlyReport instance.
    """
    serializer_class = MonthlyReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'pk'  # Explicit is better than implicit

    def get_queryset(self):
        """The same filtering logic as list view"""
        return MonthlyReportListView.get_queryset(self)

    def perform_update(self, serializer):
        """Change tracking"""
        instance = serializer.save()
        # Add your change logging logic here
        # Example: create_audit_log(instance, self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Soft delete implementation"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
