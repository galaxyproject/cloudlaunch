from django.contrib.auth.models import User, Group
from rest_framework import serializers

from .models import Application, AWSEC2, Category


class ApplicationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Application
        fields = ('id', 'url', 'name', 'version', 'description', 'info_url',
                  'categories', 'launch_data')


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'name')


class AWSEC2Serializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AWSEC2
        fields = ('url', 'name')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')
