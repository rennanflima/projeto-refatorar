# Generated by Django 2.2.4 on 2019-09-19 16:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_auto_20190904_1117'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentoprocesso',
            name='tipo_documento',
            field=models.CharField(choices=[('SOLICITACAO', 'Solicitação'), ('PARECER', 'Parecer'), ('DESPACHO', 'Despacho')], default='PARECER', max_length=20, verbose_name='Tipo do documento'),
        ),
    ]
