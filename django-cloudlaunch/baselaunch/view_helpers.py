from rest_framework import status
from rest_framework.response import Response

from baselaunch import domain_model
from baselaunch import models
from baselaunch import util
import serializers


def get_cloud_provider(view):
    """
    Returns a cloud provider for the current user. The relevant
    cloud is discovered from the view and the credentials are retrieved
    from the request or user profile. Return ``None`` if no credentials were
    retrieved.
    """
    cloud_pk = view.kwargs.get("cloud_pk")
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
        os_username = request.META.get('os_username')
        os_password = request.META.get('os_password')
        os_tenant_name = request.META.get('os_tenant_name')
        if os_username and os_password and os_tenant_name:
            return {'os_username': os_username,
                    'os_password': os_password,
                    'os_tenant_name': os_tenant_name
                    }
        else:
            return {}
    elif isinstance(cloud, models.AWS):
        aws_access_key = request.META.get('aws_access_key')
        aws_secret_key = request.META.get('aws_secret_key')
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


def generic_list(view, resource_class_name, serializer_name):
    """
    A template for the ViewSet ``list`` method.

    The method has is generic but fixed in what it does so take a look at the
    implementaion to see if it can be used in the given view.

    :type view: ViewSet
    :param view: The view from where the method is being called.

    :type resource_class_name: str
    :param resource_class_name: A name of the Cloudbridge class for the
                                resources being retrieved. Note that dot
                                notation can be used here
                                (e.g., ``compute.images``).

    :type serializer_name: str
    :param serializer_name: The name of the serializer to use.

    :rtype: Response
    :return: A ``Response`` object with serialized data.
    """
    provider = get_cloud_provider(view)
    serializer = getattr(serializers, serializer_name)(
        instance=util.getattrd(provider, resource_class_name + ".list")(),
        many=True,
        context={'request': view.request,
                 'cloud_pk': view.kwargs.get('cloud_pk'),
                 'list': True})
    return Response(serializer.data)


def generic_retrieve(view, resource_name, resource_class_name, obj_id,
                     serializer_name, cloud_pk):
    """
    A template for the ViewSet ``retrieve`` method to get a single object.

    The method has is generic but fixed in what it does so take a look at the
    implementaion to see if it can be used in the given view.

    :type view: ViewSet
    :param view: The view from where the method is being called.

    :type resource_name: str
    :param resource_name: A name of the resource being retrieved. This will be
                          included in an error message so should be human
                          representation of the resource.

    :type resource_class_name: str
    :param resource_class_name: A name of the Cloudbridge class for the
                                resource being retrieved. Note that dot
                                notation can be used here
                                (e.g., ``compute.images``).

    :type obj_id: str
    :param obj_id: The ID of the object being retrieved.

    :type serializer_name: str
    :param serializer_name: The name of the serializer to use.

    :type cloud_pk: str
    :param cloud_pk: The cloud identifier.

    :rtype: Response
    :return: A ``Response`` object with serialized data or a 400 bad request
             error.
    """
    provider = get_cloud_provider(view)
    instance = util.getattrd(provider, resource_class_name + '.get')(obj_id)
    if not instance:
        return Response({'detail': 'Cannot find {0} {1}'.format(
                         resource_name, obj_id)},
                        status=status.HTTP_400_BAD_REQUEST)
    serializer = getattr(serializers, serializer_name)(
        instance=instance,
        context={'request': view.request, 'cloud_pk': cloud_pk,
                 'list': False})
    return Response(serializer.data)


def generic_create(view, request, serializer_name, cloud_pk):
    """
    A template for the ViewSet ``delete`` method to delete an object.

    The method has is generic but fixed in what it does so take a look at the
    implementaion to see if it can be used in the given view.

    :type view: ViewSet
    :param view: The view from where the method is being called.

    :type request: ``django.http.request``
    :param request: The request object originating the create action.

    :type serializer_name: str
    :param serializer_name: The name of the serializer to use.

    :type cloud_pk: str
    :param cloud_pk: The cloud identifier.

    :rtype: Response
    :return: A ``Response`` object with serialized data and 201 CREATED status
             or a 400 BAD REQUEST error status.
    """
    serializer = getattr(serializers, serializer_name)(
        data=request.data, context={'view': view, 'request': request,
                                    'cloud_pk': cloud_pk})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
