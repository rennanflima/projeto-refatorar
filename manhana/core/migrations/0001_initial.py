# Generated by Django 2.1.7 on 2019-06-18 15:46

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('authentication', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AreaContratacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, verbose_name='Nome da área de contratação')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que a         área de contratação será tratada como ativa. Ao invés de excluir a área, desmarque isso.', verbose_name='Ativo?')),
            ],
            options={
                'verbose_name': 'Área de contratação',
                'verbose_name_plural': 'Áreas de contratação',
                'db_table': 'area_contratacao',
                'ordering': ['is_ativo', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='ArgumentoCategoria',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('campo', models.CharField(max_length=100, verbose_name='Nome do campo')),
                ('is_requerido', models.BooleanField(default=False, verbose_name='Campo obrigatório?')),
                ('tipo_dado', models.CharField(choices=[('TEXTO', 'Texto'), ('INTEIRO', 'Inteiro'), ('DECIMAL', 'Decimal'), ('BOOLEAN', 'Boolean'), ('DATA', 'Data'), ('HORA', 'Hora'), ('DATA_HORA', 'Data/Hora')], max_length=20, verbose_name='Tipo de dado do campo')),
                ('slug', models.SlugField(blank=True, unique=True, verbose_name='Slug')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que a         categoria de processo será tratada como ativa. Ao invés de excluir a categoria, desmarque isso.', verbose_name='Ativo?')),
            ],
            options={
                'verbose_name': 'Argumento da categoria da atividade',
                'verbose_name_plural': 'Argumentos das categorias das atividades',
                'db_table': 'argumento_categoria',
            },
        ),
        migrations.CreateModel(
            name='Atividade',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.TextField(unique=True, verbose_name='Descrição da Atividade')),
                ('ch_minima', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Carga horária mínima semanal')),
                ('ch_maxima', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Carga horária máxima semanal')),
                ('validacao_ch_por', models.CharField(choices=[('RESOLUCAO', 'Conforme resolução'), ('CURSO', 'Por Curso'), ('TURMA', 'Por turma'), ('DISCIPLINA', 'Por disciplina'), ('PROJETO', 'Por Projeto')], default='RESOLUCAO', max_length=15, verbose_name='Validação da carga horária')),
                ('comprovacao', models.BooleanField(default=True, help_text='Indica se         esta atividade obrigatoriamente necessita de uma comprovação documental.', verbose_name='Necessita de comprovação?')),
                ('tipo_comprovante', models.CharField(blank=True, help_text='Indica         o tipo de comprovante que será necessário comprovar.', max_length=150, verbose_name='Comprovante')),
                ('observacao', models.TextField(blank=True, verbose_name='Observação(ões)')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que a         atividade será tratada como ativa. Ao invés de excluir a atividade, desmarque isso.', verbose_name='Ativo?')),
                ('is_obrigatorio', models.BooleanField(default=False, help_text='Indica que a         atividade será tratada como obrigatória em todos os grupos de docentes.', verbose_name='Atividade obrigatória?')),
            ],
            options={
                'db_table': 'atividade',
                'ordering': ['is_ativo', 'categoria_atividade', 'descricao'],
            },
        ),
        migrations.CreateModel(
            name='CategoriaAtividade',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, unique=True, verbose_name='Nome da categoria da atividade')),
                ('label', models.CharField(blank=True, max_length=150, verbose_name='Label da categoria da atividade')),
                ('descricao', models.TextField(blank=True, verbose_name='Descrição da categoria da atividade')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que a         categoria de atividade será tratada como ativa. Ao invés de excluir a categoria, desmarque isso.', verbose_name='Ativo?')),
                ('slug', models.SlugField(blank=True, null=True, unique=True, verbose_name='Slug')),
                ('categoria_pai', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='categoria_atividade_pai', to='core.CategoriaAtividade')),
            ],
            options={
                'verbose_name': 'Categoria de atividade',
                'verbose_name_plural': 'Categorias de atividades',
                'db_table': 'categoria_atividade',
                'ordering': ['is_ativo', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='CategoriaProcesso',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, verbose_name='Nome da categoria de processo')),
                ('descricao', models.CharField(blank=True, max_length=250, verbose_name='Descrição da categoria de processo')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que a         categoria de processo será tratada como ativa. Ao invés de excluir a categoria, desmarque isso.', verbose_name='Ativo?')),
                ('categoria_atividade', models.ManyToManyField(related_name='categoria_processo_atividade_fk', to='core.CategoriaAtividade')),
                ('categoria_pai', models.ManyToManyField(blank=True, related_name='_categoriaprocesso_categoria_pai_+', to='core.CategoriaProcesso')),
            ],
            options={
                'verbose_name': 'Categoria de processo',
                'verbose_name_plural': 'Categorias de processos',
                'db_table': 'categoria_processo',
                'ordering': ['is_ativo', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='CHSemanalCategoriaAtividade',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ch_minima', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Carga horária mínima semanal')),
                ('ch_maxima', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Carga horária máxima semanal')),
                ('categoria_atividade', models.ManyToManyField(related_name='categoria_atividade_chsmaxima_fk', to='core.CategoriaAtividade')),
                ('grupo_docente', models.ManyToManyField(related_name='grupo_docente_chmaxima_fk', to='authentication.GrupoDocente')),
            ],
            options={
                'verbose_name': 'Carga horária semanal máxima de Categoria de Atividade por Grupo Docente',
                'verbose_name_plural': 'Cargas horárias semanais máximas de Categoria de Atividade por Grupo Docente',
                'db_table': 'chsemanal_atividade_docente',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='EstruturaOrganizacional',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, verbose_name='Nome da estrutura organizacional')),
                ('tipo_estrutura', models.IntegerField(choices=[(1, 'Raiz'), (2, 'Campus'), (3, 'Comissão'), (4, 'Setor'), (5, 'Polo')], default=1, verbose_name='Tipo de estrutura organizacional')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que a         estrutura organizacional será tratada como ativa. Ao invés de excluir a estrutura, desmarque isso.', verbose_name='Estrutura ativa?')),
                ('estrutura_pai', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='estrutura_pai_fk', to='core.EstruturaOrganizacional')),
                ('sucessora', models.ManyToManyField(related_name='_estruturaorganizacional_sucessora_+', to='core.EstruturaOrganizacional')),
            ],
            options={
                'verbose_name': 'Estrutura Organizacional',
                'verbose_name_plural': 'Estruturas Organizacionais',
                'db_table': 'estrutura_organizacional',
                'ordering': ('tipo_estrutura', 'nome'),
            },
        ),
        migrations.CreateModel(
            name='InformacaoArgumento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_texto', models.TextField(blank=True, verbose_name='Valor da informação em Texto')),
                ('valor_inteiro', models.IntegerField(blank=True, null=True, verbose_name='Valor da informação em Número Inteiro')),
                ('valor_decimal', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Valor da informação em Número Decimal')),
                ('valor_data', models.DateField(blank=True, null=True, verbose_name='Valor da informação em Data')),
                ('valor_hora', models.TimeField(blank=True, null=True, verbose_name='Valor da informação em Hora')),
                ('valor_data_hora', models.DateTimeField(blank=True, null=True, verbose_name='Valor da informação em Data/Hora')),
                ('valor_boolean', models.NullBooleanField(verbose_name='Valor da informação Verdadeiro ou Falso')),
                ('argumento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='informacoes_argumentos', to='core.ArgumentoCategoria')),
            ],
            options={
                'verbose_name': 'Informação do Argumento',
                'verbose_name_plural': 'Informações dos Argumentos',
                'db_table': 'informacao_argumento',
            },
        ),
        migrations.CreateModel(
            name='ParametroSistema',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, verbose_name='Nome do parâmetro')),
                ('descricao', models.TextField(blank=True, null=True, verbose_name='Descrição do parâmetro')),
                ('tipo_dado', models.CharField(choices=[('TEXTO', 'Texto'), ('INTEIRO', 'Inteiro'), ('DECIMAL', 'Decimal'), ('BOOLEAN', 'Boolean'), ('DATA', 'Data'), ('HORA', 'Hora'), ('DATA_HORA', 'Data/Hora')], max_length=20, verbose_name='Tipo de dado do parâmetro')),
                ('valor', models.CharField(max_length=50, verbose_name='Valor do parâmetro')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que o         parâmetro do sistema será tratado como ativo. Ao invés de excluir, desmarque isso.', verbose_name='Ativo?')),
            ],
            options={
                'verbose_name': 'Parâmetro do Sistema',
                'verbose_name_plural': 'Parâmetros do Sistema',
                'db_table': 'parametro_sistema',
                'ordering': ('nome',),
            },
        ),
        migrations.CreateModel(
            name='Processo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('ultima_modificacao_em', models.DateTimeField(auto_now=True)),
                ('numero_processo', models.CharField(blank=True, max_length=60, null=True, verbose_name='Número do processo')),
                ('ano', models.PositiveIntegerField(default=2019, validators=[django.core.validators.MinValueValidator(2018), django.core.validators.MaxValueValidator(2020)], verbose_name='Ano')),
                ('semestre', models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(4)], verbose_name='Semestre')),
                ('assunto', models.CharField(blank=True, max_length=255, verbose_name='Assunto')),
                ('quantidade_leitura', models.PositiveIntegerField(default=0, verbose_name='Quantidade de leituras')),
                ('criado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='processo_requests_created', to=settings.AUTH_USER_MODEL)),
                ('interessado', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='processos', to='authentication.DocenteProfile')),
                ('modificado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='processo_requests_modified', to=settings.AUTH_USER_MODEL)),
                ('processo_pai', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='processos_pai', to='core.Processo')),
            ],
            options={
                'verbose_name': 'Processo',
                'verbose_name_plural': 'Processos',
                'ordering': ['ano', 'semestre'],
            },
        ),
        migrations.CreateModel(
            name='RegistroAtividade',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ch_semanal', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Carga horária semanal')),
                ('is_editavel', models.BooleanField(default=True, help_text='Indica que a         atividade será tratada como editável.', verbose_name='Editável?')),
                ('is_obrigatorio', models.BooleanField(default=False, help_text='Indica que a         atividade será tratada como obrigatória para o processo.', verbose_name='Atividade obrigatória?')),
                ('atividade', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='registros_atividade', to='core.Atividade')),
                ('processo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registros_atividade', to='core.Processo')),
            ],
            options={
                'verbose_name': 'Registro da Atividade',
                'verbose_name_plural': 'Registros das atividades',
                'db_table': 'regitro_atividade',
            },
        ),
        migrations.CreateModel(
            name='SituacaoProcesso',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, unique=True, verbose_name='Nome da situação do processo')),
                ('descricao', models.TextField(blank=True, verbose_name='Observação(ões)')),
                ('slug', models.SlugField(unique=True, verbose_name='Slug')),
                ('is_ativo', models.BooleanField(default=True, help_text='Indica que a         situação do processo será tratada como ativa. Ao invés de excluir a situação do processo, desmarque isso.', verbose_name='Ativo?')),
            ],
            options={
                'verbose_name': 'Situação do processo',
                'verbose_name_plural': 'Situações dos processos',
                'db_table': 'situacao_processo',
                'ordering': ['is_ativo', 'nome'],
            },
        ),
        migrations.AddField(
            model_name='processo',
            name='situacao',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='processos', to='core.SituacaoProcesso'),
        ),
        migrations.AddField(
            model_name='processo',
            name='tipo_processo',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='processos', to='core.CategoriaProcesso'),
        ),
        migrations.AddField(
            model_name='informacaoargumento',
            name='registro_atividade',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='informacoes_argumentos', to='core.RegistroAtividade'),
        ),
        migrations.AddField(
            model_name='categoriaprocesso',
            name='situacao_processso',
            field=models.ManyToManyField(blank=True, related_name='categorias_processo', to='core.SituacaoProcesso'),
        ),
        migrations.AddField(
            model_name='atividade',
            name='categoria_atividade',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='categoria_atividade_fk', to='core.CategoriaAtividade'),
        ),
        migrations.AddField(
            model_name='argumentocategoria',
            name='categoria_atividade',
            field=models.ManyToManyField(to='core.CategoriaAtividade'),
        ),
        migrations.AlterUniqueTogether(
            name='processo',
            unique_together={('ano', 'semestre', 'tipo_processo', 'interessado')},
        ),
    ]
