# Generated by Django 2.1.7 on 2019-08-01 16:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_fluxoprocesso'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnidadeFluxoProcesso',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordem', models.PositiveSmallIntegerField(verbose_name='Ordem')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que a         unidade será tratado como ativa no fluxo. Ao invés de excluir a unidade, desmarque isso.', verbose_name='Fluxo ativo?')),
            ],
            options={
                'verbose_name': 'Unidade do Fluxo do Processo',
                'verbose_name_plural': 'Unidades do Fluxo do Processo',
                'db_table': 'unidades_fluxo_processo',
                'ordering': ['is_ativo', 'ordem'],
            },
        ),
        migrations.AlterField(
            model_name='fluxoprocesso',
            name='nome',
            field=models.CharField(max_length=150, unique=True, verbose_name='Nome do fluxo do processo'),
        ),
        migrations.AddField(
            model_name='unidadefluxoprocesso',
            name='fluxo_processo',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='unidades_fluxo_processo', to='core.FluxoProcesso'),
        ),
        migrations.AddField(
            model_name='unidadefluxoprocesso',
            name='unidade',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='unidades_fluxo_processo', to='core.EstruturaOrganizacional'),
        ),
    ]
