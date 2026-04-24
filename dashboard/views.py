from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.utils import timezone
from .forms import PALActivitiesUploadForm, FundsSourceForm, PALActivityForm
from django.db.models import Count, Sum, F, ExpressionWrapper, fields, FloatField, Q
from dashboard.forms import ActivityProgramForm
from dashboard.models import ActivityProgram
from timesheet.models import Activity, FundsSource
from users.models import CustomUser
from timesheet.models import Timesheet
from django.views import generic
from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from natsort import natsorted
import openpyxl

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
