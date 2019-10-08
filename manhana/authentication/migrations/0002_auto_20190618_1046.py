# Generated by Django 2.1.7 on 2019-06-18 15:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='servidorprofile',
            name='unidade_responsavel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='unidade_responsavel_organizacional_fk', to='core.EstruturaOrganizacional'),
        ),
        migrations.AddField(
            model_name='discenteprofile',
            name='pessoa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='authentication.Pessoa'),
        ),
        migrations.AddField(
            model_name='docenteprofile',
            name='area_contratacao',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='docentes_area_contratacao', to='core.AreaContratacao'),
        ),
        migrations.AddField(
            model_name='docenteprofile',
            name='grupo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='docentes_grupo', to='authentication.GrupoDocente'),
        ),
    ]
