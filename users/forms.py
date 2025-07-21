from django import forms
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
# ,UserCreationForm
from .models import CustomUser
from django.contrib.auth import get_user_model  # why this here?
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import SignupForm

User = get_user_model()  # why this?


class CustomSignupForm(SignupForm):

    def save(self, request):

        # Ensure you call the parent class's save.
        # .save() returns a User object.
        user = super(CustomSignupForm, self).save(request)

        # Add your own processing here.

        # You must return the original result.
        return user


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


# ==============password change form=============
class PasswordChangeForm(PasswordChangeForm):
    pass


# ==============profile edit form=============
class ProfileChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['bio', 'avatar', 'resume']

        def __init__(self, *args, **kwargs):
            user = kwargs.pop('user', None)
            super().__init__(*args, **kwargs)

            if user:
                self.fields['avatar'].initial = user.customuser.avatar
                self.fields['bio'].initial = user.customuser.bio
                self.fields['resume'].initial = user.customuser.resume

            # Apply Bootstrap classes and custom styles to form fields
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

        bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), required=False)  # Define bio with Textarea widget
