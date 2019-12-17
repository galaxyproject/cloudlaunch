import yaml
from django.core.management.base import BaseCommand
from cloudlaunch import models as cl_models

import cloudlaunch.management.commands.serializers as mgmt_serializers


class Command(BaseCommand):
    help = 'Exports Application Data in yaml format'

    def add_arguments(self, parser):
        parser.add_argument('-a', '--applications', nargs='+', type=str,
                            help='Export only the specified applications')

    def handle(self, *args, **options):
        return self.export_app_data(applications=options.get('applications'))

    @staticmethod
    def export_app_data(applications=None):
        if applications:
            queryset = cl_models.Application.objects.filter(pk__in=applications)
        else:
            queryset = cl_models.Application.objects.all()

        serializer = mgmt_serializers.ApplicationSerializer(queryset, many=True)
        data = serializer.to_representation(serializer.instance)
        return yaml.safe_dump(data, default_flow_style=False)
