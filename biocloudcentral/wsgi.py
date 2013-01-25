import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "biocloudcentral.settings")

# This application object is used by the development server
# as well as any WSGI server configured to use this file.
from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()

## Replace with this application definition to expose more logging.
#from paste.exceptions.errormiddleware import ErrorMiddleware
#application = ErrorMiddleware(WSGIHandler(), debug=True)
