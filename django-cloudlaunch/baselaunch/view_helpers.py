from djcloudbridge import view_helpers as cb_view_helpers
from djcloudbridge import domain_model
from baselaunch import models

import json

def get_cloud_provider(view, cloud_id=None):
    """
    Returns a cloud provider for the current user. The relevant
    cloud is discovered from the view and the credentials are retrieved
    from the request or user profile. Return ``None`` if no credentials were
    retrieved.
    """
    return cb_view_helpers.get_cloud_provider(view, cloud_id)
