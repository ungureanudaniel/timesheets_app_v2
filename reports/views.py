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
from users.models import CustomUser
import openpyxl
from openpyxl.styles import Font, Alignment
import calendar
from django.utils.translation import gettext as _

User = CustomUser

class ReportGeneratorView(LoginRequiredMixin, FormView):
    template_name = 'reports/generate_report.html'
    form_class = ReportPeriodForm
    success_url = reverse_lazy('report_results')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # This is the "user" that __init__ pops
        return kwargs

    def form_valid(self, form):
        period = form.cleaned_data['period']
        report_type = form.cleaned_data['report_type']
        custom_start = form.cleaned_data.get('custom_start_date')
        custom_end = form.cleaned_data.get('custom_end_date')
        selected_user = form.cleaned_data.get('user')

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
            'user_id': selected_user.id if selected_user else None,
        }
        return super().form_valid(form)

class ReportResultsView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/report_results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_data = self.request.session.get('report_data', {})
        
        if not report_data:
            return context

        # 1. GET THE USER ID ONCE
        # We prioritize the ID in the session (selected by manager)
        user_id = report_data.get('user_id')
        if not user_id:
            user_id = self.request.user.id 

        # 2. FETCH THE USER OBJECT
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            context['report_user'] = User.objects.get(id=user_id)
        except User.DoesNotExist:
            context['report_user'] = self.request.user
            user_id = self.request.user.id

        # 3. CONVERT DATES
        start_date = datetime.strptime(report_data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(report_data.get('end_date'), '%Y-%m-%d').date()

        # 4. THE FILTER (Run this ONLY ONCE)
        # This specific 'timesheets' variable is passed to ALL helpers
        timesheets = Timesheet.objects.filter(
            user_id=user_id,
            date__range=[start_date, end_date]
        ).select_related('activity', 'fundssource')

        # --- Start Title Logic ---
        period = report_data.get('period', 'weekly') 
        if period == 'custom':
            context['report_title'] = _("Custom Period Report")
            context['period_detail'] = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif period == 'weekly':
            context['report_title'] = _("Weekly Report")
            context['period_detail'] = _("Week") + f" {start_date.isocalendar()[1]}, {start_date.year}"
        else:
            context['report_title'] = _("Monthly Report")
            context['period_detail'] = f"{_(calendar.month_name[start_date.month])} {start_date.year}"
        # --- End Title Logic ---

        # 5. GENERATE DATA
        # Both these methods receive the EXACT SAME filtered 'timesheets'
        if report_data.get('report_type') == 'summary':
            context['report_type'] = 'summary'
            context['report_data'] = self._generate_summary_report(timesheets)
        else:
            context['report_type'] = 'detailed'
            context['report_data'] = self._generate_detailed_report(timesheets)
        
        # 6. OVERALL STATISTICS
        total_hours = sum(self._calculate_hours(ts) for ts in timesheets)
        
        count = timesheets.count()
        context['total_hours'] = total_hours
        context['total_entries'] = count
        context['average_hours'] = total_hours / count if count > 0 else 0
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
        detailed_data = []
        # Note the prefetch name here must match your model's related_name
        timesheets_with_imgs = timesheets.prefetch_related('timesheet_images').order_by('date', 'start_time')
        
        for ts in timesheets_with_imgs:
            hours = self._calculate_hours(ts)
            detailed_data.append({
                'date': ts.date,
                'hours': hours,
                'fundssource_name': ts.fundssource.name if ts.fundssource else '',
                'activity_code': ts.activity.code,
                'description': ts.description or '',
                'start_time': ts.start_time,
                'end_time': ts.end_time,
                # Use 'timesheet_images' if that is your related_name
                'images': ts.timesheet_images.all() 
            })
        return detailed_data

import os
from django.conf import settings
from reportlab.platypus import Image, Spacer
from reportlab.lib.units import inch

class ExportPDFView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        report_data = request.session.get('report_data', {})
        if not report_data:
            return HttpResponse("No report data found")
        
        buffer = BytesIO()
        # Use a slightly smaller margin to fit more content
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        # 1. Header Information
        start_date_str = report_data.get('start_date')
        end_date_str = report_data.get('end_date')
        elements.append(Paragraph(f"Raport de activitate", styles['Title']))
        elements.append(Paragraph(f"Perioada: {start_date_str} - {end_date_str}", styles['Normal']))
        elements.append(Spacer(1, 0.2 * inch))

        # 2. Get Data with Images
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        timesheets = Timesheet.objects.filter(
            user_id=report_data.get('user_id'),
            date__range=[start_date, end_date]
        ).select_related('activity', 'fundssource').prefetch_related('timesheet_images').order_by('date', 'start_time')

        # 3. Grouping Logic
        current_date = None
        
        for ts in timesheets:
            # If date changes, add a Date Header
            if ts.date != current_date:
                current_date = ts.date
                elements.append(Spacer(1, 0.1 * inch))
                date_header_style = styles['Heading3']
                date_header_style.backColor = colors.whitesmoke
                elements.append(Paragraph(f"Data: {current_date.strftime('%Y-%m-%d')}", date_header_style))
                elements.append(Spacer(1, 0.05 * inch))

            # Entry Table for this specific recording
            hours = self._calculate_hours(ts)
            
            # Formatting the table for a single entry
            entry_data = [
                [_('Time'), _('Activity'), _('Source'), _('Hrs'), _('Description')],
                [
                    f"{ts.start_time.strftime('%H:%M')}-{ts.end_time.strftime('%H:%M')}",
                    Paragraph(f"<b>{ts.activity.code}</b><br/>{ts.activity.name}", styles['Normal']),
                    ts.fundssource.name if ts.fundssource else '-',
                    f"{hours:.2f}",
                    Paragraph(ts.description or '', styles['Normal'])
                ]
            ]
            
            # Table settings: width distribution
            col_widths = [0.8*inch, 1.8*inch, 1.0*inch, 0.5*inch, 3.2*inch]
            t = Table(entry_data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(t)

            # 4. Handle Images for this entry
            # --- FIXED IMAGE WRAPPING LOGIC ---
            ts_images = ts.timesheet_images.all() 
            if ts_images:
                img_elements = []
                for img_obj in ts_images:
                    try:
                        img_path = img_obj.image.path
                        if os.path.exists(img_path):
                            img = Image(img_path)
                            # Scale height to 1.2 inches, keep aspect ratio
                            aspect = img.imageHeight / float(img.imageWidth)
                            img.drawHeight = 1.2 * inch
                            img.drawWidth = (1.2 * inch) / aspect
                            img_elements.append(img)
                    except Exception:
                        continue
                
                if img_elements:
                    # Break images into rows of 3 to prevent "overflow" on the right
                    images_per_row = 3
                    rows = [img_elements[i:i + images_per_row] for i in range(0, len(img_elements), images_per_row)]
                    
                    # Create a table where each row has max 3 images
                    # colWidths distributes the 7.5 inches of available width
                    img_grid = Table(rows, colWidths=[2.3 * inch] * images_per_row, hAlign='LEFT')
                    img_grid.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ]))
                    elements.append(img_grid)
            # --- END IMAGE LOGIC ---

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="activity_report.pdf"'
        return response

    def _calculate_hours(self, timesheet):
        if timesheet.start_time and timesheet.end_time:
            start_datetime = datetime.combine(datetime.today(), timesheet.start_time)
            end_datetime = datetime.combine(datetime.today(), timesheet.end_time)
            if end_datetime < start_datetime:
                end_datetime = end_datetime + timedelta(days=1)
            duration = end_datetime - start_datetime
            return duration.total_seconds() / 3600
        return 0

class ExportExcelView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        report_data = request.session.get('report_data', {})
        
        if not report_data:
            return HttpResponse(_("No report data found"))
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="activity_report.xlsx"'
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = _("Activity Report")
        
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
            headers = [_('Activity Code'), _('Activity Name'), _('Funds Source'), _('Total Hours'), _('Entries')]
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

