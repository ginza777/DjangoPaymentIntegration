import base64
import binascii

from rest_framework import HTTP_HEADER_ENCODING
from rest_framework.authentication import get_authorization_header

from django.conf import settings

AUTH_ERROR = {
    "error": {
        "code": -32504,
        "message": {"ru": "пользователь не существует", "uz": "foydalanuvchi mavjud emas", "en": "user does not exist"},
        "data": "user does not exist",
    }
}


def authentication(request):
    """
    Returns a `User` if a correct username and password have been supplied
    using HTTP Basic authentication.  Otherwise returns `None`.
    """
    auth = get_authorization_header(request).split()

    if not auth or auth[0].lower() != b"basic":
        return False

    if len(auth) == 1:
        return False
    elif len(auth) > 2:
        return False

    try:
        auth_parts = base64.b64decode(auth[1]).decode(HTTP_HEADER_ENCODING).partition(":")
    except (TypeError, UnicodeDecodeError, binascii.Error):
        return False

    userid, password = auth_parts[0], auth_parts[2]
    return userid == "Paycom" and (
        password == settings.PROVIDERS["payme"]["secret_key"]
        or password == settings.PROVIDERS["payme"]["test_secret_key"]
    )
