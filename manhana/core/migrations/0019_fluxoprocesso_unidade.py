# Generated by Django 2.1.7 on 2019-08-15 12:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_auto_20190814_1448'),
    ]

    operations = [
        migrations.AddField(
            model_name='fluxoprocesso',
            name='unidade',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='fluxo_processo_unidade', to='core.EstruturaOrganizacional'),
        ),
    ]
