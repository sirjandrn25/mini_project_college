# Generated by Django 3.2 on 2021-05-10 16:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mechanic',
            name='running',
            field=models.BooleanField(default=False),
        ),
    ]
