# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-03-30 12:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0036_set_default_xslt'),
        ('portico', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Delivered',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sent_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='journal.Issue')),
            ],
        ),
        migrations.RemoveField(
            model_name='company',
            name='logo',
        ),
        migrations.DeleteModel(
            name='Company',
        ),
        migrations.DeleteModel(
            name='File',
        ),
    ]
