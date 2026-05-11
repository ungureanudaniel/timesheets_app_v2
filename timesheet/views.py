from collections import defaultdict
import json
from django import forms
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from datetime import timedelta, datetime
from django.utils import timezone
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views import generic
from .forms import TimesheetForm
from users.models import CustomUser
# from django.contrib.auth import get_user_model
from .models import Timesheet, TimesheetImage
from django.db.models import Q, Count, Sum
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from calendar import monthrange
from django.utils.dateparse import parse_date
import datetime

User = CustomUser  # Assuming you have a custom user model defined in users.models

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

import calendar
from datetime import date, datetime, timedelta
from django.views.generic import TemplateView
from django.utils.safestring import mark_safe


class TimesheetCalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'timesheet/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get year and month from URL or use current
        today = date.today()
        year = int(self.request.GET.get('year', today.year))
        month = int(self.request.GET.get('month', today.month))
        
        # Generate calendar days
        cal = calendar.Calendar(firstweekday=0) # Monday start
        month_days = cal.monthdatescalendar(year, month)
        
        # Fetch all timesheets for this user in this month at once
        timesheets = Timesheet.objects.filter(
            user=user, 
            date__year=year, 
            date__month=month
        ).order_by('-date', '-start_time')
        
        # Build a dictionary of {date: total_hours}
        daily_totals = {}
        count_images = {}
        for ts in timesheets:
            daily_totals[ts.date] = daily_totals.get(ts.date, 0) + ts.duration_decimal
            count_images[ts.date] = count_images.get(ts.date, 0) + 1

        # Format calendar data with status colors
        calendar_data = []
        for week in month_days:
            week_data = []
            for day in week:
                if day.month != month:
                    status = "muted" # Day from prev/next month
                    total_decimal = 0
                    total_hm = ""
                else:
                    total_decimal = daily_totals.get(day, 0)
                    # conversion to hours and minutes
                    hours = int(total_decimal)
                    minutes = int(round((total_decimal - hours) * 60))
                    total_hm = f"{hours}h {minutes}m" if total_decimal > 0 else "0h"

                    # Determine status color based on hours
                    target = 6.0 if day.weekday() == 4 else 8.5
                    
                    if total_decimal >= target:
                        status = "success" # Green
                    elif total_decimal > 0:
                        status = "warning" # Yellow
                    else:
                        status = "danger"  # Red
                
                week_data.append({'day': day, 'status': status, 'total_decimal': total_decimal, 'total_hm': total_hm, 'images': count_images.get(day, 0)})
            calendar_data.append(week_data)

        context.update({
            'calendar_matrix': calendar_data,
            'current_month': date(year, month, 1),
            'timesheets': timesheets,
            'prev_month': date(year, month, 1) - timedelta(days=1),
            'next_month': date(year, month, 1) + timedelta(days=32),
        })
        return context


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
        for ts in context['timesheets']:
            day_entries = Timesheet.objects.filter(user=ts.user, date=ts.date)

            total_day_hours = sum(entry.duration_decimal for entry in day_entries)

            limit = 6.0 if ts.date.weekday() == 4 else 8.5
            
            if total_day_hours >= limit:
                ts.status_color = "success"  # Green
            elif total_day_hours > 0:
                ts.status_color = "warning"  # Yellow
            else:
                ts.status_color = "danger"   # Red
        return context

class TimesheetImageDetailView(LoginRequiredMixin, DetailView):
    model = Timesheet
    template_name = 'timesheet/timesheet_images.html'
    context_object_name = 'timesheet'

    def get_queryset(self):
        # Security: Users can only see their own images unless they are staff/managers
        user = self.request.user
        if user.is_staff or user.groups.filter(name='Managers').exists():
            return Timesheet.objects.all()
        return Timesheet.objects.filter(user=user)


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
        return redirect('timesheet_calendar')

    def form_invalid(self, form):
        # Default error message
        messages.error(self.request, _('Please correct the errors below.'))
        
        # Check if the "Daily Limit" error is present
        if '__all__' in form.errors:
            for error in form.errors['__all__']:
                if "Limit exceeded" in error or "Maximum allowed" in error:
                    messages.warning(self.request, error)

        print("Form errors:", form.errors)
        return super().form_invalid(form)


class UpdateTimesheetView(LoginRequiredMixin, generic.UpdateView):
    model = Timesheet
    form_class = TimesheetForm
    template_name = 'timesheet/update_timesheets.html'
    success_url = reverse_lazy('timesheet_calendar')
    
    def get_queryset(self):
        return Timesheet.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        self.object = form.save(commit=False)
        if not form.cleaned_data.get('user'):
            form.instance.user = self.get_object().user
        
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
    success_url = reverse_lazy('timesheet_calendar')

    def get_queryset(self):
        # Security: Only allow users to delete their own entries
        return Timesheet.objects.filter(user=self.request.user)