# Generated by Django 2.1.7 on 2019-08-19 20:01

import ckeditor.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_unidadefluxoprocesso_is_avaliadora'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tramite',
            name='despacho',
            field=ckeditor.fields.RichTextField(blank=True, null=True, verbose_name='Despacho'),
        ),
    ]
