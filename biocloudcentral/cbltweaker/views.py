"""
Views for the CBL tweaker app
"""
from django.shortcuts import render
from django.template import RequestContext

import logging
log = logging.getLogger(__name__)


def home(request):
    """
    Home page for the 'CBL tweaker' app
    """
    return render(request, "cbltweaker/index.html", {"form": "todo"},
        context_instance=RequestContext(request))
