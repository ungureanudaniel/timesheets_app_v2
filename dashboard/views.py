import calendar
import re
import unicodedata
from datetime import date, datetime, timedelta
from io import BytesIO
from django.forms import formset_factory
from django.db import transaction
import holidays
import openpyxl
from natsort import natsorted
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count, Prefetch, Sum, F, ExpressionWrapper, FloatField, Q, Max
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, DeleteView
from django.template.loader import get_template
from django.conf import settings
from .forms import PALActivitiesUploadForm, FundsSourceForm, PALActivityForm, ActivityProgramUpdateForm
from .models import ActivityProgram, ActivityProgramSignature, ActivityProgramItem
from .utils import format_minutes, generate_statutory_pdf_context, get_week_choices
from timesheet.models import Activity, FundsSource, Timesheet
from users.models import CustomUser
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Romanian month names
ROMANIAN_MONTHS = {
    1: "Ianuarie",
    2: "Februarie",
    3: "Martie",
    4: "Aprilie",
    5: "Mai",
    6: "Iunie",
    7: "Iulie",
    8: "August",
    9: "Septembrie",
    10: "Octombrie",
    11: "Noiembrie",
    12: "Decembrie"
}

def get_romanian_month(month):
    """Get month name in Romanian"""
    return ROMANIAN_MONTHS.get(month, calendar.month_name[month])


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
class AnalyticsView(ListView):
    template_name = "dashboard/analytics.html"

    queryset = CustomUser.objects.all()
    paginate_by = 20

    def get(self, request, **kwargs):
        # get each individual userprofile safely
        user_profile = getattr(self.request.user, 'customuser', None)
        # If no customuser attribute (AnonymousUser or profile not created), user_profile will be None
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
        workable_mon_thu = 0
        workable_fri = 0
        
        for d in range(1, num_days + 1):
            current_date = date(year, month, d)
            weekday_index = calendar.weekday(year, month, d)
            
            is_weekend = weekday_index in [5, 6]
            is_holiday = current_date in ro_holidays
            holiday_name = ro_holidays.get(current_date, "") if is_holiday else ""

            if not is_weekend and not is_holiday:
                if weekday_index in [0, 1, 2, 3]:
                    workable_mon_thu += 1
                elif weekday_index == 4:
                    workable_fri += 1

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
            employees = User.objects.filter(is_approved=True).order_by('last_name', 'first_name')
        else:
            # Non-manager users may view only their own timesheet summary.
            # Keep this as a queryset because it is prefetched below.
            employees = User.objects.filter(
                is_approved=True,
                pk=request.user.pk,
            ).order_by('last_name', 'first_name')

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
            days_matrix = {d: {'type': 'none', 'hours': 0} for d in range(1, num_days + 1)}
            total_hours_worked = 0.0
            total_minutes_worked = 0
            total_co_days = 0
            total_cm_days = 0
            worked_days_set = set() 
            co_days_set = set()
            cm_days_set = set()
            ef_days_set = set()
            # Loop through pre-fetched records smoothly
            cached_sheets = getattr(emp, 'cached_month_timesheets', [])
            for ts in cached_sheets:
                day_number = ts.date.day
                is_bank_holiday = ts.date in ro_holidays
                is_weekend = ts.date.weekday() in [5, 6]
                weekday_idx = ts.date.weekday()

                if weekday_idx in [0, 1, 2, 3]:
                    leave_minutes = 8.5 * 60
                elif weekday_idx == 4:
                    leave_minutes = 6 * 60
                else:
                    leave_minutes = 0

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
                
                is_ef = (
                    "EF" == activity_code or 
                    "EVENIMENT FAMILIAL" in activity_name or
                    "FAMILIAL" in activity_name
                )
                if is_co:
                    days_matrix[day_number] = {'type': 'CO', 'hours': 'CO'}
                    co_days_set.add(day_number)
                    total_minutes_worked += leave_minutes
                elif is_cm:
                    days_matrix[day_number] = {'type': 'CM', 'hours': 'CM'}
                    cm_days_set.add(day_number)
                    total_minutes_worked += leave_minutes
                elif is_ef:
                    days_matrix[day_number] = {'type': 'EF', 'hours': 'EF'}
                    ef_days_set.add(day_number)
                    total_minutes_worked += leave_minutes
                else:
                    if (is_bank_holiday or is_weekend) and not (ts.start_time and ts.end_time) and not getattr(ts, 'duration_decimal', None):
                        continue
                    # Calculate worked hours for this timesheet entry
                    if hasattr(ts, 'duration_decimal') and ts.duration_decimal is not None:
                        hours = float(ts.duration_decimal)
                    elif ts.start_time and ts.end_time:
                        today_dummy = datetime.today()
                        dt1 = datetime.combine(today_dummy, ts.start_time)
                        dt2 = datetime.combine(today_dummy, ts.end_time)
                        hours = max(0.0, (dt2 - dt1).total_seconds() / 3600.0)
                    else:
                        hours = 8.5
                    minutes = round(hours * 60)  
                    current_entry = days_matrix[day_number]
                    if current_entry['type'] == 'work':
                        existing_minutes = int(current_entry['hours']) if current_entry['hours'] else 0
                        new_total_minutes = existing_minutes + minutes
                        days_matrix[day_number]['hours'] = new_total_minutes  # Store as minutes
                    else:
                        days_matrix[day_number] = {'type': 'work', 'hours': minutes}

                    total_minutes_worked += minutes
                    total_hours_worked += hours
                    # Track this day as a worked day for meal ticket eligibility
                    worked_days_set.add(day_number)
            
            # eligible_meal_ticket_days = worked_days_set - co_days_set - cm_days_set-ef_days_set
            # Standard Romanian Norm setup subtracting statutory bank holidays 
            norma_hours = workable_mon_thu * 8.5 + workable_fri * 6
            norma_minutes = norma_hours * 60
            employee_data.append({
                'employee': emp,
                'employee_name': f"{emp.first_name} {emp.last_name}".strip() if emp else "Unknown",
                'norma_hours': norma_hours,
                'norma_minutes': norma_minutes,
                'job_title': getattr(emp, 'job_title', None) or 'N/A',
                'days_matrix': days_matrix,
                'total_hours_worked': round(total_hours_worked, 1),
                'statutory_total_days': len(worked_days_set),
                'total_minutes_worked': total_minutes_worked,
                'total_co_days': len(co_days_set),
                'total_cm_days': len(cm_days_set),
                'total_ef_days': len(ef_days_set),
                
                # 'meal_tickets_count': len(eligible_meal_ticket_days)
            })
        serializable_employee_data = []

        for emp_data in employee_data:
            emp = emp_data.get('employee')

            # format name as last and first
            if emp:
                last = getattr(emp, 'last_name', '').strip()
                first = getattr(emp, 'first_name', '').strip()
                formatted_name = f"{last} {first}".strip() or getattr(emp, 'username', 'Unknown')
            serializable_emp_data = {
                'employee_id': emp.id if emp else None,
                'employee_name': formatted_name,
                'norma_hours': emp_data.get('norma_hours'),
                'norma_minutes': emp_data.get('norma_minutes'),
                'job_title': emp_data.get('job_title'),
                'days_matrix': emp_data.get('days_matrix'),
                'total_hours_worked': emp_data.get('total_hours_worked'),
                'total_minutes_worked': emp_data.get('total_minutes_worked'),
                'total_co_days': emp_data.get('total_co_days'),
                'total_cm_days': emp_data.get('total_cm_days'),
                'total_ef_days': emp_data.get('total_ef_days'),
                'statutory_total_days': emp_data.get('statutory_total_days'),
                # 'meal_tickets_count': emp_data.get('meal_tickets_count')
            }
            serializable_employee_data.append(serializable_emp_data)

        if serializable_employee_data:
            request.session['pdf_employee_data'] = serializable_employee_data
            request.session['pdf_period'] = {
                'year': year,
                'month': month,
                'period_query': period_query,
            }
        request.session.modified = True

        # context['employee_data'] = sorted(employee_data, key=lambda x: x['employee'].last_name)
        context['employee_data'] = employee_data
        context['current_period'] = period_query
        return context

