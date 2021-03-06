# Generated by Django 2.1.7 on 2019-06-18 16:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_grupodocente_grupo_pai'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='grupodocente',
            options={'ordering': ('nome',), 'verbose_name': 'Grupo do docente', 'verbose_name_plural': 'Grupos dos docentes'},
        ),
        migrations.AlterField(
            model_name='grupodocente',
            name='grupo_pai',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='grupos_pai', to='authentication.GrupoDocente'),
        ),
    ]
