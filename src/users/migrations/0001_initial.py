# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-11-16 21:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UserPermissions',
            fields=[
                ('id', models.AutoField(auto_created=True,
                                        primary_key=True,
                                        serialize=False,
                                        verbose_name='ID')),
            ],
            options={
                'permissions': (('can_delete_user', 'Can delete Users'),
                                ('can_edit_user', 'Can edit Users')),
            },
        ),
    ]