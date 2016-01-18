from abc import ABCMeta, abstractmethod

from cloudbridge.cloud.interfaces.resources import CloudResource
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import NoReverseMatch
from django.http.response import Http404
from rest_framework import mixins
from rest_framework import relations
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response

from baselaunch import util
from baselaunch import view_helpers


# -----------------------------------
# Django Rest Framework View Helpers
# -----------------------------------
class CustomNonModelObjectMixin(object):
    """
    A custom viewset mixin to make it easier to work with non-django-model viewsets.
    Only the list_objects() and retrieve_object() methods need to be implemented.
    Create and update methods will work normally through DRF's serializers.
    """
    __metaclass__ = ABCMeta

    def get_queryset(self):
        return self.list_objects()

    def get_object(self):
        obj = self.retrieve_object()
        if obj is None:
            raise Http404

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

    @abstractmethod
    def list_objects(self):
        """
        Override this method to return the list of objects for
        list() methods.
        """
        pass

    @abstractmethod
    def retrieve_object(self):
        """
        Override this method to return the object for the get method.
        If the returned object is None, an HTTP404 will be raised.
        """
        pass


class CustomModelViewSet(CustomNonModelObjectMixin, viewsets.ModelViewSet):
    pass


class CustomReadOnlyModelViewSet(CustomNonModelObjectMixin,
                                 viewsets.ReadOnlyModelViewSet):
    pass


class CustomReadOnlySingleViewSet(CustomNonModelObjectMixin,
                                  mixins.ListModelMixin,
                                  viewsets.GenericViewSet):

    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_object(self):
        # return an empty data row so that the serializer can emit fields
        return {}

# --------------------------------------------
# Django Rest Framework Serialization Helpers
# --------------------------------------------


class CustomHyperlinkedRelatedField(relations.HyperlinkedRelatedField):
    """
    This custom hyperlink field builds up the arguments required to link to a
    nested view of arbitrary depth, provided the ``parent_url_kwargs`` parameter
    is passed in. This parameter must contain a list of ``kwarg`` names that are
    required for django's ``reverse()`` to work. The values for each argument
    are obtained from the serializer context. It's modelled after drf-nested-
    routers' ``NestedHyperlinkedRelatedField``.
    """
    lookup_field = 'pk'

    def __init__(self, *args, **kwargs):
        self.parent_url_kwargs = kwargs.pop('parent_url_kwargs', [])
        super(CustomHyperlinkedRelatedField, self).__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.
        May raise a ``NoReverseMatch`` if the ``view_name`` and ``lookup_field``
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, 'pk') and obj.pk is None:
            return None

        reverse_kwargs = {}
        # Use kwargs from view if available. When using the serializer
        # manually, a view may not be available. If so, the required
        # args must be supplied through the serializer context
        if 'view' in self.context:
            reverse_kwargs = {key: val for key, val in self.context['view'].kwargs.items()
                              if key in self.parent_url_kwargs}
        # Let serializer context values override view kwargs
        reverse_kwargs.update({key: val for key, val in self.context.items()
                               if key in self.parent_url_kwargs})
        lookup_value = util.getattrd(obj, self.lookup_field)
        if lookup_value:
            reverse_kwargs.update({self.lookup_url_kwarg: lookup_value})
        try:
            return self.reverse(
                view_name, kwargs=reverse_kwargs, request=request, format=format)
        except NoReverseMatch as e:
            # If the reverse() failed when the lookup_value is empty, just
            # ignore, since it's probably a null value in the dataset
            if lookup_value:
                raise e
            return ""


class CustomHyperlinkedIdentityField(CustomHyperlinkedRelatedField):
    """
    A version of the ``CustomHyperlinkedRelatedField`` dedicated to creating
    identity links. It's simply copied from rest framework's
    ``relations.HyperlinkedRelatedField``.
    """
    lookup_field = 'pk'

    def __init__(self, *args, **kwargs):
        kwargs['read_only'] = True
        # The asterisk is a special value that DRF has an interpretation
        # for: It will result in the source being set to the current object.
        # itself. (Usually, the source is a field of the current object being
        # serialized)
        kwargs['source'] = '*'
        super(CustomHyperlinkedIdentityField, self).__init__(*args, **kwargs)