class TimesheetPDFView(View):
    def get(self, request, *args, **kwargs):
        # 1. Parse target period (YYYY-MM)
        # Get data from session
        employee_data = request.session.get('pdf_employee_data', []) # Contains employee data with days_matrix, total_hours, etc.
        period_data = request.session.get('pdf_period', {}) # Contains year, month, period_query
        selected_period = request.GET.get('selected_period', datetime.now().strftime('%Y-%m'))
        if selected_period and not employee_data:
            try:
                year, month = map(int, selected_period.split('-'))
                return HttpResponse("Please load the summary page first.", status=400)
            except ValueError:
                pass
        if not employee_data:
            return HttpResponse("No data available. Please go back and load the summary first.", status=400)
        year = period_data.get('year', datetime.now().year)
        month = period_data.get('month', datetime.now().month)
        selected_period = period_data.get('period_query', f"{year}-{month:02d}")

        # Get total number of days in selected month as strict integers
        _, num_days = calendar.monthrange(year, month)
        month_days = list(range(1, num_days + 1))
        # 3. Setup PDF document (A4 landscape)
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=15,
            rightMargin=15,
            topMargin=15,
            bottomMargin=15
        )
        
        elements = []

        # 4. Setup Styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=12,
            leading=14,
            alignment=1,
            textColor=colors.HexColor('#1a252f')
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.HexColor('#555555')
        )

        header_cell_style = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontSize=6,
            leading=7,
            alignment=1,
            fontName='Helvetica-Bold'
        )

        name_cell_style = ParagraphStyle(
            'NameCell',
            parent=styles['Normal'],
            fontSize=6.5,
            leading=8,
            fontName='Helvetica-Bold'
        )

        body_cell_style = ParagraphStyle(
            'BodyCell',
            parent=styles['Normal'],
            fontSize=6,
            leading=7,
            alignment=1
        )

        sig_title_style = ParagraphStyle(
            'SigTitle',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            fontName='Helvetica-Bold',
            alignment=1
        )

        sig_name_style = ParagraphStyle(
            'SigName',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            alignment=1
        )

        # 5. Build Top Header Info
        month_name = get_romanian_month(month)
        elements.append(Paragraph(("FOAIE COLECTIVA DE PREZENTA"), title_style))
        elements.append(Paragraph(f"{('Pontaj lunar')} — {month_name} {year}", subtitle_style))
        elements.append(Spacer(1, 8))

        # 6. Construct dynamic table headers
        row1 = [
            Paragraph("<b>Nr.<br/>crt.</b>", header_cell_style),
            Paragraph("<b>Nume Prenume</b>", header_cell_style),
            Paragraph("<b>Norma</b>", header_cell_style),
        ]
        
        for day_int in month_days:
            row1.append(Paragraph(f"<b>{day_int}</b>", header_cell_style))
            
        row1.extend([
            Paragraph("<b>Total<br/>ore</b>", header_cell_style),
            Paragraph("<b>Zile<br/>CO</b>", header_cell_style),
            Paragraph("<b>Zile<br/>CM</b>", header_cell_style),
            Paragraph("<b>Zile<br/>EF</b>", header_cell_style),
            # Paragraph("<b>Tichete<br/>Masa</b>", header_cell_style),
        ])
        total_ore_col_idx = 3 + num_days
        alert_cell_style = ParagraphStyle(
                            'AlertCell',
                            parent=styles['Normal'],
                            fontSize=6,
                            leading=7,
                            alignment=1,
                            fontName='Helvetica-Bold',
                            textColor=colors.HexColor('#CC0000'),
                            borderColor=colors.HexColor('#CC0000'),
                        )
        table_styles = []
        table_data = [row1]
        # 7. Populate employee rows
        for idx, row in enumerate(employee_data, start=1):
            # Safe name extraction
            if isinstance(row, dict):
                emp_name = row.get('employee_name', f"Angajat {idx}")
                job_title = row.get('job_title', "N/A")
                norma_minutes = row.get('norma_minutes', 168)
                days_matrix = row.get('days_matrix', {})
                total_minutes = row.get('total_minutes_worked')
                co_days = row.get('co_days', row.get('total_co_days', 0))
                cm_days = row.get('cm_days', row.get('total_cm_days', 0))
                ef_days = row.get('ef_days', row.get('total_ef_days', 0))
                # meal_tickets = row.get('meal_tickets', row.get('meal_tickets_count', 0))
            else:
                emp_name = getattr(row, 'employee_name')
                job_title = getattr(row, 'job_title', "N/A")
                norma_minutes = getattr(row, 'norma_minutes', 168)
                days_matrix = getattr(row, 'days_matrix', {})
                total_minutes = getattr(row, 'total_minutes_worked', 0)
                co_days = getattr(row, 'co_days', 0)
                cm_days = getattr(row, 'cm_days', 0)
                ef_days = getattr(row, 'ef_days', 0)
                # meal_tickets = getattr(row, 'meal_tickets', 0)
            # fetch and format employee name
            emp_name = f"{emp_name}".strip() if emp_name else f"Angajat {idx}"
            total_formatted = format_minutes(total_minutes) if total_minutes is not None else "0:00"
            norma_formated = format_minutes(norma_minutes) if norma_minutes is not None else "0:00"
            total_mismatch = (total_minutes != norma_minutes)
                        
            if total_mismatch:
                table_styles.append(
                    ('BACKGROUND', (total_ore_col_idx, idx), (total_ore_col_idx, idx), colors.HexColor('#FFE6E6'))
                )
            data_row = [
                Paragraph(str(idx), body_cell_style),
                Paragraph(emp_name, name_cell_style),
                Paragraph(norma_formated, body_cell_style),
            ]
            # Populate matrix days
            for day_int in month_days:
                # Get the day's data
                day_data = days_matrix.get(str(day_int), {})                
                # Extract and format the value
                if isinstance(day_data, dict):
                    raw_value = day_data.get('hours', '')
                    # Format if it's a number (minutes)
                    if isinstance(raw_value, (int, float)) and raw_value > 0:
                        cell_val = format_minutes(raw_value)  # 510 -> 8:30
                    elif isinstance(raw_value, str):
                        cell_val = raw_value  # "CO", "CM", "EF", or ""
                    else:
                        cell_val = ''
                else:
                    cell_val = ''
                
                # Add to PDF cell
                data_row.append(Paragraph(str(cell_val if cell_val is not None else ''), body_cell_style))
            total_paragraph_style = alert_cell_style if total_mismatch else body_cell_style

            # Append totals and counts    
            data_row.extend([
                Paragraph(total_formatted, total_paragraph_style),
                Paragraph(str(co_days), body_cell_style),
                Paragraph(str(cm_days), body_cell_style),
                Paragraph(str(ef_days), body_cell_style),
                # Paragraph(str(meal_tickets), body_cell_style),
            ])

            table_data.append(data_row)

        # 8. Define Column Widths
        col_widths = [18, 95, 25]
        day_col_width = max(15.5, (520 / num_days))
        col_widths.extend([day_col_width] * num_days)
        col_widths.extend([32, 22, 22, 22, 26])

        # 9. Style Table Grid & Weekend Highlights
        t_style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#666666')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f3f5')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ]

        # Light gray background for weekends
        for idx_d, day_int in enumerate(month_days):
            weekday = calendar.weekday(year, month, day_int)
            if weekday in (5, 6):  # Saturday / Sunday
                col_index = 3 + idx_d
                t_style.append(('BACKGROUND', (col_index, 0), (col_index, -1), colors.HexColor('#eaeaea')))
        t_style.extend(table_styles)
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle(t_style))
        elements.append(t)

        # 10. SIGNATURE BLOCKS
        elements.append(Spacer(1, 20))

        sig_data = [
            [
                Paragraph("<b>Sef Paza,</b>", sig_title_style),
                "",
                Paragraph("<b>Director,</b>", sig_title_style)
            ],
            [
                Paragraph("Damian Mihai", sig_name_style),
                "",
                Paragraph("Negutescu Ion Clementin", sig_name_style)
            ],
            [
                Paragraph("Semnatura: _______________________", sig_name_style),
                "",
                Paragraph("Semnatura: _______________________", sig_name_style)
            ]
        ]

        sig_table = Table(sig_data, colWidths=[250, 311, 250])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
        ]))

        elements.append(sig_table)

        # 11. Render PDF
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Pontaj_{year}_{month:02d}.pdf"'
        return response


