from django.views.generic import FormView, TemplateView
from django.db.models import Sum, Count
from django.utils import timezone
from django.urls import reverse_lazy
from timesheet.models import Timesheet
from .forms import ReportPeriodForm
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO
import openpyxl

class ReportGeneratorView(LoginRequiredMixin, FormView):
    template_name = 'reports/generate_report.html'
    form_class = ReportPeriodForm
    success_url = reverse_lazy('report_results')

    def form_valid(self, form):
        period = form.cleaned_data['period']
        report_type = form.cleaned_data['report_type']
        
        # Calculate date range
        today = timezone.now().date()
        if period == 'weekly':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        else:  # monthly
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Store in session for results view
        self.request.session['report_data'] = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'report_type': report_type,
            'user_id': self.request.user.id
        }
        return super().form_valid(form)

class ReportResultsView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/report_results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_data = self.request.session.get('report_data', {})
        
        # Get timesheets for period
        timesheets = Timesheet.objects.filter(
            user_id=report_data.get('user_id'),
            date__gte=report_data.get('start_date'),
            date__lte=report_data.get('end_date'),
            submitted=True
        )
        
        # Generate report data
        if report_data.get('report_type') == 'summary':
            context['report'] = self._generate_summary_report(timesheets)
        else:
            context['report'] = self._generate_detailed_report(timesheets)
        
        context['period'] = report_data.get('period', 'weekly')
        context['start_date'] = report_data.get('start_date')
        context['end_date'] = report_data.get('end_date')
        return context
    
    def _generate_summary_report(self, timesheets):
        return timesheets.values(
            'activity__code',
            'activity__name',
            'fundssource__name'
        ).annotate(
            total_hours=Sum('hours_worked'),
            entries=Count('id')
        ).order_by('activity__code')
    
    def _generate_detailed_report(self, timesheets):
        return timesheets.select_related(
            'activity', 'fundssource'
        ).order_by('date')

    def export_pdf(self):
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        
        # Draw report content
        p.drawString(100, 800, "Work Activity Report")
        # ... more PDF generation code ...
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')

    def export_excel(self):
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="report.xlsx"'
        
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Add report data
        ws.append(['Activity Code', 'Activity Name', 'Total Hours'])
        # ... more Excel generation code ...
        
        wb.save(response)
        return response