class ProviderFieldMixin(object):
    """
    A mixin class for handling related fields in django rest framework for
    cloudbridge providers.
    It works in a similar way to default DRF RelatedFields, except that the
    queryset must be a provider service instead of a django queryset. It is
    assumed that the service supports list() and get() methods. If not, this
    class can be subclassed and custom implementations provided for the
    get_queryset() and get_object() methods.
    For example:
        snapshot_id = ProviderHyperlinkRelatedField(
                        view_name='snapshot-detail',
                        lookup_field='id',
                        lookup_url_kwarg='pk',
                        parent_url_kwargs=['cloud_pk'],
                        queryset='block_store.snapshots',
                        display_fields=[
                            'name', 'id', 'size'],
                        display_format="{0} (ID: {1}, Size: {2} GB)",
                        write_only=True)

    In the example above, the queryset points to the provider property
    block_store.snapshots().
    This will result in the list of values to display in the drop down being
    obtained as follows:
        provider.<queryset>.list()
    When an individual object is selected from the list, it will be
    retrieved by calling:
        provider.<queryset>.get(lookup_field)

    All other fields work the same way as `
    """

    def __init__(self, *args, **kwargs):
        """
        Same behaviour as ``RelatedField`` except that
        querysets have a different meaning.

        :type queryset: str
        :param queryset: The provider service to use for listing objects.

        :type display_fields: str
        :param display_fields: Which property's in the object to use when
                               formatting the display string.

        :type display_format: str
        :param display_format: The format string to use when displaying the
                               objects. ``display_fields`` will be used to
                               provide parameters.
        """
        self.display_fields = kwargs.pop('display_fields', [])
        self.display_format = kwargs.pop('display_format', None)
        super(ProviderFieldMixin, self).__init__(*args, **kwargs)

    def get_queryset(self):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        list_method = util.getattrd(
            provider, self.queryset + '.list')
        if list_method:
            return list_method()
        else:
            return util.getattrd(
                provider, self.queryset)

    def get_provider_object(self, pk):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        obj = util.getattrd(
            provider, self.queryset + '.get')(pk)
        if obj:
            return obj
        else:
            return ObjectDoesNotExist()

    def display_value(self, instance):
        """
        Format the instance using the provided display_format
        and display_fields strings. If not specified, will revert
        to default DRF behaviour, which is to provide str(object)

        (Will be rendered in html by DRF as:
        <option value='$to_representation(instance)'>#display_value(instance)
        </option>).
        """
        if self.display_fields and self.display_format:
            display_values = [util.getattrd(instance, field)
                              for field in self.display_fields]
            return self.display_format.format(*display_values)
        else:
            return super(
                ProviderFieldMixin, self).display_value(instance)


class ProviderHyperlinkRelatedField(
        ProviderFieldMixin, CustomHyperlinkedRelatedField):
    """
    A HyperLink related field for provider objects. Behaves
    very similarly to a DRF HyperlinkedRelatedField, except
    that it works for provider objects instead of querysets.
    Usage example:
    snapshot_id = ProviderHyperlinkRelatedField(
                    view_name='snapshot-detail',
                    lookup_field='id',
                    lookup_url_kwarg='pk',
                    parent_url_kwargs=['cloud_pk'],
                    queryset='block_store.snapshots',
                    display_fields=[
                        'name', 'id', 'size'],
                    display_format="{0} (ID: {1}, Size: {2} GB)",
                    write_only=True)
    """

    def get_object(self, view_name, view_args, view_kwargs):
        """
        Return the object corresponding to a matched URL.

        Takes the matched URL conf arguments, and should return an
        object instance, or raise an `ObjectDoesNotExist` exception.

        Calls the ProviderFieldMixin's get_provider_object to retrieve
        the object by pk.
        """
        lookup_value = view_kwargs[self.lookup_url_kwarg]
        return self.get_provider_object(lookup_value)


class ProviderPKRelatedField(
        ProviderFieldMixin, serializers.PrimaryKeyRelatedField):
    """
    A Primary Key related field for provider objects. Behaves
    very similarly to a DRF PrimaryKeyRelatedField, except
    that it works for provider objects instead of querysets.
    Usage example:
    snapshot_id = ProviderPKRelatedField(label="Snapshot ID",
                                         queryset='block_store.snapshots',
                                         display_fields=[
                                             'name', 'id', 'size'],
                                         display_format="{0} (ID: {1},"
                                         " Size: {2} GB)",
                                         write_only=True,
                                         required=False,
                                         allow_null=True)
    """

    def to_internal_value(self, data):
        """
        Return the object corresponding to a matched
        primary key.
        """
        return self.get_provider_object(data)

    def to_representation(self, value):
        """
        Returns the primary key value of the object.
        (Will be rendered in html by DRF as:
        <option value='$to_representation(instance)'>#display_value(instance)
        </option>).
        """
        if isinstance(value, CloudResource):
            return value.id
        else:
            return value
