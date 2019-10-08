# Generated by Django 2.2.4 on 2019-09-03 21:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_auto_20190903_1552'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='categoriaprocesso',
            name='categoria_pai',
        ),
        migrations.AddField(
            model_name='categoriaprocesso',
            name='categoria_pai',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='categoria_pai_processo_fk', to='core.CategoriaProcesso'),
        ),
    ]
