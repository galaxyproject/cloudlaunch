from django.contrib.auth.models import User, Group
from rest_framework import viewsets

from .models import Application, AWSEC2, Category
from .serializers import ApplicationSerializer
from .serializers import AWSEC2Serializer
from .serializers import CategorySerializer
from .serializers import GroupSerializer
from .serializers import UserSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class AWSEC2ViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows AWS EC2 cloud info to be viewed or edited.
    """
    queryset = AWSEC2.objects.all()
    serializer_class = AWSEC2Serializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
