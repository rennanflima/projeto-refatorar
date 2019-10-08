# Generated by Django 2.2.4 on 2019-08-27 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_auto_20190827_0819'),
    ]

    operations = [
        migrations.AddField(
            model_name='tramite',
            name='tipo_despacho',
            field=models.CharField(choices=[('SOLICITACAO', 'Solicitação'), ('PARECER', 'Parecer'), ('DESPACHO', 'Despacho')], default='SOLICITACAO', max_length=10, verbose_name='Tipo do despacho'),
        ),
        migrations.AlterField(
            model_name='registroatividade',
            name='justificativa',
            field=models.TextField(blank=True, help_text='Caso a atividade seja inválida justifique', verbose_name='Justificativa'),
        ),
    ]
