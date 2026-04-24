from collections import defaultdict
import json
from django import forms
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from datetime import timedelta, datetime
from django.utils import timezone
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views import generic
from .forms import TimesheetForm
from django.contrib.auth import get_user_model
from .models import Timesheet, TimesheetImage
from django.db.models import Q, Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from calendar import monthrange
from django.utils.dateparse import parse_date
import datetime

User = get_user_model()

def get_user_timesheets(user):
    """Helper function to get timesheets for the given user."""
    timesheets = Timesheet.objects.filter(user=user).select_related('activity')
    calendar_events = []

    for t in timesheets:
        # Get activity name safely
        activity_name = str(t.activity) if t.activity else "No Activity"
        
        # Calculate duration
        duration = 0
        try:
            if callable(getattr(t, 'worked_hours', None)):
                hours_result = t.worked_hours()
                duration = float(hours_result) if hours_result else 0
            elif hasattr(t, 'worked_hours') and t.worked_hours is not None:
                duration = float(t.worked_hours) if t.worked_hours else 0
        except (TypeError, ValueError):
            duration = 0
        
        hours_display = f"{duration:.1f}h"
        
        # Determine color class based on hours
        if duration >= 8:
            className = 'timesheet-event-bar high-hours'
        elif duration >= 4:
            className = 'timesheet-event-bar medium-hours'
        else:
            className = 'timesheet-event-bar low-hours'
        
        timesheet_event = {
            'id': f"timesheet_{t.id}",
            'title': f"{activity_name} ({hours_display})",
            'start': t.date.strftime("%Y-%m-%d"),
            'className': className,
            'extendedProps': {
                'activity': activity_name,
                'hours': duration,
                'description': str(t.description) if hasattr(t, 'description') and t.description else ""
            }
        }
        calendar_events.append(timesheet_event)

    return calendar_events


class TimesheetListView(LoginRequiredMixin, ListView):
    model = Timesheet
    template_name = "timesheet/timesheets_list.html"
    context_object_name = "timesheets"
    paginate_by = 25  # Increased for easier scrolling

    def get_queryset(self):
        user = self.request.user
        
        # 1. Base Permissions: Managers see all, Reporters see only theirs
        if user.is_staff or user.groups.filter(name='Managers').exists():
            queryset = Timesheet.objects.all()
        else:
            queryset = Timesheet.objects.filter(user=user)

        # 2. Filter by Reporter Name (Search)
        employee_id = self.request.GET.get('employee')
        if employee_id:
            queryset = queryset.filter(user_id=employee_id)

        reporter_query = self.request.GET.get('reporter_name')
        if reporter_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=reporter_query) |
                Q(user__last_name__icontains=reporter_query) |
                Q(user__username__icontains=reporter_query)
            )
        # 3. Date Filtering
        # Allows admin to look at a specific day or month
        date_query = self.request.GET.get('date_filter')
        if date_query:
            queryset = queryset.filter(date=date_query)

        return queryset.select_related('user', 'activity', 'fundssource')\
                       .prefetch_related('timesheet_images')\
                       .order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_reporters"] = User.objects.filter(is_active=True).order_by('first_name')
        context["selected_employee"] = self.request.GET.get("employee", '')
        # Keep the search term in the box after the page refreshes
        context["selected_date"] = self.request.GET.get('date_filter', '')
        return context


# this function uses the helper function to retrieve timesheet data and communicates with Ajax module in main.js
# class GetTimesheetsView(LoginRequiredMixin, generic.View):
#     def get(self, request):
#         user = request.user
#         month = request.GET.get('month')
#         year = request.GET.get('year')

#         # Filter by month and year if provided
#         if month and year:
#             start_date = datetime.date(int(year), int(month), 1)
#             end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
#             timesheets = Timesheet.objects.filter(
#                 user=user,
#                 date__range=[start_date, end_date]
#             ).select_related('activity', 'fundssource')
#         else:
#             # Default to current month
#             today = timezone.now().date()
#             start_date = today.replace(day=1)
#             end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
#             timesheets = Timesheet.objects.filter(
#                 user=user,
#                 date__range=[start_date, end_date]
#             ).select_related('activity', 'fundssource')

#         # Serialize timesheet data
#         serialized_timesheets = []
#         for timesheet in timesheets:
#             serialized_timesheets.append({
#                 'id': timesheet.id,
#                 'date': timesheet.date.isoformat(),
#                 'activity': {
#                     'name': timesheet.activity.name,
#                 },
#                 'start_time': timesheet.start_time.isoformat() if timesheet.start_time else None,
#                 'end_time': timesheet.end_time.isoformat() if timesheet.end_time else None,
#                 'worked_hours': timesheet.worked_hours(),
#                 'description': timesheet.description,
#                 'fundssource': {
#                     'name': timesheet.fundssource.name if timesheet.fundssource else None,
#                 }
#             })
        
#         return JsonResponse(serialized_timesheets, safe=False)


# new timesheet
class CreateTimesheetView(generic.CreateView):
    template_name = "timesheet/create_timesheets.html"
    form_class = TimesheetForm

    def get_form_kwargs(self):
        """Pass the current user to the form for permission checks."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        """Handle the 'clicked_date' from the calendar or previous page."""
        initial = super().get_initial()
        clicked_date = self.request.GET.get('date')
        if clicked_date:
            initial['date'] = clicked_date
        return initial

    def form_valid(self, form):
        user = self.request.user
        is_manager = user.is_staff or user.groups.filter(name='Managers').exists()
        
        # Create the instance but don't save to DB yet
        self.object = form.save(commit=False)

        # If manager selected a user in the dropdown, use that.
        # Otherwise (for regular users), force it to be the logged-in user.
        selected_user = form.cleaned_data.get('user')
        if is_manager and selected_user:
            self.object.user = selected_user
        else:
            self.object.user = user

        # Save the object
        self.object.save()

        # Handle multiple image uploads
        files = self.request.FILES.getlist('images')
        for f in files:
            TimesheetImage.objects.create(timesheet=self.object, image=f)

        messages.success(self.request, _('Timesheet created successfully!'))
        return redirect('timesheet_list')

    def form_invalid(self, form):
        messages.error(self.request, _('Please correct the errors below.'))
        print("Form errors:", form.errors)  # Still helpful for debugging
        return super().form_invalid(form)


class UpdateTimesheetView(LoginRequiredMixin, generic.UpdateView):
    model = Timesheet
    form_class = TimesheetForm
    template_name = 'timesheet/update_timesheets.html'
    success_url = reverse_lazy('timesheet_list')
    
    def get_queryset(self):
        return Timesheet.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)

        # Handle new image uploads
        images = self.request.FILES.getlist('images')
        for image in images:
            TimesheetImage.objects.create(timesheet=self.object, image=image)

        messages.success(self.request, 'Timesheet updated successfully!')
        return response


class DeleteTimesheetView(LoginRequiredMixin, generic.DeleteView):
    model = Timesheet
    template_name = 'timesheet/delete_confirm.html' 
    success_url = reverse_lazy('timesheet_list')

    def get_queryset(self):
        # Security: Only allow users to delete their own entries
        return Timesheet.objects.filter(user=self.request.user)