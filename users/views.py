from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.views import generic
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.decorators import method_decorator
from .forms import CustomLoginForm, ProfileChangeForm, CustomUserCreationForm, UsernameEmailChangeForm
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib import messages
from .models import *
from axes.decorators import axes_dispatch


# Function to check if the user is admin
def is_admin(user):
    return user.is_staff or user.is_superuser


# Protect the admin dashboard view
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Your logic for the admin dashboard
    return render(request, 'dashboard')

# ==============user list============
class UserListView(generic.ListView):
    template = "accounts/user_management.html"

    model = CustomUser
    paginate_by = 1

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["users"] = CustomUser.objects.all()
        return context


# ==============user registration view============
class CustomSignupView(SuccessMessageMixin, generic.CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_message = "Your account has been created! Please wait for administrator approval. You will receive an email once your account is approved."
    success_url = reverse_lazy('users:login')

    def get_success_url(self):
        return reverse_lazy('users:login')


class CustomLoginView(SuccessMessageMixin, LoginView):
    template_name = 'accounts/login.html'
    success_message = "Welcome back!"
    form_class = CustomLoginForm
    # This decorator helps Axes track login attempts
    @method_decorator(axes_dispatch)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse_lazy('users:profile')
    
    def form_valid(self, form):
        # Axes will automatically track successful logins
        response = super().form_valid(form)
        return response


# ============== user logout view ==============
class CustomLogoutView(LogoutView):
    next_page = 'home'
    
    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            
            # Instead of error, redirect to a confirmation page or home
            messages.info(request, "Vă rugăm să folosiți butonul de logout pentru a vă deconecta.")
            return redirect('home')
            
        messages.success(request, "Ați fost deconectat cu succes.")
        return super().dispatch(request, *args, **kwargs)


class ProfileEditView(LoginRequiredMixin, generic.UpdateView):
    model = CustomUser
    form_class = ProfileChangeForm
    template_name = 'accounts/profile_edit.html'

    def get_success_url(self):
        # Redirect to the profile page of the current user after successful update
        return reverse('users:profile')

    def get_object(self):
        # Retrieve the current user object
        return self.request.user


class CredentialsEditView(LoginRequiredMixin, generic.UpdateView):
    model = CustomUser
    form_class = UsernameEmailChangeForm
    template_name = 'accounts/credentials_change.html'

    def get_success_url(self):
        # Redirect to the profile page of the current user after successful update
        return reverse('users:profile')

    def get_object(self):
        # Retrieve the current user object
        return self.request.user


# ==============user credentials change view=====================
@login_required
def user_change_view(request, pk):
    # Fetch the user instance
    user = get_object_or_404(CustomUser, pk==request.user.pk)
    if request.method == 'POST':
        user_form = UsernameEmailChangeForm(request.POST, instance=request.user)

        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Your credentials have been successfully updated.')
            return redirect('users:profile', pk=request.user.pk)
    else:
        user_form = UsernameEmailChangeForm(instance=request.user)

    return render(request, 'accounts/credentials_change.html', {'form': user_form, 'user': user})


class CustomPasswordChangeView(SuccessMessageMixin, LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_reset.html'
    success_message = "Password changed successfully!"
    
    def get_success_url(self):
        # Redirect to the user's profile after password change
        return reverse_lazy('users:profile')

# @login_required
# def password_change_view(request, username):
#     # Fetch the user instance
#     user = get_object_or_404(User, username=username)

#     if request.method == 'POST':
#         password_form = PasswordChangeForm(user=request.user, data=request.POST)

#         if password_form.is_valid():
#             user = password_form.save()
#             update_session_auth_hash(request, user)  # Important for keeping the user logged in

#             messages.success(request, 'Your password has been successfully updated.')
#             return redirect('users:profile', username=request.user.username)
#     else:
#         form = PasswordChangeForm(user=request.user)
#     return render(request, 'accounts/password_change.html', {'form': form, 'user': user})

class ProfileView(LoginRequiredMixin, generic.DetailView):
    model = CustomUser
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        return self.request.user
    
    def get_template_names(self):
        print(f"Looking for template: {self.template_name}")
        return [self.template_name]