class TimesheetStandardizedHoursPDFView(View):
    def get(self, request, *args, **kwargs):
        # 1. Parse target period (YYYY-MM)
        # Get data from session
        employee_data = request.session.get('pdf_employee_data', []) # Contains employee data with days_matrix, total_hours, etc.
        
        period_data = request.session.get('pdf_period', {}) # Contains year, month, period_query
        selected_period = request.GET.get('selected_period', datetime.now().strftime('%Y-%m'))
        if selected_period and not employee_data:
            try:
                year, month = map(int, selected_period.split('-'))
                return HttpResponse("Please load the summary page first.", status=400)
            except ValueError:
                pass
        if not employee_data:
            return HttpResponse("No data available. Please go back and load the summary first.", status=400)
        year = period_data.get('year', datetime.now().year)
        month = period_data.get('month', datetime.now().month)
        selected_period = period_data.get('period_query', f"{year}-{month:02d}")

        # Get total number of days in selected month as strict integers
        _, num_days = calendar.monthrange(year, month)
        month_days = list(range(1, num_days + 1))
        ro_holidays = holidays.Romania(years=year)
        # 3. Setup PDF document (A4 landscape)
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=15,
            rightMargin=15,
            topMargin=15,
            bottomMargin=15
        )
        
        elements = []

        # 4. Setup Styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=12,
            leading=14,
            alignment=1,
            textColor=colors.HexColor('#1a252f')
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.HexColor('#555555')
        )

        header_cell_style = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontSize=6,
            leading=7,
            alignment=1,
            fontName='Helvetica-Bold'
        )

        name_cell_style = ParagraphStyle(
            'NameCell',
            parent=styles['Normal'],
            fontSize=6.5,
            leading=8,
            fontName='Helvetica-Bold'
        )

        body_cell_style = ParagraphStyle(
            'BodyCell',
            parent=styles['Normal'],
            fontSize=6,
            leading=7,
            alignment=1
        )

        sig_title_style = ParagraphStyle(
            'SigTitle',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            fontName='Helvetica-Bold',
            alignment=1
        )

        sig_name_style = ParagraphStyle(
            'SigName',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            alignment=1
        )

        # 5. Build Top Header Info
        month_name = get_romanian_month(month)
        elements.append(Paragraph(("FOAIE COLECTIVA DE PREZENTA"), title_style))
        elements.append(Paragraph(f"{('Pontaj lunar')} — {month_name} {year}", subtitle_style))
        elements.append(Spacer(1, 8))

        # 6. Construct dynamic table headers
        row1 = [
            Paragraph("<b>Nr.<br/>crt.</b>", header_cell_style),
            Paragraph("<b>Nume Prenume</b>", header_cell_style),
            Paragraph("<b>Functie</b>", header_cell_style),
        ]
        
        for day_int in month_days:
            row1.append(Paragraph(f"<b>{day_int}</b>", header_cell_style))
        # Add the additional columns for totals and counts
        row1.extend([
            Paragraph("<b>Total<br/>zile<br/>lucrate</b>", header_cell_style),
            Paragraph("<b>Zile<br/>CO</b>", header_cell_style),
            Paragraph("<b>Zile<br/>CM</b>", header_cell_style),
            Paragraph("<b>Zile<br/>EF</b>", header_cell_style),
            # Paragraph("<b>Tichete<br/>Masa</b>", header_cell_style),
        ])
        total_ore_col_idx = 3 + num_days
        alert_cell_style = ParagraphStyle(
            'AlertCell',
            parent=styles['Normal'],
            fontSize=6,
            leading=7,
            alignment=1,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#CC0000'),
            borderColor=colors.HexColor('#CC0000'),
        )
        table_styles = []
        table_data = [row1]
        statutory_norm, employee_rows = generate_statutory_pdf_context(year, month, employee_data, ro_holidays=ro_holidays) # Contains standardized hours data
        
        # 7. Populate employee rows
        for idx, row in enumerate(employee_rows, start=1):
            # Safe name extraction
            if isinstance(row, dict):
                emp_name = row.get('employee_name', f"Angajat {idx}")
                norma = row.get('statutory_norm', statutory_norm)
                job_title = row.get('job_title', "N/A")
                days_matrix = row.get('days_matrix', {})
                total_hours = row.get('statutory_total_hours', 0)
                total_worked_days = row.get('statutory_total_days', 0)
                co_days = row.get('co_days', row.get('total_co_days', 0))
                cm_days = row.get('cm_days', row.get('total_cm_days', 0))
                ef_days = row.get('ef_days', row.get('total_ef_days', 0))
                # meal_tickets = row.get('meal_tickets', row.get('meal_tickets_count', 0))
            else:
                emp_name = getattr(row, 'employee_name')
                norma = getattr(row, 'statutory_norm', statutory_norm)
                job_title = getattr(row, 'job_title', "N/A")
                days_matrix = getattr(row, 'days_matrix', {})
                total_hours = getattr(row, 'statutory_total_hours', 0)
                total_worked_days = getattr(row, 'statutory_total_days', 0)
                co_days = getattr(row, 'co_days', 0)
                cm_days = getattr(row, 'cm_days', 0)
                ef_days = getattr(row, 'ef_days', 0)
                # meal_tickets = getattr(row, 'meal_tickets', 0)

            # fetch and format employee name
            emp_name = f"{emp_name}".strip() if emp_name else f"Angajat {idx}"
            # Check for mismatch and apply alert style
            # total_mismatch = (total_hours != norma)
            
            total_formatted = f"{total_worked_days}" if total_worked_days else "0"
            # if total_mismatch:
            #     table_styles.append(
            #         ('BACKGROUND', (total_ore_col_idx, idx), (total_ore_col_idx, idx), colors.HexColor('#FFE6E6'))
            #     )
            data_row = [
                Paragraph(str(idx), body_cell_style),
                Paragraph(emp_name, name_cell_style),
                Paragraph(job_title, body_cell_style),
            ]
            # Populate matrix days
            for day_int in month_days:
                # Get the day's data
                day_data = days_matrix.get(str(day_int), {})                
                # Extract and format the value
                if isinstance(day_data, dict):
                    raw_value = day_data.get('hours', '')
                    # Format if it's a number (minutes)
                    if isinstance(raw_value, (int, float)) and raw_value > 0:
                        cell_val = raw_value  # Keep as is for standardized hours
                    elif isinstance(raw_value, str):
                        cell_val = raw_value  # "CO", "CM", "EF", or ""
                    else:
                        cell_val = ''
                else:
                    cell_val = ''
                
                # Add to PDF cell
                data_row.append(Paragraph(str(cell_val if cell_val is not None else ''), body_cell_style))
            # Choose paragraph style based on alert status
            # total_paragraph_style = alert_cell_style if total_mismatch else body_cell_style

            # Append totals and counts    
            data_row.extend([
                Paragraph(total_formatted, body_cell_style),
                Paragraph(str(co_days), body_cell_style),
                Paragraph(str(cm_days), body_cell_style),
                Paragraph(str(ef_days), body_cell_style),
                # Paragraph(str(meal_tickets), body_cell_style),
            ])

            table_data.append(data_row)

        # 8. Define Column Widths
        col_widths = [18, 95, 25]
        day_col_width = max(15.5, (520 / num_days))
        col_widths.extend([day_col_width] * num_days)
        col_widths.extend([32, 22, 22, 22, 26])

        # 9. Style Table Grid & Weekend Highlights
        t_style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#666666')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f3f5')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ]

        # Light gray background for weekends
        for idx_d, day_int in enumerate(month_days):
            weekday = calendar.weekday(year, month, day_int)
            if weekday in (5, 6):  # Saturday / Sunday
                col_index = 3 + idx_d
                t_style.append(('BACKGROUND', (col_index, 0), (col_index, -1), colors.HexColor("#b7e0bb")))
        t_style.extend(table_styles)
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle(t_style))
        elements.append(t)

        # 10. SIGNATURE BLOCKS
        elements.append(Spacer(1, 20))

        sig_data = [
            [
                Paragraph("<b>Sef Paza,</b>", sig_title_style),
                "",
                Paragraph("<b>Director,</b>", sig_title_style)
            ],
            [
                Paragraph("Damian Mihai", sig_name_style),
                "",
                Paragraph("Negutescu Ion Clementin", sig_name_style)
            ],
            [
                Paragraph("Semnatura: _______________________", sig_name_style),
                "",
                Paragraph("Semnatura: _______________________", sig_name_style)
            ]
        ]

        sig_table = Table(sig_data, colWidths=[250, 311, 250])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
        ]))

        elements.append(sig_table)

        # 11. Render PDF
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Pontaj_{year}_{month:02d}.pdf"'
        return response


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


class PALActivityUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Update view for Activity
    """
    model = Activity
    template_name = 'dashboard/pal_activity_edit.html'
    success_url = reverse_lazy('pal')
    form_class = PALActivityForm

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class PALActivityDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
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
    team_members = CustomUser.objects.filter(is_approved=True, is_active=True)
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


# class ActivityProgramCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
#     """
#     Create view for Activity Program
#     """
#     model = ActivityProgram
#     template_name = 'activities/activity_program_create.html'
#     success_url = reverse_lazy('activity_program_list')  # or PDF generation page

#     def test_func(self):
#         return self.request.user.is_staff or self.request.user.is_superuser


class BulkActivityProgramCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Create one weekly activity program with several activities, each with its own rangers."""
    template_name = 'activities/activity_program_create.html'
    code_field_re = re.compile(r'^activity_(\d+)_code$')
    approver_fields = ('director', 'chief_ranger', 'accountant')
    # Non-reporter personnel (office, management) are always assigned to the PAL activity
    pal_code = 'PAL'
    pal_title = 'Activități conform PAL'
    # Keyword (case-insensitive) that the Job title field must contain for a user to be assignable to activities
    ranger_job_title = 'ranger'
    # Job title keywords (lowercase, without diacritics) identifying each approver
    approver_job_titles = {
        'director': ('director', 'Director',),
        'chief_ranger': ('sef paza', 'chief ranger', 'Sef Paza',),
        'accountant': ('Contabil Sef', 'accountant', 'contabil',),
        'biologist': ('Biolog',  'biolog'),
    }

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    @staticmethod
    def normalize_job_title(title):
        # "Șef Pază" -> "sef paza"
        decomposed = unicodedata.normalize('NFKD', title or '')
        return ' '.join(''.join(c for c in decomposed if not unicodedata.combining(c)).lower().split())

    def find_approver_by_job_title(self, users, field):
        keywords = self.approver_job_titles[field]
        titles = [(u, self.normalize_job_title(u.job_title)) for u in users]
        # Prefer an exact job title, then one starting with the keyword (e.g. "Contabil șef")
        for matches in (
            lambda t: t in keywords,
            lambda t: any(t.startswith(k) for k in keywords),
        ):
            for user, title in titles:
                if matches(title):
                    return user
        return None

    def get_context(self, selected=None, cards=None):
        active_users = User.objects.filter(is_approved=True, is_active=True).order_by("last_name", "first_name")
        if selected is None:
            # Default the approvers from the users' job titles,
            # falling back to the ones used on the previous program
            last_program = ActivityProgram.objects.order_by('-registration_date', '-pk').first()
            selected = {'week': str(timezone.now().isocalendar()[1])}
            for field in self.approver_fields:
                approver = self.find_approver_by_job_title(active_users, field)
                if approver is not None:
                    approver_id = approver.pk
                else:
                    approver_id = getattr(last_program, f'{field}_id', None) if last_program else None
                selected[field] = str(approver_id or '')
        return {
            'active_users': active_users,
            # Only users whose Job title contains "ranger" can be assigned to activities
            'reporters': active_users.filter(job_title__icontains=self.ranger_job_title),
            'pal_personnel': active_users.exclude(job_title__icontains=self.ranger_job_title),
            'pal_code': self.pal_code,
            'pal_title': self.pal_title,
            'activities':natsorted(Activity.objects.all(), key=lambda a: a.code),
            'week_choices': [(str(w), label) for w, label in get_week_choices()],
            'selected': selected,
            'cards': cards or [{'code': '', 'title': '', 'ranger_ids': []}],
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        year = timezone.now().year
        week = request.POST.get('week', '')
        selected = {'week': week}
        for field in self.approver_fields:
            selected[field] = request.POST.get(field, '')

        # Each activity card posts activity_<i>_code / _title / _rangers.
        # Indexes can have gaps when cards are removed in the browser.
        indexes = sorted(
            int(m.group(1))
            for m in map(self.code_field_re.match, request.POST.keys())
            if m
        )
        cards = [
            {
                'code': request.POST.get(f'activity_{i}_code', ''),
                'title': request.POST.get(f'activity_{i}_title', '').strip(),
                'ranger_ids': request.POST.getlist(f'activity_{i}_rangers'),
            }
            for i in indexes
        ]

        errors = []
        valid_weeks = {w for w, _ in get_week_choices()}
        if not week.isdigit() or int(week) not in valid_weeks:
            errors.append("Selectează o săptămână validă.")
        elif ActivityProgram.objects.filter(year=year, week=int(week)).exists():
            errors.append(
                f"Există deja un program pentru săptămâna {week}/{year}. "
                "Modifică programul existent sau alege altă săptămână."
            )

        active_users = {str(u.pk): u for u in User.objects.filter(is_active=True)}
        reporters = {pk: u for pk, u in active_users.items() if self.ranger_job_title in (u.job_title or '').lower()}
        labels ={'director': 'directorul', 'chief_ranger': 'șeful pazei', 'accountant': 'contabilul șef'}
        approvers = {}
        for field in self.approver_fields:
            approvers[field] = active_users.get(selected[field])
            if approvers[field] is None:
                errors.append(f"Selectează {labels[field]}.")

        activities = {a.code: a for a in Activity.objects.all()}
        if not cards:
            errors.append("Adaugă cel puțin o activitate.")
        for position, card in enumerate(cards, start=1):
            if card['code'] not in activities:
                errors.append(f"Activitatea #{position}: selectează codul activității.")
            if not any(r in reporters for r in card['ranger_ids']):
                errors.append(f"Activitatea #{position}: selectează cel puțin un ranger.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, self.template_name, self.get_context(selected, cards))

        with transaction.atomic():
            last_nr = ActivityProgram.objects.aggregate(m=Max('registration_nr'))['m'] or 0
            program = ActivityProgram.objects.create(
                registration_nr=last_nr + 1,
                registration_date=timezone.now().date(),
                year=year,
                week=int(week),
                created_by=request.user,
                **approvers,
            )
            for card in cards:
                activity_obj = activities[card['code']]
                item = program.items.create(
                    activity_code=activity_obj.code,
                    activity_title=card['title'] or activity_obj.name,
                )
                item.rangers.set([reporters[r] for r in card['ranger_ids'] if r in reporters])

            pal_personnel = [u for pk, u in active_users.items() if pk not in reporters]
            if pal_personnel:
                pal_item = program.items.create(activity_code=self.pal_code, activity_title=self.pal_title)
                pal_item.rangers.set(pal_personnel)

            # All personnel sign the program (signal creates their pending signatures),
            # plus the extra signatures of the approvers.
            program.assigned_rangers.set(active_users.values())
            program.create_approver_signatures()

        messages.success(
            request,
            f"Programul pentru săptămâna {week}/{year} a fost creat cu {len(cards)} activități.",
        )
        return redirect('activity_program_list')


class ActivityProgramListView(LoginRequiredMixin, ListView):
    model = ActivityProgram
    template_name = 'activities/activity_program_list.html'
    context_object_name = 'activity_programs'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        qs = ActivityProgram.objects.annotate(
            signatures_total=Count('signatures', distinct=True),
            signatures_signed=Count('signatures', filter=Q(signatures__is_signed=True), distinct=True),
        ).prefetch_related('items').order_by('-year', '-week')
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(pk__in=ActivityProgramSignature.objects.filter(ranger=user).values('program'))


class ActivityProgramDetailView(LoginRequiredMixin, DetailView):
    model = ActivityProgram
    template_name = 'activities/activity_program_detail.html'
    context_object_name = 'program'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        program = self.get_object()

        # Signature status context: a user can have a personnel signature
        # and, if an approver, an extra one for their role
        user_sigs = program.signatures.filter(ranger=user)
        context['user_sigs'] = user_sigs
        context['pending_sigs'] = [sig for sig in user_sigs if not sig.is_signed]
        context['can_sign'] = bool(context['pending_sigs'])
        context['items'] = program.items.prefetch_related('rangers')
        context['all_signatures'] = program.signatures.select_related('ranger').order_by('role', 'ranger__last_name')
        return context


class ActivityProgramUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Update view for Activity Program
    """
    model = ActivityProgram
    form_class = ActivityProgramUpdateForm
    template_name = 'activities/activity_program_edit.html'
    success_url = reverse_lazy('activity_program_list')

    code_field_re = re.compile(r'^activity_(\d+)_code$')
    approver_fields = ('director', 'chief_ranger', 'accountant')
    # Non-reporter personnel (office, management) are always assigned to the PAL activity
    pal_code = 'PAL'
    pal_title = 'Activități conform PAL'
    # Keyword (case-insensitive) that the Job title field must contain for a user to be assignable to activities
    ranger_job_title = 'ranger'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_object(self, queryset=None):
        return get_object_or_404(ActivityProgram, pk=self.kwargs['pk'])

    def get_program_cards(self, program):
        """Rebuild the editable activity cards from the program's items (excluding the auto PAL item)."""
        cards = []
        for item in program.items.all():
            if item.activity_code.upper() == self.pal_code.upper():
                continue
            cards.append({
                'code': item.activity_code,
                'title': item.activity_title,
                'ranger_ids': [str(r.pk) for r in item.rangers.all()],
            })
        if not cards:
            cards = [{'code': '', 'title': '', 'ranger_ids': []}]
        return cards

    def build_context(self, program, selected=None, cards=None):
        active_users = User.objects.filter(is_approved=True, is_active=True).order_by("last_name", "first_name")
        if selected is None:
            selected = {
                'week': str(program.week),
                'director': str(program.director_id or ''),
                'chief_ranger': str(program.chief_ranger_id or ''),
                'accountant': str(program.accountant_id or ''),
            }
        return {
            'object': program,
            'active_users': active_users,
            # Only users whose Job title contains "ranger" can be assigned to activities
            'reporters': active_users.filter(job_title__icontains=self.ranger_job_title),
            'pal_personnel': active_users.exclude(job_title__icontains=self.ranger_job_title),
            'pal_code': self.pal_code,
            'pal_title': self.pal_title,
            'activities': natsorted(Activity.objects.all(), key=lambda a: a.code),
            'week_choices': [(str(w), label) for w, label in get_week_choices()],
            'selected': selected,
            'cards': cards if cards is not None else self.get_program_cards(program),
        }

    def get(self, request, *args, **kwargs):
        program = self.get_object()
        return render(request, self.template_name, self.build_context(program))

    def post(self, request, *args, **kwargs):
        program = self.get_object()
        year = program.year
        week = request.POST.get('week', '')
        selected = {'week': week}
        for field in self.approver_fields:
            selected[field] = request.POST.get(field, '')

        indexes = sorted(
            int(m.group(1))
            for m in map(self.code_field_re.match, request.POST.keys())
            if m
        )
        cards = [
            {
                'code': request.POST.get(f'activity_{i}_code', ''),
                'title': request.POST.get(f'activity_{i}_title', '').strip(),
                'ranger_ids': request.POST.getlist(f'activity_{i}_rangers'),
            }
            for i in indexes
        ]

        errors = []
        valid_weeks = {w for w, _ in get_week_choices()}
        if not week.isdigit() or int(week) not in valid_weeks:
            errors.append("Selectează o săptămână validă.")
        elif int(week) != program.week and ActivityProgram.objects.filter(year=year, week=int(week)).exists():
            errors.append(
                f"Există deja un program pentru săptămâna {week}/{year}. "
                "Modifică programul existent sau alege altă săptămână."
            )

        active_users = {str(u.pk): u for u in User.objects.filter(is_active=True)}
        reporters = {pk: u for pk, u in active_users.items() if self.ranger_job_title in (getattr(u, 'job_title', '') or '').lower()}
        labels = {'director': 'directorul', 'chief_ranger': 'șeful pazei', 'accountant': 'contabilul șef'}
        approvers = {}
        for field in self.approver_fields:
            approvers[field] = active_users.get(selected[field])
            if approvers[field] is None:
                errors.append(f"Selectează {labels[field]}.")

        activities = {a.code: a for a in Activity.objects.all()}
        if not cards:
            errors.append("Adaugă cel puțin o activitate.")
        for position, card in enumerate(cards, start=1):
            if card['code'] not in activities:
                errors.append(f"Activitatea #{position}: selectează codul activității.")
            if not any(r in reporters for r in card['ranger_ids']):
                errors.append(f"Activitatea #{position}: selectează cel puțin un ranger.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, self.template_name, self.build_context(program, selected, cards))

        with transaction.atomic():
            program.week = int(week)
            program.director = approvers['director']
            program.chief_ranger = approvers['chief_ranger']
            program.accountant = approvers['accountant']
            program.save()

            # Rebuild the activity items from the submitted cards
            ActivityProgramItem.objects.filter(program=program).delete()
            for card in cards:
                activity_obj = activities[card['code']]
                item = ActivityProgramItem.objects.create(
                    program=program,
                    activity_code=activity_obj.code,
                    activity_title=card['title'] or activity_obj.name,
                )
                item.rangers.set([reporters[r] for r in card['ranger_ids'] if r in reporters])

            # Recreate the automatic PAL item for non-reporter personnel
            pal_personnel = [u for pk, u in active_users.items() if pk not in reporters]
            if pal_personnel:
                pal_item = ActivityProgramItem.objects.create(
                    program=program,
                    activity_code=self.pal_code,
                    activity_title=self.pal_title,
                )
                pal_item.rangers.set(pal_personnel)

            program.assigned_rangers.set(active_users.values())
            program.create_approver_signatures()

        messages.success(
            request,
            f"Programul pentru săptămâna {week}/{year} a fost actualizat cu {len(cards)} activități.",
        )
        return redirect('activity_program_list')


class ActivityProgramExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Export view for Activity Program generated using ReportLab (Portrait A4)."""

    def test_func(self):
        return self.request.user.is_authenticated

    def get(self, request, pk, *args, **kwargs):
        program = get_object_or_404(ActivityProgram, pk=pk)

        # Fetch items and prefetch rangers
        items = (
            ActivityProgramItem.objects.filter(program=program)
            .prefetch_related('rangers')
            .order_by('activity_code')
        )

        # Identify all distinct staff members assigned
        staff_members = set()
        for ranger in program.assigned_rangers.all():
            staff_members.add(ranger)

        # Days mapping (Luni - Duminica)
        days_map = [
            ('Luni', 1),
            ('Marti', 2),
            ('Miercuri', 3),
            ('Joi', 4),
            ('Vineri', 5),
            ('Sambata', 6),
            ('Duminica', 7),
        ]

        # 1. Setup Document Buffer (A4 Portrait)
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=portrait(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20,
        )

        elements = []

        # 2. Setup Styles
        styles = getSampleStyleSheet()

        header_title_style = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Heading1'],
            fontSize=10,
            leading=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0f172a'),
        )

        header_subtitle_style = ParagraphStyle(
            'HeaderSubtitle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#475569'),
        )

        director_title_style = ParagraphStyle(
            'DirectorTitle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=1,  # Center
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#000000'),
        )

        director_name_style = ParagraphStyle(
            'DirectorName',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=1,  # Center
            textColor=colors.HexColor('#1e293b'),
        )

        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=9,
            alignment=1,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e293b'),
        )

        body_cell_style = ParagraphStyle(
            'BodyCell',
            parent=styles['Normal'],
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor('#1e293b'),
        )

        name_cell_style = ParagraphStyle(
            'NameCell',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=9,
            alignment=1,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0f172a'),
        )

        day_cell_style = ParagraphStyle(
            'DayCell',
            parent=styles['Normal'],
            fontSize=7,
            leading=8.5,
            alignment=1,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#334155'),
        )

        sig_title_style = ParagraphStyle(
            'SigTitle',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=9,
            fontName='Helvetica-Bold',
            alignment=1,
            textColor=colors.HexColor('#0f172a'),
        )

        sig_name_style = ParagraphStyle(
            'SigName',
            parent=styles['Normal'],
            fontSize=7,
            leading=8.5,
            alignment=1,
            textColor=colors.HexColor('#334155'),
        )

        rules_style = ParagraphStyle(
            'RulesText',
            parent=styles['Normal'],
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor('#334155'),
        )

        # 3. Build Top Header Block (Org Info + Director Approval Box)
        director_name = (
            program.director.get_full_name()
            if hasattr(program, 'director') and program.director
            else '__________________'
        )

        header_left = [
            Paragraph(
                '<b>ADMINISTRATIA PARCULUI NATURAL BUCEGI</b>', header_title_style
            ),
            Spacer(1, 2),
            Paragraph(
                f'Nr. {getattr(program, "registration_number", "____/NIC/____")}',
                header_subtitle_style,
            ),
            Spacer(1, 4),
            Paragraph(
                f'<b>PROGRAM SAPTAMANA {program.week} ({program.year})</b>',
                header_title_style,
            ),
        ]

        header_right = [
            Paragraph('Se aproba,', director_title_style),
            Paragraph('<b>DIRECTOR</b>', director_title_style),
            Spacer(1, 2),
            Paragraph(director_name, director_name_style),
            Spacer(1, 4),
            Paragraph('Semnatura: ____________', director_title_style),
        ]

        header_table = Table([[header_left, header_right]], colWidths=[355, 200])
        header_table.setStyle(
            TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                (
                    'BOX',
                    (1, 0),
                    (1, 0),
                    1,
                    colors.HexColor('#0f172a'),
                ),  # Border around Director box
                ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f8fafc')),
                ('TOPPADDING', (1, 0), (1, 0), 6),
                ('BOTTOMPADDING', (1, 0), (1, 0), 6),
                ('LEFTPADDING', (1, 0), (1, 0), 6),
                ('RIGHTPADDING', (1, 0), (1, 0), 6),
            ])
        )

        elements.append(header_table)
        elements.append(Spacer(1, 10))

        # 4. Construct Schedule Table Matrix
        table_data = [[
            Paragraph('<b>Nr.<br/>crt.</b>', table_header_style),
            Paragraph('<b>NUME SI PRENUME</b>', table_header_style),
            Paragraph('<b>ZIUA</b>', table_header_style),
            Paragraph('<b>PROGRAM SAPTAMANAL</b>', table_header_style),
            Paragraph(
                '<b>SEMNATURA<br/><font size=5.5>(LUAT LA'
                ' CUNOSTINTA)</font></b>',
                table_header_style,
            ),
        ]]

        table_styles = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#475569')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]

        current_row = 1
        for idx, member in enumerate(sorted(staff_members, key=lambda m: m.id), 1):
            user_fullname = (member.get_full_name().upper() if member.get_full_name() else member.username.upper())
            start_person_row = current_row

        for day_label, day_code in days_map:
            day_acts = []
            for item in items:
                item_rangers = item.rangers.all()
                # Check if ranger is explicitly tagged on the item OR if no specific rangers are assigned to the item
                if member in item_rangers or not item_rangers.exists():
                    item_day = getattr(item, 'day', getattr(item, 'day_of_week', None))
                    if item_day is None or item_day == day_code:
                        act_str = f'<b>{item.activity_code}</b> - {item.activity_title}'
                        day_acts.append(Paragraph(act_str, body_cell_style))

            acts_content = (
                day_acts if day_acts else Paragraph('-', body_cell_style)
            )

            row = [
                Paragraph(str(person_index), body_cell_style),
                Paragraph(user_fullname, name_cell_style),
                Paragraph(day_label, day_cell_style),
                acts_content,
                Paragraph('Semnătura: _________', sig_name_style),
            ]
            table_data.append(row)
            current_row += 1

        end_person_row = current_row - 1

        # Span Person Name, Index, and Signature across the 7 days of the week
        table_styles.extend([
            ('SPAN', (0, start_person_row), (0, end_person_row)),
            ('SPAN', (1, start_person_row), (1, end_person_row)),
            ('SPAN', (4, start_person_row), (4, end_person_row)),
            ('VALIGN', (0, start_person_row), (1, end_person_row), 'MIDDLE'),
            ('VALIGN', (4, start_person_row), (4, end_person_row), 'MIDDLE'),
            (
                'BACKGROUND',
                (1, start_person_row),
                (1, end_person_row),
                colors.HexColor('#f8fafc'),
            ),
        ])

        # Column widths totaling ~555pt (A4 printable width)
        schedule_table = Table(
            table_data, colWidths=[20, 110, 50, 255, 120], repeatRows=1
        )
        schedule_table.setStyle(TableStyle(table_styles))
        elements.append(schedule_table)

        elements.append(Spacer(1, 8))

        # 5. Operational Instructions Box
        rules_text = Paragraph(
            '<b>ATENTIE! CERINTE OBLIGATORII:</b><br/>'
            '• In cazul activitatilor neprevazute, puteti grupa 2 sau 3 activitati'
            ' intr-o singura zi.<br/>'
            '• RAPORTUL ZILNIC ESTE OBLIGATORIU si va fi insotit de fotografii'
            ' realizate cu aplicatia GPS Map Camera (coordonate GPS, data si'
            ' ora).<br/>'
            '• Semnatura electronica/olografa aplicata dovedeste data intocmirii si'
            ' luarii la cunostinta.',
            rules_style,
        )
        rules_table = Table([[rules_text]], colWidths=[555])
        rules_table.setStyle(
            TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fffde7')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(rules_table)

        elements.append(Spacer(1, 12))

        # 6. Bottom Multi-Signature Grid
        sig_data = [
            [
                Paragraph('<b>Sef Paza</b>', sig_title_style),
                Paragraph('<b>Resp. Conscientizare</b>', sig_title_style),
                Paragraph('<b>Biolog / Conservare</b>', sig_title_style),
            ],
            [
                Paragraph(
                    getattr(
                        getattr(program, 'chief_ranger', None),
                        'get_full_name',
                        lambda: '________________',
                    )(),
                    sig_name_style,
                ),
                Paragraph(
                    getattr(
                        getattr(program, 'awareness_officer', None),
                        'get_full_name',
                        lambda: '________________',
                    )(),
                    sig_name_style,
                ),
                Paragraph(
                    getattr(
                        getattr(program, 'biologist', None),
                        'get_full_name',
                        lambda: '________________',
                    )(),
                    sig_name_style,
                ),
                Paragraph(
                    getattr(
                        getattr(program, 'created_by', None),
                        'get_full_name',
                        lambda: '________________',
                    )(),
                    sig_name_style,
                ),
            ],
            [
                Paragraph('Semnatura: ________', sig_name_style),
                Paragraph('Semnatura: ________', sig_name_style),
                Paragraph('Semnatura: ________', sig_name_style),
                Paragraph('Semnatura: ________', sig_name_style),
            ],
        ]

        sig_table = Table(sig_data, colWidths=[138, 139, 139, 139])
        sig_table.setStyle(
            TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ])
        )

        elements.append(sig_table)

        # 7. Render PDF Document
        doc.build(elements)
        buffer.seek(0)

        filename = f'Program_Activitate_Saptamana_{program.week}_{program.year}.pdf'
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class ActivityProgramDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
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


class ActivityProgramSignView(LoginRequiredMixin, View):
    def post(self, request, pk):
        program = get_object_or_404(ActivityProgram, pk=pk)
        role = request.POST.get('role', ActivityProgramSignature.Role.PERSONNEL.value)

        # Only the pending signatures created for the program can be signed
        sig_record = ActivityProgramSignature.objects.filter(
            program=program,
            ranger=request.user,
            role=role
        ).first()
        if sig_record is None:
            messages.error(request, "Nu aveți permisiunea de a semna acest program.")
            return redirect('activity_program_detail', pk=pk)

        signature_data = request.POST.get('signature_data', '')
        client_ip = request.META.get('REMOTE_ADDR')

        sig_record.is_signed = True
        sig_record.signed_at = timezone.now()
        sig_record.ip_address = client_ip
        sig_record.signature_data = signature_data
        sig_record.save()

        messages.success(request, "Programul a fost semnat cu succes.")
        return redirect('activity_program_detail', pk=pk)


class FundsSourceListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
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
