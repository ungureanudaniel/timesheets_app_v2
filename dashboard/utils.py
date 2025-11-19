# timesheets/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
import openpyxl
from timesheet.models import Activity  # Adjust to your actual model


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
