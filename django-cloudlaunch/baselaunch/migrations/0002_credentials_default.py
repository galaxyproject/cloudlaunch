# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-01-11 17:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baselaunch', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='credentials',
            name='default',
            field=models.BooleanField(default=False, verbose_name='Use as default credentials'),
            preserve_default=False,
        ),
    ]