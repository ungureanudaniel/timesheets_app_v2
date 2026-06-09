import calendar

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.utils import timezone

from timesheets_main import settings
from .forms import PALActivitiesUploadForm, FundsSourceForm, PALActivityForm
from django.db.models import Count, Prefetch, Sum, F, ExpressionWrapper, fields, FloatField, Q
from django.contrib.auth import get_user_model
from dashboard.forms import ActivityProgramForm
from dashboard.models import ActivityProgram
from timesheet.models import Activity, FundsSource
from users.models import CustomUser
from timesheet.models import Timesheet
from django.views import generic
from django.views.generic import CreateView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from natsort import natsorted
import openpyxl
from django.views.generic import TemplateView
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import date, datetime, timedelta
from django.core.mail import send_mail
from django.db.models import Count
from timesheet.models import Timesheet
import holidays

def automated_task_runner(request):
    # Security check: Only let the pinger in
    secret_key = settings.TASK_RUNNER_KEY
    if request.GET.get('key') != secret_key:
        return HttpResponseForbidden("Invalid Key")

    task = request.GET.get('task')
    today = timezone.now().date()

    if task == "monday_summary":
        # 1. Send Office Summary + 2. Weekly Reminder to Reporters
        send_office_weekly_summary(today)
        return HttpResponse("Monday tasks completed")

    elif task == "friday_reminder":
        # 3. Friday Afternoon Reminder
        send_reporter_reminders("Friday Reminder: Please finish your reports before the weekend!")
        return HttpResponse("Friday reminders sent")

    elif task == "monthly_report":
        # 4. 1st of the Month Reminder
        send_reporter_reminders("Monthly Reminder: It is the 1st of the month. Please finalize last month's report.")
        return HttpResponse("Monthly reminders sent")

    return HttpResponse("No task specified")

# Helper functions to keep it clean
def send_office_weekly_summary(today):
    last_week = today - timedelta(days=7)
    summary = Timesheet.objects.filter(date__range=[last_week, today - timedelta(days=1)])\
        .values('user__username').annotate(days=Count('date', distinct=True))
    
    body = "Weekly Audit:\n" + "\n".join([f"{s['user__username']}: {s['days']} days" for s in summary])
    send_mail("Weekly Summary", body, "system@company.com", ["office@company.com"])

def send_reporter_reminders(msg):
    from django.contrib.auth.models import User
    emails = User.objects.filter(is_staff=False).values_list('email', flat=True)
    send_mail("Report Reminder", msg, "system@company.com", list(emails))

