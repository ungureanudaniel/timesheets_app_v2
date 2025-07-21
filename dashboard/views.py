from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from users.models import CustomUser
from timesheet.models import Timesheet


# main admin dashboard view.
def dashboard(request):
    template = "dashboard/dashboard.html"

    context = {}
    return render(request, template, context)


# the analytics view for the admin/manager.
def analytics(request):
    template = "dashboard/analytics.html"

    context = {}
    return render(request, template, context)


# the activities view for the admin/manager.
def pal_activities(request):
    template = "dashboard/pal.html"

    context = {}
    return render(request, template, context)


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
