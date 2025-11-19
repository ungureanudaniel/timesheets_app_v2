import json
from django import forms
from django.views.generic import ListView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from datetime import timedelta, datetime
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views import generic
from .forms import TimesheetForm
from .models import Timesheet, TimesheetImage
from django.db.models import Q, Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from calendar import monthrange
from django.utils.dateparse import parse_date
import datetime

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


class TimesheetListView(LoginRequiredMixin, generic.View):
    def get(self, request):
        # Get all timesheets for the user, ordered by date (newest first)
        timesheets_list = Timesheet.objects.filter(user=request.user).select_related('activity', 'fundssource').order_by('-date', '-created_at')
        
        # Simple pagination - 20 items per page
        paginator = Paginator(timesheets_list, 20)
        page = request.GET.get('page')
        
        try:
            timesheets = paginator.page(page)
        except PageNotAnInteger:
            timesheets = paginator.page(1)
        except EmptyPage:
            timesheets = paginator.page(paginator.num_pages)
        
        context = {
            "timesheets": timesheets,
            "form": TimesheetForm(),  # Form for the modal
        }
        
        return render(request, "timesheet/timesheets_list.html", context)


# this function uses the helper function to retrieve timesheet data and communicates with Ajax module in main.js
class GetTimesheetsView(LoginRequiredMixin, generic.View):
    def get(self, request):
        user = request.user
        calendar_events = get_user_timesheets(user)  # Use the helper function

        return JsonResponse(calendar_events, safe=False)  # Return JSON response


# new timesheet
class CreateTimesheetView(generic.CreateView):
    template_name = "modals/create_timesheets.html"
    form_class = TimesheetForm

    def get(self, request):
        clicked_date = request.GET.get('date')
        form = TimesheetForm(initial={'date': clicked_date})

        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = TimesheetForm(request.POST)
        if form.is_valid():
            try:
                new_timesheet = form.save(commit=False)
                new_timesheet.user = request.user
                # Fetch date from hidden input
                clicked_date = request.POST.get('date')
                if clicked_date:
                    parsed_date = parse_date(clicked_date)
                    print(parsed_date)
                    if parsed_date is None:
                        raise ValidationError(f"Invalid date: {clicked_date}")
                    new_timesheet.date = parsed_date
                
                new_timesheet.save()

                # Save uploaded images
                files = request.FILES.getlist('images')
                for f in files:
                    TimesheetImage.objects.create(timesheet=new_timesheet, image=f)

                messages.success(request, _('Timesheet created successfully!'))
                return redirect('timesheet_list')
            except Exception as e:
                messages.error(request, _('Error saving timesheet: ') + str(e))
        else:
            # Pass form errors to the template
            messages.error(request, _('Please correct the errors below.'))
            print("Form errors:", form.errors)  # Debugging

        return render(request, self.template_name, {'form': form})


# timesheet update view
class UpdateTimesheetView(LoginRequiredMixin, generic.View):
    def post(self, request):
        timesheet_id = request.POST.get('timesheet_id')
        date = request.POST.get('date')
        activity_id = request.POST.get('activity')
        fundssource_id = request.POST.get('fundssource')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        description = request.POST.get('description')

        # Validate required fields
        if not all([date, activity_id, fundssource_id, start_time, end_time, description]):
            return JsonResponse({
                'status': 'error', 
                'message': 'All fields are required.'
            }, status=400)

        try:
            timesheet = Timesheet.objects.get(id=timesheet_id, user=request.user)
            
            # Update all fields according to model
            timesheet.date = date
            timesheet.activity = activity_id
            timesheet.fundssource = fundssource_id
            timesheet.start_time = start_time
            timesheet.end_time = end_time
            timesheet.description = description
            
            timesheet.save()

            return JsonResponse({
                'status': 'success', 
                'message': 'Timesheet updated successfully.'
            })
            
        except Timesheet.DoesNotExist:
            return JsonResponse({
                'status': 'error', 
                'message': 'Timesheet not found.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Error updating timesheet: {str(e)}'
            }, status=400)
class DeleteTimesheetView(LoginRequiredMixin, generic.View):
    """
    This class handles the deletion of a Timesheet instance.
    """
    def post(self, request):
        timesheet_id = request.POST.get('id')

        try:
            # Fetch the timesheet by ID
            timesheet = Timesheet.objects.get(id=timesheet_id, user=request.user)  # Assuming there's a user foreign key
            timesheet.delete()  # Delete the timesheet

            return JsonResponse({'status': 'success', 'message': 'Timesheet deleted successfully.'})
        except Timesheet.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Timesheet not found.'}, status=404)