def sanitize_romanian(text):
    if not text:
        return ""
    replacements = {
        'ă': 'a', 'Ă': 'A',
        'ș': 's', 'Ș': 'S',
        'ț': 't', 'Ț': 'T',
        'â': 'a', 'Â': 'A',
        'î': 'i', 'Î': 'I'
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    return text

# main admin dashboard view.
def dashboard(request):
    template = "dashboard/dashboard.html"

    context = {}
    return render(request, template, context)

# ==============Data analytics============
class AnalyticsView(generic.ListView):
    template_name = "dashboard/analytics.html"

    queryset = CustomUser.objects.all()
    paginate_by = 20

    def get(self, request, **kwargs):
        # get each individual userprofile safely
        user_profile = getattr(self.request.user, 'customuser', None)
        # If no customuser attribute (AnonymousUser or profile not created), user_profile will be None
        print(user_profile)
        return super().get(request, **kwargs)
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

class PALActivitiesListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Activity
    template_name = 'dashboard/pal.html'
    context_object_name = 'activities'
    paginate_by = 10

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        qs = Activity.objects.all()
        return natsorted(qs, key=lambda x: x.code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        queryset = self.get_queryset()
        
        paginator = Paginator(queryset, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['activities'] = page_obj
        context['object_list'] = page_obj
        context['page_obj'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        
        return context


User = get_user_model()

class HoursSummaryTableView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/hours_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        
        # Parse selected period or default to current month
        period_query = request.GET.get('selected_period')
        if not period_query:
            current_date = datetime.now()
            period_query = current_date.strftime('%Y-%m')

        # Split into numerical items
        year, month = map(int, period_query.split('-'))

        # Instantiate Romanian Public Holidays rules engine for this target year
        ro_holidays = holidays.Romania(years=year)

        # Month names for display
        ro_months = {
            1: "Ianuarie", 2: "Februarie", 3: "Martie", 4: "Aprilie",
            5: "Mai", 6: "Iunie", 7: "Iulie", 8: "August",
            9: "Septembrie", 10: "Octombrie", 11: "Noiembrie", 12: "Decembrie"
        }
        ro_days_short = ["L", "M", "M", "J", "V", "S", "D"]

        # Compute structural day lists for selected calendar space
        num_days = calendar.monthrange(year, month)[1]
        month_days_list = []
        
        # Track valid baseline legal working days for the contract type norm math
        actual_working_days_count = 0
        
        for d in range(1, num_days + 1):
            current_date = date(year, month, d)
            weekday_index = calendar.weekday(year, month, d)
            
            is_weekend = weekday_index in [5, 6]
            is_holiday = current_date in ro_holidays
            holiday_name = ro_holidays.get(current_date, "") if is_holiday else ""

            if not is_weekend and not is_holiday:
                actual_working_days_count += 1

            month_days_list.append({
                'day_num': d,
                'day_letter': ro_days_short[weekday_index],
                'is_weekend': is_weekend,
                'is_holiday': is_holiday,
                'holiday_name': holiday_name
            })

        context['current_period'] = period_query
        context['current_month_year'] = f"{ro_months[month]} {year}"
        context['month_days'] = month_days_list

        if request.user.is_staff or request.user.groups.filter(name='Managers').exists():
            employees = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        else:
            employees = User.objects.filter(id=request.user.id)

        monthly_timesheets = Timesheet.objects.filter(
            date__year=year, 
            date__month=month
        ).select_related('activity')

        employees = employees.prefetch_related(
            Prefetch('timesheet_set', queryset=monthly_timesheets, to_attr='cached_month_timesheets')
        )

        employee_data = []
        
        for emp in employees:
            # Initialize every single day with a default structure
            days_matrix = {d: {'type': 'none', 'hours': ''} for d in range(1, num_days + 1)}
            
            total_hours_worked = 0.0
            total_co_days = 0
            total_cm_days = 0
            worked_days_set = set() 
            co_days_set = set()
            cm_days_set = set()
            # Loop through pre-fetched records smoothly
            cached_sheets = getattr(emp, 'cached_month_timesheets', [])
            for ts in cached_sheets:
                day_number = ts.date.day
                
                activity_code = ts.activity.code.upper() if (ts.activity and ts.activity.code) else ""
                activity_name = ts.activity.name.upper() if (ts.activity and ts.activity.name) else ""
                
                is_co = (
                    "CO" == activity_code or 
                    "ODIHNA" in activity_name or 
                    "ODIHNĂ" in activity_name or
                    "CONCEDIU DE ODIHNĂ" in activity_name or
                    "CONCEDIU ANUAL" in activity_name
                )
                
                is_cm = (
                    "CM" == activity_code or 
                    "MEDICAL" in activity_name or
                    "CONCEDIU MEDICAL" in activity_name or
                    "BOALA" in activity_name
                )

                if is_co:
                    days_matrix[day_number] = {'type': 'CO', 'hours': 'CO'}
                    co_days_set.add(day_number)
                elif is_cm:
                    days_matrix[day_number] = {'type': 'CM', 'hours': 'CM'}
                    cm_days_set.add(day_number)
                else:
                    if hasattr(ts, 'duration_decimal') and ts.duration_decimal is not None:
                        hours = float(ts.duration_decimal)
                    elif ts.start_time and ts.end_time:
                        today_dummy = datetime.today()
                        dt1 = datetime.combine(today_dummy, ts.start_time)
                        dt2 = datetime.combine(today_dummy, ts.end_time)
                        hours = max(0.0, (dt2 - dt1).total_seconds() / 3600.0)
                    else:
                        hours = 8.0
                    
                    current_entry = days_matrix[day_number]
                    if current_entry['type'] == 'work':
                        existing_hours = float(current_entry['hours']) # add the new hours to the existing ones for that day
                        new_total = existing_hours + hours
                        days_matrix[day_number]['hours'] = round(new_total, 1)
                    else:
                        days_matrix[day_number] = {'type': 'work', 'hours': round(hours, 1)}

                    total_hours_worked += hours
                    # Track this day as a worked day for meal ticket eligibility
                    worked_days_set.add(day_number)
            
            eligible_meal_ticket_days = worked_days_set - co_days_set - cm_days_set
            # Standard Romanian Norm setup subtracting statutory bank holidays 
            norma_hours = actual_working_days_count * 8

            employee_data.append({
                'employee': emp,
                'norma_hours': norma_hours,
                'days_matrix': days_matrix,  
                'total_hours_worked': round(total_hours_worked, 1),
                'total_co_days': len(co_days_set),
                'total_cm_days': len(cm_days_set),
                'meal_tickets_count': len(eligible_meal_ticket_days)
            })

        context['employee_data'] = employee_data
        return context

class PALActivitiesUploadView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Upload new Activity
    """
    model = Activity
    form_class = PALActivitiesUploadForm
    template_name = 'dashboard/palactivities_upload.html'
    success_url = reverse_lazy('pal')
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all activities ordered by code
        activities_list = Activity.objects.all().order_by('code')
        
        # Setup pagination
        paginator = Paginator(activities_list, self.paginate_by)
        page = self.request.GET.get('page')
        activities = paginator.get_page(page)
        
        context['activities'] = activities
        return context

    def get(self, request, *args, **kwargs):
        form = PALActivitiesUploadForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = PALActivitiesUploadForm(request.POST, request.FILES)
        if form.is_valid():
            if 'file' not in request.FILES:
                messages.error(request, "No file uploaded.")
                return redirect(self.success_url)

            excel_file = request.FILES['file']
            try:
                wb = openpyxl.load_workbook(excel_file, data_only=True)
                sheet = wb.active if wb.active is not None else wb[wb.sheetnames[0]]

                # Normalize headers
                headers = [str(cell.value).strip().lower() if cell.value is not None else '' for cell in sheet[1]]

                if 'code' not in headers or 'name' not in headers:
                    messages.error(request, "Excel file must contain 'code' and 'name' columns.")
                    return redirect(self.success_url)

                code_index = headers.index('code')
                name_index = headers.index('name')

                # transaction
                from django.db import transaction
                with transaction.atomic():
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        if not row or all(cell is None for cell in row):
                            continue

                        code_val = row[code_index]
                        name_val = sanitize_romanian(row[name_index])

                        if code_val:
                            # This handles both Creating and Updating
                            Activity.objects.update_or_create(
                                code=code_val,
                                defaults={'name': name_val}
                            )
                
                messages.success(request, "Activities uploaded and synced successfully.")
            except Exception as e:
                messages.error(request, f"Error processing Excel file: {e}")
            return redirect(self.success_url)
        else:
            messages.error(request, "Invalid form submission.")
            return render(request, self.template_name, {'form': form})


class PALActivityCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Create view for Activity
    """
    model = Activity
    template_name = 'dashboard/pal_activity_create.html'
    success_url = reverse_lazy('pal')
    form_class = PALActivityForm

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class PALActivityUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    """
    Update view for Activity
    """
    model = Activity
    template_name = 'dashboard/pal_activity_edit.html'
    success_url = reverse_lazy('pal')
    form_class = PALActivityForm

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class PALActivityDeleteView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    """
    Delete view for Activity
    """
    model = Activity
    template_name = 'dashboard/pal_activity_delete.html'
    success_url = reverse_lazy('pal')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activity'] = self.get_object()
        return context


# the activity program view
def activity_program(request):
    template = "activities/activity-program.html"

    context = {}
    return render(request, template, context)


def get_total_hours_qs(queryset):
    """
    Helper to calculate total hours from start_time and end_time at DB level.
    This assumes end_time and start_time are on the same day.
    """
    return queryset.annotate(
        duration=ExpressionWrapper(
            (F('end_time') - F('start_time')),
            output_field=FloatField()
        )
    ).aggregate(
        # Duration is returned in microseconds, 
        # so we divide by 3,600,000,000 to get hours.
        total=Sum(F('duration')) / 3600000000.0
    )['total'] or 0

def worked_hours_per_member(request):
    today = timezone.now()
    team_members = CustomUser.objects.filter(is_active=True)
    data = []

    for member in team_members:
        qs = Timesheet.objects.filter(
            user=member, 
            date__year=today.year, 
            date__month=today.month
        )
        total_hours = get_total_hours_qs(qs)

        data.append({
            'name': member.get_full_name() or member.username,
            'hours': round(float(total_hours), 1)
        })

    return JsonResponse(data, safe=False)

def yearly_statistics(request):
    current_year = timezone.now().year
    months_data = []
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for month in range(1, 13):
        month_qs = Timesheet.objects.filter(date__year=current_year, date__month=month)
        
        # Calculate totals
        total_worked = get_total_hours_qs(month_qs)
        
        # For counts, we can still use Count
        stats = month_qs.aggregate(
            holidays=Count('id', filter=Q(description__icontains="holiday")), # Adjust filter if needed
            sick_leaves=Count('id', filter=Q(description__icontains="sick")), # Adjust filter if needed
        )

        months_data.append({
            'month': month_names[month-1],
            'worked_hours': round(float(total_worked), 1),
            'holidays': stats['holidays'],
            'sick_leaves': stats['sick_leaves'],
            'weekend_hours': 0 
        })

    return JsonResponse(months_data, safe=False)


class ActivityProgramCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Create view for Activity Program
    """
    model = ActivityProgram
    form_class = ActivityProgramForm
    template_name = 'activities/activity_program_create.html'
    success_url = reverse_lazy('activity_program_list')  # or PDF generation page

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class ActivityProgramListView(LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    """
    List view for Activity Programs
    """
    model = ActivityProgram
    template_name = 'activities/activity_program_list.html'
    context_object_name = 'activity_programs'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        return ActivityProgram.objects.filter(user=self.request.user).order_by('-registration_date')


class ActivityProgramUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    """
    Update view for Activity Program
    """
    model = ActivityProgram
    form_class = ActivityProgramForm
    template_name = 'activities/activity_program_edit.html'
    success_url = reverse_lazy('activity_program_list')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class ActivityProgramDeleteView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    """
    Delete view for Activity Program
    """
    model = ActivityProgram
    template_name = 'activities/activity_program_delete.html'
    success_url = reverse_lazy('activity_program_list')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activity_program'] = self.get_object()
        return context

class FundsSourceListView(LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    """
    List view for Funds Source
    """
    model = FundsSource
    template_name = 'dashboard/funds_source.html'
    context_object_name = 'funds'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
class NewFundsSourceView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Create view for new Funds Source
    """
    model = FundsSource
    form_class = FundsSourceForm
    template_name = 'dashboard/new_funds_source.html'
    success_url = reverse_lazy('funds_source')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
