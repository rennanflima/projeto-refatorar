# Generated by Django 2.2.4 on 2019-08-28 16:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_auto_20190828_1102'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tramite',
            name='data_despacho',
        ),
        migrations.RemoveField(
            model_name='tramite',
            name='despacho',
        ),
        migrations.RemoveField(
            model_name='tramite',
            name='tipo_despacho',
        ),
        migrations.AlterField(
            model_name='documentoprocesso',
            name='tipo_documento',
            field=models.CharField(choices=[('SOLICITACAO', 'Solicitação'), ('PARECER', 'Parecer'), ('DESPACHO', 'Despacho')], default='PARECER', max_length=10, verbose_name='Tipo do documento'),
        ),
    ]
