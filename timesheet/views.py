import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views import generic
from django.utils import timezone
from datetime import datetime
from .forms import TimesheetForm
from .models import Timesheet, Activity
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from calendar import monthrange
# from django.utils import timezone
# from datetime import datetime, timedelta
# from calendar import HTMLCalendar


# =============helper function to fetch timesheet data======
def get_user_timesheets(user):
    """Helper function to get timesheets for the given user."""
    timesheets = Timesheet.objects.filter(user=user)  # Adjust if you have a foreign key to the user
    calendar_events = []

    for t in timesheets:
        timesheet_event = {
            'id': f"timesheet_{t.id}",
            'title': f"Timesheet: {t.activity}",
            'start': t.date.strftime("%Y-%m-%d"),  # Ensure date format is compatible with FullCalendar
            'type': 'event',
            'description': f"Worked {t.hours_worked} hours on {t.activity}. Description: {t.description}"
        }
        calendar_events.append(timesheet_event)

    return calendar_events


# serializer and renderer for the timesheet list view
class TimesheetCalendarView(LoginRequiredMixin, generic.View):
    def get(self, request):
        user = request.user
        calendar_events = get_user_timesheets(user)  # Use the helper function
        form = TimesheetForm()  # Create an empty form for the modal
        # Convert the event data to JSON format for the template
        context = {
            "calendar_events": json.dumps(calendar_events),  # Pass JSON directly to the template
            "form": form,  # Pass form to the template
        }

        return render(request, "timesheet/timesheets_list.html", context)


# this function uses the helper function to retrieve timesheet data and communicates with Ajax module in main.js
class GetTimesheetsView(LoginRequiredMixin, generic.View):
    def get(self, request):
        user = request.user
        calendar_events = get_user_timesheets(user)  # Use the helper function

        return JsonResponse(calendar_events, safe=False)  # Return JSON response
# def timesheet_list(request):
#     # get current year and month
#     current_month = timezone.now().month
#     # current_year = timezone.now().year
#     # Base queryset
#     timesheets = Timesheet.objects.all()
#     # Filter by search query
#     query = request.GET.get('q', '')
#     try:
#         if query:
#             timesheets = timesheets.filter(
#                 Q(activity__name__icontains=query) | Q(description__icontains=query))

#     except Exception as e:
#         print('Query error:',e)
#     # Filter by month
#     month = request.GET.get('month', '')
#     if month:
#         try:
#             month_date = datetime.strptime(month, "%Y-%m")
#             timesheets = timesheets.filter(date__year=month_date.year, date__month=month_date.month)
#         except ValueError:
#             print('month error:',e)
#             pass  # Invalid month format, ignore the filter

#     # Get distinct months for the filter dropdown
#     months = [(i, calendar.month_name[i]) for i in range(1, 13)]
#     # Get the month and year from GET parameters if available
#     try:
#         month = int(request.GET.get('month', current_month))
#         # year = int(request.GET.get('year', current_year))
#     except Exception as e:
#         print('Current month request error:',e)
#         messages.warning(request, e)

#     template = 'timesheet/timesheets_list.html'
#     # timesheets = Timesheet.objects.filter(date__year=year, date__month=month, user=request.user)\

#     context = {
#         'timesheets': timesheets,
#         'months': months
#     }
#     return render(request, template, context)


# new timesheet
@login_required
def create_timesheet(request):
    template = "modals/create_timesheets.html"

    if request.method == 'POST':
        form = TimesheetForm(request.POST)
        if form.is_valid():
            try:
                new_timesheet = form.save(commit=False)
                new_timesheet.user = request.user
                new_timesheet.save()
                messages.success(request, _('Timesheet created successfully!'))
                return redirect('timesheet_list')
            except Exception as e:
                messages.error(request, _('Error saving timesheet: ') + str(e))
        else:
            print("Form errors:", form.errors)  # Debugging
            messages.error(request, _('Please correct the errors below.'))
    else:
        form = TimesheetForm()

    context = {'form': form}
    return render(request, template, context)


# timesheet update view
class UpdateTimesheetView(LoginRequiredMixin, generic.View):
    """
    This class handles the update of a Timesheet instance.
    """
    def post(self, request):
        timesheet_id = request.POST.get('id')
        title = request.POST.get('title')
        start = request.POST.get('start')
        end = request.POST.get('end')

        try:
            # Fetch the timesheet by ID
            timesheet = Timesheet.objects.get(id=timesheet_id, user=request.user)  # Assuming there's a user foreign key
            timesheet.activity = title  # Update the activity
            timesheet.start_time = start  # Update the start time (if you have it)
            timesheet.end_time = end  # Update the end time (if you have it)
            timesheet.save()  # Save the changes

            return JsonResponse({'status': 'success', 'message': 'Timesheet updated successfully.'})
        except Timesheet.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Timesheet not found.'}, status=404)


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
