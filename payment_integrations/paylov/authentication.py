from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed

from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _


class ServerUser(AnonymousUser):
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class CustomBasicAuthentication(BasicAuthentication):
    _from_settings = False
    _CREDENTIALS = None

    @classmethod
    def from_settings(cls, username, password):
        class _cls(cls):
            _from_settings = True
            _CREDENTIALS = (username, password)

        return _cls

    def authenticate_credentials(self, userid, password, request=None):
        _username, _password = self._CREDENTIALS
        if _username == userid and _password == password:
            return ServerUser(), None
        raise AuthenticationFailed(_("Invalid username/password."))
