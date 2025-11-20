from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.utils import timezone
from .forms import PALActivitiesUploadForm, FundsSourceForm, PALActivityForm
from django.db.models import Sum
from dashboard.forms import ActivityProgramForm
from dashboard.models import ActivityProgram
from timesheet.models import Activity, FundsSource
from users.models import CustomUser
from timesheet.models import Timesheet
from django.views import generic
from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
import openpyxl


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
    """
    List all Activities with pagination
    """
    model = Activity
    template_name = 'dashboard/pal.html'
    context_object_name = 'activities'
    paginate_by = 10  # Show 10 activities per page
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        # Call the parent method to get the properly ordered queryset
        return super().get_queryset().order_by('code')

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
                # Read Excel file using openpyxl
                wb = openpyxl.load_workbook(excel_file, data_only=True)
                if not wb.sheetnames:
                    messages.error(request, "Excel file contains no sheets.")
                    return redirect(self.success_url)

                # Prefer active sheet but fall back to first sheet
                sheet = wb.active if wb.active is not None else wb[wb.sheetnames[0]]

                if sheet is None:
                    messages.error(request, "Could not read worksheet from the uploaded Excel file.")
                    return redirect(self.success_url)

                # get the headers from worksheet (normalize to lowercase strings)
                headers = [str(cell.value).strip().lower() if cell.value is not None else '' for cell in sheet[1]]

                # Check required columns
                if 'code' not in headers or 'name' not in headers:
                    messages.error(request, "Excel file must contain 'code' and 'name' columns.")
                    return redirect(self.success_url)

                # Get column indices
                code_index = headers.index('code')
                name_index = headers.index('name')

                # Iterate rows and save Activities
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if not row or all(cell is None for cell in row):
                        continue

                    code_val = row[code_index] if len(row) > code_index else None
                    name_val = row[name_index] if len(row) > name_index else None

                    if code_val is None:
                        # skip rows without a code
                        continue

                    if Activity.objects.filter(code=code_val).exists():
                        Activity.objects.filter(code=code_val).update(name=name_val)
                    else:
                        # Create new Activity if it doesn't exist
                        Activity.objects.create(code=code_val, name=name_val)
                messages.success(request, "Activities uploaded successfully.")
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


# the worked hours per member view
def worked_hours_per_member(request):
    current_month = timezone.now().month
    current_year = timezone.now().year

    team_members = CustomUser.objects.all()  # Adjust this to your team selection logic
    data = []

    for member in team_members:
        worked_hours = Timesheet.objects.filter(user=member.user, date__year=current_year, date__month=current_month).aggregate(total_hours=Sum('hours'))['total_hours'] or 0
        data.append({
            'name': member.user.get_full_name(),
            'hours': worked_hours
        })

    return JsonResponse(data, safe=False)

# the yearly statistics view
def yearly_statistics(request):
    current_year = timezone.now().year
    team_members = CustomUser.objects.all()  # Adjust this to your team selection logic

    months_data = []
    for month in range(1, 13):
        worked_hours = Timesheet.objects.filter(date__year=current_year, date__month=month).aggregate(total_hours=Sum('hours'))['total_hours'] or 0
        holidays = Timesheet.objects.filter(date__year=current_year, date__month=month, is_holiday=True).count()
        sick_leaves = Timesheet.objects.filter(date__year=current_year, date__month=month, is_sick_leave=True).count()
        weekend_hours = Timesheet.objects.filter(date__year=current_year, date__month=month, is_weekend=True).aggregate(total_hours=Sum('hours'))['total_hours'] or 0

        months_data.append({
            'month': month,
            'worked_hours': worked_hours,
            'holidays': holidays,
            'sick_leaves': sick_leaves,
            'weekend_hours': weekend_hours
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
