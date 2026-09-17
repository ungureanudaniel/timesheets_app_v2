# timesheets/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
import openpyxl
from timesheet.models import Activity  # Adjust to your actual model
from django.core.management.base import BaseCommand
from users.models import CustomUser
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from timesheet.models import Timesheet

import calendar
from datetime import date


def upload_activities(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active

            for row in sheet.iter_rows(min_row=4, values_only=True):  # skip header
                group, subgroup, code, description = row
                if code and description:
                    Activity.objects.get_or_create(code=code, defaults={'name': description, 'group': group, 'subgroup': subgroup})

            messages.success(request, "Activities uploaded successfully.")
        except Exception as e:
            messages.error(request, f"Error processing file: {e}")
        return redirect('upload_activities')
    return render(request, 'pal.html')  # Replace with your actual template


class Command(BaseCommand):
    help = 'Sends weekly, monthly, and office overview reports'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        
        # 1. EVERY MONDAY: Office Overview (Who filled what last week)
        if today.weekday() == 0:  # 0 is Monday
            self.send_office_overview(today)
            self.send_weekly_reminders(today)

        # 2. END OF MONTH: Monthly Reminders
        # Check if tomorrow is the 1st of a new month
        if (today + timedelta(days=1)).day == 1:
            self.send_monthly_reminders(today)

    def send_office_summary(self):
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count
        
        # Calculate last week's range
        today = timezone.now().date()
        start_date = today - timedelta(days=7)
        
        # Query: Count distinct dates per user
        summary = Timesheet.objects.filter(
            date__range=[start_date, today - timedelta(days=1)]
        ).values('user__first_name', 'user__last_name', 'user__username').annotate(
            days_count=Count('date', distinct=True)
        ).order_by('-days_count')

        # Build Email Content
        html_content = "<h3>Weekly Submission Summary</h3><table border='1'>"
        html_content += "<tr><th>Employee</th><th>Days Logged (Target: 5)</th></tr>"
        
        for entry in summary:
            name = f"{entry['user__first_name']} {entry['user__last_name']}" or entry['user__username']
            color = "green" if entry['days_count'] >= 5 else "red"
            html_content += f"<tr><td>{name}</td><td style='color:{color}'>{entry['days_count']}</td></tr>"
        
        html_content += "</table>"

        # Send the email to the office
        send_mail(
            subject="Weekly Timesheet Audit",
            message="Please view in an HTML compatible mail client.",
            from_email="noreply@yourserver.com",
            recipient_list=["office@yourcompany.com"],
            html_message=html_content
        )

    def send_weekly_reminders(self, today):
        # Logic to email reporters who haven't filled out their timesheet for the past week
        pass

    def send_monthly_reminders(self, today):
        # Logic to email reporters that the month is ending
        pass

def format_minutes(minutes):
    """
    Convert minutes to readable format.
    ex. 510 -> 8:30
    """
    if not minutes:
        return "0"
    
    minutes = int(minutes)
    hours = minutes // 60
    mins = minutes % 60
    
    return f"{hours}:{mins:02d}"

def generate_statutory_pdf_context(year, month, employee_data_list, ro_holidays):
    """
    Transforms operational timesheet data (employee_data_list) into standard statutory 8h/day pontaj format.
    """
    num_days = calendar.monthrange(year, month)[1]
    
    # 1. Calculate standard legal norm (8 hours per working day)
    working_days_count = 0
    for d in range(1, num_days + 1):
        curr_date = date(year, month, d)
        is_weekend = curr_date.weekday() in (5, 6)
        is_holiday = curr_date in ro_holidays
        if not is_weekend and not is_holiday:
            working_days_count += 1

    statutory_month_norm = working_days_count * 8  # e.g., 21 days * 8 = 168h

    # 2. Transform employee matrix for legal PDF display
    statutory_employee_data = []
    for item in employee_data_list:
        legal_days_matrix = {}
        legal_total_hours = 0
        
        # Parse existing matrix
        for day_num, day_info in item['days_matrix'].items():
            entry_type = day_info.get('type')
            raw_minutes = day_info.get('hours', 0)
            weekday = date(year, month, int(day_num)).weekday()  # 0=Monday, 6=Sunday
            if entry_type in ['CO', 'CM', 'EF']:
                # Statutory leave preserves code
                legal_days_matrix[day_num] = day_info
                legal_total_hours += int(8)
            elif entry_type == 'work' and ((weekday in range(4) and raw_minutes == 510) or (weekday == 4 and raw_minutes == 360)):
                # Force standard 8h rendering for legal pontaj
                legal_days_matrix[day_num] = {'type': 'work', 'hours': 8}
                legal_total_hours += int(8)
            elif raw_minutes > 0:
                # For any other work hours, round to nearest 8h if > 0
                legal_days_matrix[day_num] = {'type': 'work', 'hours': raw_minutes/60}
                legal_total_hours += int(raw_minutes/60)
            else:
                legal_days_matrix[day_num] = day_info

        statutory_employee_data.append({
            'employee_name': item['employee_name'],
            'statutory_norm': statutory_month_norm,
            'statutory_total_hours': legal_total_hours,
            'days_matrix': legal_days_matrix,
            'total_co_days': item['total_co_days'],
            'total_cm_days': item['total_cm_days'],
            'total_ef_days': item['total_ef_days'],
            'meal_tickets_count': item['meal_tickets_count'],
        })

    return statutory_month_norm, statutory_employee_data