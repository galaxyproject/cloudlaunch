import rest_framework.authentication
 
from .models import AuthToken


# Override drf.authtoken's default create token and add a default token name.
# This requires the following setting:
# REST_AUTH_TOKEN_CREATOR = 'cloudlaunch.authentication.default_create_token'
def default_create_token(token_model, user, serializer):
    token, _ = token_model.objects.get_or_create(user=user, name="default")
    return token
 
 
# This is linked in from settings.py through DEFAULT_AUTHENTICATION_CLASSES
# and will override DRF's default token auth.
# Also requires setting REST_AUTH_TOKEN_MODEL = 'cloudlaunch.models.AuthToken'
class TokenAuthentication(rest_framework.authentication.TokenAuthentication):
    model = AuthToken
