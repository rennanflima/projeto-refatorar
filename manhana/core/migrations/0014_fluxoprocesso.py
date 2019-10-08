# Generated by Django 2.1.7 on 2019-08-01 16:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_responsavelunidade_id_responsabilidade_sig'),
    ]

    operations = [
        migrations.CreateModel(
            name='FluxoProcesso',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, unique=True, verbose_name='Nome da situação do processo')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que o         fluxo será tratado como ativo. Ao invés de excluir o fluxo, desmarque isso.', verbose_name='Fluxo ativo?')),
                ('tipo_processo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='fluxo_processos', to='core.CategoriaProcesso')),
            ],
            options={
                'verbose_name': 'Fluxo do Processo',
                'verbose_name_plural': 'Fluxos dos Processos',
                'db_table': 'fluxo_processo',
                'ordering': ['is_ativo', 'nome', 'tipo_processo'],
            },
        ),
    ]
