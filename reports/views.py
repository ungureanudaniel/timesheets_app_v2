from django.shortcuts import render


def report(request):
    template = "timesheet/report.html"

    context = {}
    return render(request, template, context)
