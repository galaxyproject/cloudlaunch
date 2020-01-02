import argparse
import requests
import yaml

from django.core.management.base import BaseCommand

import cloudlaunch.management.commands.serializers as mgmt_serializers


class Command(BaseCommand):
    help = 'Imports Application Data from a given url or file and updates' \
           ' existing models'

    def file_from_url(url):
        """
        Reads a file from a url
        :return: content of file
        """
        try:
            r = requests.get(url)
            r.raise_for_status()
            return r.text
        except requests.exceptions.RequestException as e:
            raise argparse.ArgumentTypeError(e)

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-f', '--file', type=argparse.FileType('r'))
        group.add_argument('-u', '--url', type=Command.file_from_url)

    def handle(self, *args, **options):
        if options['file']:
            content = options['file'].read()
        else:
            content = options['url']

        registry = yaml.safe_load(content)
        return self.import_app_data(registry.get('apps'))

    @staticmethod
    def import_app_data(yaml_data):
        serializer = mgmt_serializers.ApplicationSerializer(
            data=yaml_data, many=True)
        if serializer.is_valid():
            serializer.save()
        else:
            return str(serializer.errors)
