from django.http import HttpResponse
from django_filters import rest_framework as dj_filters
from rest_framework import authentication
from rest_framework import filters
from rest_framework import generics
from rest_framework import mixins
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
import requests

from djcloudbridge import drf_helpers
from . import models
from . import serializers
from . import view_helpers


class CustomApplicationPagination(PageNumberPagination):
    page_size_query_param = 'page_size'

class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = models.Application.objects.filter(status=models.Application.LIVE)
    serializer_class = serializers.ApplicationSerializer
    filter_backends = (filters.OrderingFilter, filters.SearchFilter)
    search_fields = ('slug',)
    ordering = ('display_order',)
    pagination_class = CustomApplicationPagination


class InfrastructureView(APIView):
    """
    List kinds in infrastructures.
    """

    def get(self, request, format=None):
        # We only support cloud infrastructures for the time being
        response = {'url': request.build_absolute_uri('clouds')}
        return Response(response)


class AuthView(APIView):
    """
    List authentication endpoints.
    """

    def get(self, request, format=None):
        data = {
            'login': request.build_absolute_uri(
                reverse('rest_auth:rest_login')),
            'logout': request.build_absolute_uri(
                reverse('rest_auth:rest_logout')),
            'user': request.build_absolute_uri(
                reverse('rest_auth:rest_user_details')),
            'registration': request.build_absolute_uri(
                reverse('rest_auth_reg:rest_register')),
            'password/reset': request.build_absolute_uri(
                reverse('rest_auth:rest_password_reset')),
            'password/reset/confirm': request.build_absolute_uri(
                reverse('rest_auth:rest_password_reset_confirm')),
            'password/reset/change': request.build_absolute_uri(
                reverse('rest_auth:rest_password_change')),
        }
        return Response(data)


class AuthTokenView(APIView):
    """
    Return an auth token for a user that is already logged in.
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (authentication.SessionAuthentication,)

    def get(self, request, format=None):
        try:
            token = Token.objects.get(user=request.user)
            return Response({'token': token.key})
        except Token.DoesNotExist:
            return Response({'token': None})

    def post(self, request, format=None):
        token = Token.objects.get_or_create(user=request.user)
        return Response({'token': token.key})


class CorsProxyView(APIView):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    exclude_from_schema = True

    def get(self, request, format=None):
        url = self.request.query_params.get('url')
        response = requests.get(url)
        return HttpResponse(response.text, status=response.status_code,
                    content_type=response.headers.get('content-type'))


class CloudManViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List CloudMan related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.CloudManSerializer


class DeploymentViewSet(viewsets.ModelViewSet):
    """
    List compute related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DeploymentSerializer
    filter_backends = (filters.OrderingFilter, dj_filters.DjangoFilterBackend)
    ordering = ('-added',)
    filter_fields = ('archived',)

    def get_queryset(self):
        """
        This view should return a list of all the deployments
        for the currently authenticated user.
        """
        user = self.request.user
        return models.ApplicationDeployment.objects.filter(owner=user)


class DeploymentTaskViewSet(viewsets.ModelViewSet):
    """List tasks associated with a deployment."""
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DeploymentTaskSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering = ('-updated',)

    def get_queryset(self):
        """
        This view should return a list of all the tasks
        for the currently associated task.
        """
        deployment = self.kwargs.get('deployment_pk')
        user = self.request.user
        return models.ApplicationDeploymentTask.objects.filter(
            deployment=deployment, deployment__owner=user)


class PublicKeyList(generics.ListCreateAPIView):
    """List public ssh keys associated with the user profile."""

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.PublicKeySerializer

    def get_queryset(self):
        c.incr('user.list.public.keys')
        return models.PublicKey.objects.filter(
            user_profile__user=self.request.user)


class PublicKeyDetail(generics.RetrieveUpdateDestroyAPIView):
    """Get a single public ssh keys associated with the user profile."""

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.PublicKeySerializer

    def get_queryset(self):
        return models.PublicKey.objects.filter(
            user_profile__user=self.request.user)
