# Generated by Django 2.2.4 on 2019-08-28 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_auto_20190827_1452'),
    ]

    operations = [
        migrations.AddField(
            model_name='tramite',
            name='is_rascunho',
            field=models.BooleanField(default=False, verbose_name='Tramitação rascunho'),
        ),
    ]
