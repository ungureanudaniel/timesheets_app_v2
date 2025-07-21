from allauth.account.auth_backends import AuthenticationBackend as AllAuthAuthenticationBackend
from django.contrib.auth import get_user_model


class AuthenticationBackend(AllAuthAuthenticationBackend):
    """
    Extend the original `allauth` authentication backend to limit user types who can sign in.
    Sign in via team or organization should be forbidden.
    """

    def _authenticate_by_username(self, **credentials):
        user = super()._authenticate_by_username(**credentials)
        if user and user.is_person:  # Allow only users with `is_person=True`
            return user
        return None

    def _authenticate_by_email(self, **credentials):
        user = super()._authenticate_by_email(**credentials)
        if user and user.is_person:  # Allow only users with `is_person=True`
            return user
        return None

    def get_user(self, user_id):
        """
        Override get_user to ensure only valid `Person` users can authenticate.
        """
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
