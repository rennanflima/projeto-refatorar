# Generated by Django 2.2.4 on 2019-09-04 16:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_auto_20190903_1601'),
    ]

    operations = [
        migrations.AddField(
            model_name='processo',
            name='unidade_interessada',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='processos', to='core.EstruturaOrganizacional'),
        ),
        migrations.AlterField(
            model_name='categoriaprocesso',
            name='categoria_atividade',
            field=models.ManyToManyField(blank=True, related_name='categoria_processo_atividade_fk', to='core.CategoriaAtividade'),
        ),
        migrations.AlterField(
            model_name='documentoprocesso',
            name='tipo_documento',
            field=models.CharField(choices=[('SOLICITACAO', 'Solicitação'), ('PARECER', 'Parecer'), ('DESPACHO', 'Despacho')], default='PARECER', max_length=10, verbose_name='Tipo do documento'),
        ),
        migrations.AlterField(
            model_name='fluxoprocesso',
            name='tipo_fluxo',
            field=models.CharField(choices=[('P', 'Principal'), ('R', 'Recurso'), ('C', 'Consulta')], default='P', max_length=5, verbose_name='Tipo do fluxo do processo'),
        ),
        migrations.AlterField(
            model_name='processo',
            name='interessado',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='processos', to='authentication.DocenteProfile'),
        ),
    ]
