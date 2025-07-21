from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.views import generic
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from .forms import UsernameEmailChangeForm
from django.urls import reverse
from .forms import ProfileChangeForm
# ,CustomSignupForm
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib import messages
from .models import *
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from allauth.account.views import SignupView


# Function to check if the user is admin
def is_admin(user):
    return user.is_staff or user.is_superuser


# Protect the admin dashboard view
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Your logic for the admin dashboard
    return render(request, 'admin/dashboard.html')


# ==============user list============
class AnalyticsView(generic.ListView):
    template = "dashboard/analytics.html"

    queryset = CustomUser.objects.all()
    paginate_by = 20

    def get(self, request, **kwargs):
        # get each individual userprofile
        user_profile = self.request.user.customuser
        print(user_profile) 


# ==============user list============
class UserListView(generic.ListView):
    template = "account/user_management.html"

    model = CustomUser
    paginate_by = 1

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["users"] = CustomUser.objects.all()
        return context


# ==============user registration view============
class CustomSignupView(SignupView):
    template = 'account/signup.html'

    def form_valid(self, form):
        # Call the original form_valid method
        response = super().form_valid(form)

        # Get the user and assign them to a default group
        user = form.save(self.request)
        group = Group.objects.get(name='REPORTER')
        user.groups.add(group)
        user.save()

        return response


# def register(request):
#     if request.method == 'POST':
#         form = CustomSignupForm(request.POST)  # access the registration form
#         try:
#             if form.is_valid():
#                 # fetch username and email from form
#                 username = form.cleaned_data['username']
#                 email = form.cleaned_data['email']
#                 # Check if user already exists
#                 try:
#                     if User.objects.filter(username=username).exists():
#                         messages.error(request, 'Username already exists. Please choose a different username.')
#                     elif User.objects.filter(email=email).exists():
#                         messages.error(request, 'Email address already exists. Please use a different email.')
#                     else:
#                         # If the username and email are unique, save the user and create a profile
#                         with transaction.atomic():
#                             user = form.save(commit=False)
#                             user.is_active = False  # to keep the account inactive until approved manually by admins
#                             user.save()

#                         # Notify admins and supervisors via email
#                         subject = 'New User Access Request'
#                         html_message = render_to_string('registration/registration_notice_email.html', {
#                             'username': user.username,
#                             'email': user.email,
#                         })
#                         plain_message = strip_tags(html_message)
#                         admins = User.objects.filter(groups__name='ADMIN').values_list('email', flat=True)
#                         supervisors = User.objects.filter(groups__name='SUPERVISOR').values_list('email', flat=True)

#                         recipients = list(admins) + list(supervisors)

#                         send_mail(
#                             subject,
#                             plain_message,
#                             settings.EMAIL_HOST_USER,  # Sender's email address
#                             recipients,
#                             html_message=html_message,
#                         )

#                         # success message
#                         messages.warning(request, 'Registration successful. Your account is pending admin approval.')

#                         # redirect the user to login into the profile page with newly created credentials, but with an inactive account
#                         return render(request, 'registration/profile.html')
#                 except Exception as e:
#                     print(f'Error: {e}')
#             else:
#                 # If form is invalid, print form errors to the console (optional) and display messages
#                 for field, errors in form.errors.items():
#                     for error in errors:
#                         messages.error(request, f"{field}: {error}")
#         except Exception as e:
#             messages.error(request, e)
#     else:
#         form = CustomSignupForm()

#     return render(request, 'registration/register.html', {'form': form})


# ==============user login view==============
class CustomLoginView(LoginView):
    template_name = 'account/login.html'  # The path to your custom login template
    authentication_form = AuthenticationForm  # Use Django's default AuthenticationForm
    redirect_authenticated_user = True  # Redirect user if already authenticated
    success_url = reverse_lazy('timesheets:dashboard')  # Redirect after login

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().username}!")  # Display a success message on successful login
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)

# ============== user logout view ==============
class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        messages.success(request, "You have been successfully logged out.")
        return response
# ============user profile editing====================
# @login_required
# def profile_edit_view(request, username):
#     template_name = 'registration/profile_updater.html'
#     # Fetch the user instance
#     user = get_object_or_404(User, username=username)

#     # Fetch or create UserProfile instance for the user

#     user_profile, created = CustomUser.objects.get_or_create(user=user)

#     if request.method == 'POST':
#         form = ProfileChangeForm(request.POST, request.FILES, instance=user_profile)
#         if form.is_valid():
#             # form.save(commit=False)
#             form.save()
#             return redirect('profile', username=username)
#     else:
#         form = ProfileChangeForm(instance=user_profile)

#     context = {
#         'user':user,
#         'avatar_url': user_profile.avatar.url if user_profile.avatar else None,
#         'form': form,}

#     return render(request, template_name, context)


class ProfileEditView(LoginRequiredMixin, generic.UpdateView):
    model = CustomUser
    form_class = ProfileChangeForm
    template_name = 'account/profile_edit.html'

    def get_success_url(self):
        # Redirect to the profile page of the current user after successful update
        return reverse('profile', kwargs={'username': self.request.user.username})

    def get_object(self):
        # Retrieve the current user object
        return self.request.user


# ==============user credentials change view=====================
@login_required
def user_change_view(request, username):
    # Fetch the user instance
    user = get_object_or_404(CustomUser, username=username)
    if request.method == 'POST':
        user_form = UsernameEmailChangeForm(request.POST, instance=request.user)

        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Your credentials have been successfully updated.')
            return redirect('profile', username=request.user.username)
    else:
        user_form = UsernameEmailChangeForm(instance=request.user)

    return render(request, 'account/credentials_change.html', {'form': user_form, 'user': user})


@login_required
def password_change_view(request, username):
    # Fetch the user instance
    user = get_object_or_404(User, username=username)

    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)

        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Important for keeping the user logged in

            messages.success(request, 'Your password has been successfully updated.')
            return redirect('profile', username=request.user.username)
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'account/password_change.html', {'form': form, 'user': user})

class ProfileView(LoginRequiredMixin, generic.DetailView):
    model = CustomUser
    template_name = 'account/profile.html'

    def get_object(self):
        # Retrieve the current user object
        return self.request.user