from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from timesheet.forms import TimesheetForm
from timesheet.models import Timesheet, Activity
from django.contrib import messages
from django.utils.translation import gettext_lazy as _


# ==========home page==============
def home(request):
    template = "general/home.html"

    context = {}
    return render(request, template, context)


# ===========contact page==============
def contact(request):
    template = "general/contact.html"

    context = {}
    return render(request, template, context)
