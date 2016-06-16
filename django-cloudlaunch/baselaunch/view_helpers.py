from baselaunch import domain_model
from baselaunch import models


def get_cloud_provider(view, cloud_id = None):
    """
    Returns a cloud provider for the current user. The relevant
    cloud is discovered from the view and the credentials are retrieved
    from the request or user profile. Return ``None`` if no credentials were
    retrieved.
    """
    cloud_pk = cloud_id or view.kwargs.get("cloud_pk")
    cloud = models.Cloud.objects.filter(
        slug=cloud_pk).select_subclasses().first()

    request_creds = get_credentials(cloud, view.request)
    return domain_model.get_cloud_provider(cloud, request_creds)


def get_credentials(cloud, request):
    """
    Returns a dictionary containing the current user's credentials for a given
    cloud. An attempt will be made to retrieve the credentials from the request
    first, followed by the user's profile.
    """
    request_creds = get_credentials_from_request(cloud, request)
    if request_creds:
        return request_creds
    else:
        return get_credentials_from_profile(cloud, request)


def get_credentials_from_request(cloud, request):
    """
    Extracts and returns the credentials from the current request for a given
    cloud. Returns an empty dict if not available.
    """
    if isinstance(cloud, models.OpenStack):
        os_username = request.META.get('HTTP_CL_OS_USERNAME')
        os_password = request.META.get('HTTP_CL_OS_PASSWORD')
        os_tenant_name = request.META.get('HTTP_CL_OS_TENANT_NAME')
        os_project_name = request.META.get('HTTP_CL_OS_PROJECT_NAME')
        os_project_domain_name = request.META.get(
            'HTTP_CL_OS_PROJECT_TENANT_NAME')
        os_user_domain_name = request.META.get('HTTP_CL_OS_USER_DOMAIN_NAME')
        os_identity_api_version = request.META.get(
            'HTTP_CL_OS_IDENTITY_API_VERSION')
        d = {}
        if os_username and os_password:
            d = {'os_username': os_username, 'os_password': os_password}
            if os_tenant_name:
                d['os_tenant_name'] = os_tenant_name
            if os_project_name:
                d['os_project_name'] = os_project_name
            if os_project_domain_name:
                d['os_project_domain_name'] = os_project_domain_name
            if os_user_domain_name:
                d['os_user_domain_name'] = os_user_domain_name
            if os_identity_api_version:
                d['os_identity_api_version'] = os_identity_api_version
        return d
    elif isinstance(cloud, models.AWS):
        aws_access_key = request.META.get('HTTP_CL_AWS_ACCESS_KEY')
        aws_secret_key = request.META.get('HTTP_CL_AWS_SECRET_KEY')
        if aws_access_key and aws_secret_key:
            return {'aws_access_key': aws_access_key,
                    'aws_secret_key': aws_secret_key,
                    }
        else:
            return {}
    else:
        raise Exception("Unrecognised cloud provider: %s" % cloud)


def get_credentials_from_profile(cloud, request):
    """
    Returns the stored database credentials for a given cloud for the currently
    logged in user. If the user is not logged in or no credentials are found,
    return an empty dict.

    .. note:: If no credentials are found but the server has environment
    variables required by Cloudbridge available, those credentials will
    be used!
    """
    if request.user.is_anonymous():
        return {}
    profile = request.user.userprofile
    # Check for default credentials
    credentials = profile.credentials.filter(cloud=cloud, default=True). \
        select_subclasses().first()
    if credentials:
        return credentials.as_dict()
    # Check for a set of credentials for the given cloud
    credentials = profile.credentials.filter(cloud=cloud).select_subclasses()
    if not credentials:
        return {}
    if credentials.count() == 1:
        return credentials[0].as_dict()
    else:
        raise ValueError("Too many credentials to choose from.")
