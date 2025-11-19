from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm, AuthenticationForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from general import models
from timesheets_main import settings
from .models import CustomUser
from django.contrib.auth import get_user_model  # why this here?
from django.utils.translation import gettext_lazy as _

User = get_user_model()  # why this?


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_('Username or Email'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your username or email'),
            'autofocus': True
        })
    )
    # Password field with Bootstrap styling
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # Initialize the parent class
        self.fields['password'].widget.attrs.update({'class': 'form-control'}) # Add Bootstrap class to password field

    # def clean_username_email(self):
    #     username = self.cleaned_data.get('username')
        
    #     # Check if this email exists in the database
    #     if username:
    #         if not User.objects.filter(
    #             models.Q(username=username) | models.Q(email=username)
    #             ).exists():
    #             raise forms.ValidationError(
    #                 _("This username or email is not registered. Please check your username or email, or sign up for an account."),
    #                 code='usernameor_not_found'
    #             )
    #         return username
    
    # def confirm_login_allowed(self, user):
    #     super().confirm_login_allowed(user)
        
    #     # Add custom checks if needed (e.g., is_approved status)
    #     if not user.is_approved:
    #         raise forms.ValidationError(
    #             _("Your account is pending approval. Please contact an administrator."),
    #             code='account_pending'
    #         )


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email Address")
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = True  # User can login
        user.is_approved = False  # needs admin approval
        if commit:
            user.save()
            user.assign_initial_group()  # Your custom method
            self.send_admin_notification(user)
        return user

    def send_admin_notification(self, user):
        """Send email to admin about new user registration"""
        subject = f'New User Registration: {user.username}'
        
        # Email content for admin
        message = render_to_string('emails/admin_notification.txt', {
            'user': user,
            'admin_url': settings.ADMIN_URL,  # Add this to your settings
        })
        
        # Send to admin email(s) - you can specify multiple
        admin_emails = ['danielungureanu531@gmail.com']  # Change to your admin email
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            admin_emails,
            fail_silently=False,
        )

# ==============user update form=============
class UsernameEmailChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply Bootstrap classes and custom styles to form fields
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control w-100',
            'placeholder': _('Enter first name'),
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control w-100',
            'placeholder': _('Enter last name'),
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control d-flex p-2 bd-highlight',
            'placeholder': _('Enter email'),
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_approved = False  # Set new user as unapproved by default
        if commit:
            user.save()
            user.assign_initial_group()
        return user


# ==============profile edit form=============
class ProfileChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'bio', 'avatar', 'resume']

    bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), required=False)  # Define bio with Textarea widget

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['avatar'].initial = user.avatar
            self.fields['bio'].initial = user.bio
            self.fields['resume'].initial = user.resume

        # Apply Bootstrap classes and custom styles to form fields
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control d-flex p-2 bd-highlight',
            'placeholder': _('Enter first name'),
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control d-flex p-2 bd-highlight',
            'placeholder': _('Enter last name'),
        })
        self.fields['bio'].widget.attrs.update({
            'class': 'form-control d-flex p-2 bd-highlight',
            'placeholder': _('Write a short description of yourself'),
        })
        self.fields['avatar'].widget.attrs.update({
            'class': 'form-control d-flex p-2 bd-highlight',
            'placeholder': _('Attach picture of you'),
        })
        self.fields['resume'].widget.attrs.update({
            'class': 'form-control d-flex p-2 bd-highlight',
            'accept': '.pdf',
            'placeholder': _('Attach a new resume'),
        })

    def save(self, commit=True):
        user_profile = super().save(commit=False)
        if commit:
            user_profile.save()
        return user_profile
