from django.views.generic import FormView, TemplateView
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.urls import reverse_lazy
from timesheet.models import Timesheet
from .forms import ReportPeriodForm
from datetime import timedelta, datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment
import calendar
from django.utils.translation import gettext as _

class ReportGeneratorView(LoginRequiredMixin, FormView):
    template_name = 'reports/generate_report.html'
    form_class = ReportPeriodForm
    success_url = reverse_lazy('report_results')

    def form_valid(self, form):
        period = form.cleaned_data['period']
        report_type = form.cleaned_data['report_type']
        custom_start = form.cleaned_data.get('custom_start_date')
        custom_end = form.cleaned_data.get('custom_end_date')
        
        # Calculate date range
        today = timezone.now().date()
        
        if custom_start and custom_end:
            start_date = custom_start
            end_date = custom_end
            period = 'custom'
        elif period == 'weekly':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        else:  # monthly
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Store in session for results view
        self.request.session['report_data'] = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'period': period,
            'report_type': report_type,
            'user_id': self.request.user.id
        }
        return super().form_valid(form)

class ReportResultsView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/report_results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_data = self.request.session.get('report_data', {})
        
        if not report_data:
            return context
            
        start_date = datetime.strptime(report_data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(report_data.get('end_date'), '%Y-%m-%d').date()
        period = report_data.get('period', 'weekly')
        
        # Set report titles
        if period == 'custom':
            context['report_title'] = _("Custom Period Report")
            context['period_detail'] = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif period == 'weekly':
            context['report_title'] = _("Weekly Report")
            context['period_detail'] = _("Week") + f" {start_date.isocalendar()[1]}, {start_date.year}"
        else:
            context['report_title'] = _("Monthly Report")
            context['period_detail'] = f"{_(calendar.month_name[start_date.month])} {start_date.year}"
        
        # Get timesheets for period
        timesheets = Timesheet.objects.filter(
            user_id=report_data.get('user_id'),
            date__range=[start_date, end_date]
        ).select_related('activity', 'fundssource')
        
        # Generate report data
        if report_data.get('report_type') == 'summary':
            context['report_type'] = 'summary'
            context['report_data'] = self._generate_summary_report(timesheets)
        else:
            context['report_type'] = 'detailed'
            context['report_data'] = self._generate_detailed_report(timesheets)
        
        # Overall statistics
        total_hours = 0
        for timesheet in timesheets:
            hours = self._calculate_hours(timesheet)
            total_hours += hours
        
        context['total_hours'] = total_hours
        context['total_entries'] = timesheets.count()
        context['average_hours'] = total_hours / timesheets.count() if timesheets.count() > 0 else 0
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['period'] = period
        
        return context
    
    def _calculate_hours(self, timesheet):
        """Calculate hours from start_time and end_time (both are time objects)"""
        if timesheet.start_time and timesheet.end_time:
            # Convert time objects to datetime objects for the same day to calculate difference
            start_datetime = datetime.combine(datetime.today(), timesheet.start_time)
            end_datetime = datetime.combine(datetime.today(), timesheet.end_time)
            
            # Handle case where end_time is after midnight (next day)
            if end_datetime < start_datetime:
                end_datetime = end_datetime + timedelta(days=1)
            
            duration = end_datetime - start_datetime
            return duration.total_seconds() / 3600
        return 0
    
    def _generate_summary_report(self, timesheets):
        """Generate summary report grouped by activity"""
        summary_data = []
        
        # Group by activity manually since we need to calculate hours
        activities = {}
        for timesheet in timesheets:
            activity_key = (timesheet.activity.id, timesheet.activity.code, timesheet.activity.name)
            if activity_key not in activities:
                activities[activity_key] = {
                    'activity__code': timesheet.activity.code,
                    'activity__name': timesheet.activity.name,
                    'fundssource__name': timesheet.fundssource.name if timesheet.fundssource else '',
                    'total_hours': 0,
                    'entries': 0
                }
            
            hours = self._calculate_hours(timesheet)
            activities[activity_key]['total_hours'] += hours
            activities[activity_key]['entries'] += 1
        
        # Convert to list and calculate averages
        for activity_data in activities.values():
            activity_data['avg_hours'] = activity_data['total_hours'] / activity_data['entries'] if activity_data['entries'] > 0 else 0
            summary_data.append(activity_data)
        
        return sorted(summary_data, key=lambda x: x['activity__code'])
    
    def _generate_detailed_report(self, timesheets):
        """Generate detailed report with all timesheet entries"""
        detailed_data = []
        for timesheet in timesheets.order_by('date', 'activity__code'):
            hours = self._calculate_hours(timesheet)
            detailed_data.append({
                'timesheet': timesheet,
                'hours': hours,
                'date': timesheet.date,
                'activity_code': timesheet.activity.code,
                'activity_name': timesheet.activity.name,
                'fundssource_name': timesheet.fundssource.name if timesheet.fundssource else '',
                'description': timesheet.description or '',
                'start_time': timesheet.start_time,
                'end_time': timesheet.end_time
            })
        
        return detailed_data

class ExportPDFView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        report_data = request.session.get('report_data', {})
        
        if not report_data:
            return HttpResponse("No report data found")
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Work Activity Report", styles['Title'])
        elements.append(title)
        
        # Period info
        start_date = datetime.strptime(report_data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(report_data.get('end_date'), '%Y-%m-%d').date()
        period_text = f"Period: {start_date} to {end_date}"
        elements.append(Paragraph(period_text, styles['Normal']))
        elements.append(Paragraph("<br/>", styles['Normal']))
        
        # Get report data
        timesheets = Timesheet.objects.filter(
            user_id=report_data.get('user_id'),
            date__range=[start_date, end_date]
        ).select_related('activity', 'fundssource')
        
        if report_data.get('report_type') == 'summary':
            table_data = [['Activity Code', 'Activity Name', 'Funds Source', 'Total Hours', 'Entries']]
            
            # Group by activity manually
            activities = {}
            for timesheet in timesheets:
                activity_key = (timesheet.activity.code, timesheet.activity.name)
                if activity_key not in activities:
                    activities[activity_key] = {
                        'code': timesheet.activity.code,
                        'name': timesheet.activity.name,
                        'fundssource': timesheet.fundssource.name if timesheet.fundssource else '',
                        'total_hours': 0,
                        'entries': 0
                    }
                
                hours = self._calculate_hours(timesheet)
                activities[activity_key]['total_hours'] += hours
                activities[activity_key]['entries'] += 1
            
            for activity_data in activities.values():
                table_data.append([
                    activity_data['code'],
                    activity_data['name'],
                    activity_data['fundssource'],
                    f"{activity_data['total_hours']:.2f}",
                    activity_data['entries']
                ])
        else:
            table_data = [['Date', 'Start Time', 'End Time', 'Activity Code', 'Activity Name', 'Hours', 'Description']]
            for timesheet in timesheets.order_by('date'):
                hours = self._calculate_hours(timesheet)
                
                table_data.append([
                    timesheet.date.strftime('%Y-%m-%d'),
                    timesheet.start_time.strftime('%H:%M') if timesheet.start_time else '',
                    timesheet.end_time.strftime('%H:%M') if timesheet.end_time else '',
                    timesheet.activity.code,
                    timesheet.activity.name,
                    f"{hours:.2f}",
                    timesheet.description or ''
                ])
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="activity_report.pdf"'
        return response
    
    def _calculate_hours(self, timesheet):
        """Calculate hours from start_time and end_time (both are time objects)"""
        if timesheet.start_time and timesheet.end_time:
            # Convert time objects to datetime objects for the same day to calculate difference
            start_datetime = datetime.combine(datetime.today(), timesheet.start_time)
            end_datetime = datetime.combine(datetime.today(), timesheet.end_time)
            
            # Handle case where end_time is after midnight (next day)
            if end_datetime < start_datetime:
                end_datetime = end_datetime + timedelta(days=1)
            
            duration = end_datetime - start_datetime
            return duration.total_seconds() / 3600
        return 0

class ExportExcelView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        report_data = request.session.get('report_data', {})
        
        if not report_data:
            return HttpResponse("No report data found")
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="activity_report.xlsx"'
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Activity Report"
        
        # Get dates from report data
        start_date = datetime.strptime(report_data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(report_data.get('end_date'), '%Y-%m-%d').date()
        
        # Get report data
        timesheets = Timesheet.objects.filter(
            user_id=report_data.get('user_id'),
            date__range=[start_date, end_date]
        ).select_related('activity', 'fundssource')
        
        # Add headers
        if report_data.get('report_type') == 'summary':
            headers = ['Activity Code', 'Activity Name', 'Funds Source', 'Total Hours', 'Entries']
            ws.append(headers)
            
            # Group by activity manually
            activities = {}
            for timesheet in timesheets:
                activity_key = (timesheet.activity.code, timesheet.activity.name)
                if activity_key not in activities:
                    activities[activity_key] = {
                        'code': timesheet.activity.code,
                        'name': timesheet.activity.name,
                        'fundssource': timesheet.fundssource.name if timesheet.fundssource else '',
                        'total_hours': 0,
                        'entries': 0
                    }
                
                hours = self._calculate_hours(timesheet)
                activities[activity_key]['total_hours'] += hours
                activities[activity_key]['entries'] += 1
            
            for activity_data in activities.values():
                ws.append([
                    activity_data['code'],
                    activity_data['name'],
                    activity_data['fundssource'],
                    round(activity_data['total_hours'], 2),
                    activity_data['entries']
                ])
        else:
            headers = ['Date', 'Start Time', 'End Time', 'Activity Code', 'Activity Name', 'Funds Source', 'Hours Worked', 'Description']
            ws.append(headers)
            
            for timesheet in timesheets.order_by('date'):
                hours = self._calculate_hours(timesheet)
                
                ws.append([
                    timesheet.date,
                    timesheet.start_time.strftime('%H:%M') if timesheet.start_time else '',
                    timesheet.end_time.strftime('%H:%M') if timesheet.end_time else '',
                    timesheet.activity.code,
                    timesheet.activity.name,
                    timesheet.fundssource.name if timesheet.fundssource else '',
                    round(hours, 2),
                    timesheet.description or ''
                ])
        
        # Style the header
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        wb.save(response)
        return response
    
    def _calculate_hours(self, timesheet):
        """Calculate hours from start_time and end_time (both are time objects)"""
        if timesheet.start_time and timesheet.end_time:
            # Convert time objects to datetime objects for the same day to calculate difference
            start_datetime = datetime.combine(datetime.today(), timesheet.start_time)
            end_datetime = datetime.combine(datetime.today(), timesheet.end_time)
            
            # Handle case where end_time is after midnight (next day)
            if end_datetime < start_datetime:
                end_datetime = end_datetime + timedelta(days=1)
            
            duration = end_datetime - start_datetime
            return duration.total_seconds() / 3600
        return 0

