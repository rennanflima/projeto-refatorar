# MODELS DE PARÂMETROS DO SISTEMA
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.defaultfilters import slugify as slug_template
from django.utils.text import slugify

from manhana.core.managers import (AtividadeQuerySet,
                                   EstruturaOrganizacionalQuerySet,
                                   FluxoProcessoQuerySet,
                                   ResponsavelUnidadeQuerySet,
                                   SituacaoProcessoQuerySet,
                                   UnidadeFluxoProcessoQuerySet,
                                   VinculoServidorUnidadeQuerySet)
from manhana.core.models.choices import *
from manhana.core.models.publico import Auditavel


class EstruturaOrganizacional(models.Model):
    RAIZ = 1
    CAMPUS = 2
    COMISSAO = 3
    SETOR = 4
    POLO = 5
    PRO_REITORIA = 6
    nome = models.CharField('Nome da estrutura organizacional', max_length=150)
    sigla = models.CharField('Sigla da estrutura organizacional', max_length=30, blank=True)
    tipo_estrutura = models.IntegerField('Tipo de estrutura organizacional', choices=TIPO_ESTRUTURA, default=SETOR)
    estrutura_pai = models.ForeignKey('self', related_name='estrutura_pai_fk', blank=True, null=True, on_delete=models.PROTECT)
    is_ativo = models.BooleanField('Estrutura ativa?', default=True, help_text='Indica que a \
        estrutura organizacional será tratada como ativa. Ao invés de excluir a estrutura, desmarque isso.')
    sucessora = models.ManyToManyField('self', blank=True, symmetrical=False)
    id_unidade_sig = models.IntegerField('ID da unidade nos SIGs', blank=True, null=True, db_index=True)

    objects = EstruturaOrganizacionalQuerySet.as_manager()

    class Meta:
        verbose_name = 'Estrutura Organizacional' 
        verbose_name_plural = 'Estruturas Organizacionais'
        ordering = ('tipo_estrutura', 'nome')
        db_table = 'estrutura_organizacional'

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(EstruturaOrganizacional, self).save(*args, **kwargs)


class AreaContratacao(models.Model):
    """MODEL PARA MANUTENÇÃO DA AREA DE CONTRATACAO DO DOCENTE"""
    nome = models.CharField('Nome da área de contratação', max_length=150)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que a \
        área de contratação será tratada como ativa. Ao invés de excluir a área, desmarque isso.')

    class Meta:
        ordering = ['is_ativo', 'nome']
        verbose_name = 'Área de contratação'
        verbose_name_plural = 'Áreas de contratação'
        db_table = 'area_contratacao'

    def __str__(self):
        return self.nome


class CategoriaAtividade(models.Model):
    """
    MODEL PARA MANUTENÇÃO DAS CATEGORIAS DE ATIVIDADE EXERCIDAS
    PELO DOCENTE (ENSINO, COMPLEMENTAR, PESQUISA, EXTENSÃO, GESTÃO, ETC.)
    """
    nome = models.CharField('Nome da categoria da atividade', max_length=150, unique=True)
    label = models.CharField('Label da categoria da atividade', max_length=150, blank=True)
    descricao = models.TextField('Descrição da categoria da atividade', blank=True)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que a \
        categoria de atividade será tratada como ativa. Ao invés de excluir a categoria, desmarque isso.')
    slug = models.SlugField('Slug', unique=True, blank=True, null=True)
    categoria_pai = models.ForeignKey('self', related_name='categoria_atividade_pai', on_delete=models.PROTECT, blank=True, null=True)
    is_importada = models.BooleanField('Atividade importada?', default=False, help_text='Indica que os \
        dados atividade será importado de um sistema externo.')
    is_restricao_ch_semanal = models.BooleanField('Atividade tem restrição de carga horária semanal?', default=False, help_text='Indica que os \
        dados atividade tem restrição de carga horária semanal.')

    class Meta:
        ordering = ['is_ativo', 'nome']
        verbose_name = 'Categoria de atividade'
        verbose_name_plural = 'Categorias de atividades'
        db_table = 'categoria_atividade'

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nome)
        super(CategoriaAtividade, self).save(*args, **kwargs)


class CHSemanalCategoriaAtividade(models.Model):
    """MODEL PARA REFERENCIAR CATEGORIA ATIVIDADE COM GRUPO DOCENTE DEFININDO CARGA HORÁRIA SEMANAL MÁXIMA E MÍNIMA"""
    categoria_atividade = models.ManyToManyField(CategoriaAtividade, related_name='carga_horaria_semanal_categoria_atividade')
    grupo_docente = models.ManyToManyField('authentication.GrupoDocente', related_name='carga_horaria_semanal_categoria_atividade')
    ch_minima = models.DecimalField('Carga horária mínima semanal', max_digits=10, decimal_places=2)
    ch_maxima = models.DecimalField('Carga horária máxima semanal', max_digits=10, decimal_places=2)

    def __str__(self):
        return str(self.id)

    def categorias(self):
        return ', '.join([c.nome for c in self.categoria_atividade.all()])
    categorias.short_description = "Categorias de Atividades"

    def grupos(self):
        return ', '.join([g.nome for g in self.grupo_docente.all()])
    grupos.short_description = "Grupos de Docentes"

    class Meta:
        ordering = ['id', ]
        verbose_name = 'Carga horária semanal máxima de Categoria de Atividade por Grupo Docente'
        verbose_name_plural = 'Cargas horárias semanais máximas de Categoria de Atividade por Grupo Docente'
        db_table = 'chsemanal_atividade_docente'


class Atividade(models.Model):
    """MODEL PARA MANUTENÇÃO DAS ATIVIDADES EXERCIDAS PELO DOCENTE"""
    RESOLUCAO = 'RESOLUCAO'
    CURSO = 'CURSO'
    TURMA = 'TURMA'
    DISCIPLINA = 'DISCIPLINA'
    PROJETO = 'PROJETO'
    QUANTIDADE = 'QUANTIDADE'
    descricao = models.TextField('Descrição da Atividade', unique=True)
    ch_minima = models.DecimalField('Carga horária mínima semanal', max_digits=10, decimal_places=2)
    ch_maxima = models.DecimalField('Carga horária máxima semanal', max_digits=10, decimal_places=2)
    validacao_ch_por = models.CharField('Validação da carga horária', max_length=15, choices=VALIDACAO_POR_CHOICES, default=RESOLUCAO)
    comprovacao = models.BooleanField('Necessita de comprovação?', default=True, help_text='Indica se \
                                      esta atividade obrigatoriamente necessita de uma comprovação documental.')
    tipo_comprovante = models.CharField('Comprovante', max_length=150, blank=True, help_text='Indica \
        o tipo de comprovante que será necessário comprovar.')
    categoria_atividade = models.ForeignKey(CategoriaAtividade, related_name='atividades',
                                            on_delete=models.PROTECT)
    observacao = models.TextField('Observação(ões)', blank=True)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que a \
                                   atividade será tratada como ativa. Ao invés de excluir a atividade, desmarque isso.')
    is_obrigatorio = models.BooleanField('Atividade obrigatória?', default=False, help_text='Indica que a \
                                         atividade será tratada como obrigatória em todos os grupos de docentes.')

    objects = AtividadeQuerySet.as_manager()

    class Meta:
        ordering = ['is_ativo', 'categoria_atividade', 'descricao']
        db_table = 'atividade'

    def __str__(self):
        return self.descricao

    def categoriaatividade(self):
        return self.categoria_atividade.nome
    categoriaatividade.short_description = 'Categoria de atividade'

    def clean(self):
        if self.ch_minima < 0 or self.ch_maxima < 0:
            raise ValidationError('As cargas horárias não podem ser menor que zero.')
        if self.ch_maxima < self.ch_minima:
            raise ValidationError({'ch_maxima':'Carga horária máxima não pode ser menor que carga horária mínima.'})


class SituacaoProcesso(models.Model):
    nome = models.CharField('Nome da situação do processo', max_length=150, unique=True)
    descricao = models.TextField('Observação(ões)', blank=True)
    slug = models.SlugField('Slug', unique=True)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que a \
        situação do processo será tratada como ativa. Ao invés de excluir a situação do processo, desmarque isso.')

    objects = SituacaoProcessoQuerySet.as_manager()

    class Meta:
        ordering = ['is_ativo', 'nome']
        verbose_name = 'Situação do processo'
        verbose_name_plural = 'Situações dos processos'
        db_table = 'situacao_processo'

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nome)
        super(SituacaoProcesso, self).save(*args, **kwargs)


class CategoriaProcesso(models.Model):
    nome = models.CharField('Nome da categoria de processo', max_length=150)
    descricao = models.CharField('Descrição da categoria de processo', max_length=250, blank=True)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que a \
        categoria de processo será tratada como ativa. Ao invés de excluir a categoria, desmarque isso.')
    categoria_atividade = models.ManyToManyField(CategoriaAtividade, related_name='categoria_processo_atividade_fk', blank=True)
    categoria_pai = models.ForeignKey('self', related_name='categoria_pai_processo_fk', blank=True, null=True, on_delete=models.PROTECT)
    situacao_processso = models.ManyToManyField(SituacaoProcesso, related_name='categorias_processo', blank=True)

    class Meta:
        ordering = ['is_ativo', 'nome']
        verbose_name = 'Categoria de processo'
        verbose_name_plural = 'Categorias de processos'
        db_table = 'categoria_processo'

    def __str__(self):
        if not self.categoria_pai:
            return self.nome
        else:
            return f"{self.nome} ({self.categoria_pai.nome})"

    def categorias_atividade(self):
        return ', '.join([ca.nome for ca in self.categoria_atividade.all()])
    categoria_atividade.short_description = "Categorias de Atividades do Processo"

    def situacoes_processo(self):
        return ', '.join([s.nome for s in self.situacao_processso.all()])
    categoria_atividade.short_description = "Situações do Processo"


class ArgumentoCategoria(models.Model):
    TEXTO = 'TEXTO'
    INTEIRO = 'INTEIRO'
    DECIMAL = 'DECIMAL'
    BOOLEAN = 'BOOLEAN'
    DATA = 'DATA'
    HORA = 'HORA'
    DATA_HORA = 'DATA_HORA'
    ARQUIVO = 'ARQUIVO'
    campo = models.CharField('Nome do campo', max_length=100)
    is_requerido = models.BooleanField('Campo obrigatório?', default=False)
    tipo_dado = models.CharField('Tipo de dado do campo', max_length=20, choices=TIPO_DADO)
    categoria_atividade = models.ManyToManyField(CategoriaAtividade, related_name='argumentos')
    slug = models.SlugField('Slug', unique=True, blank=True)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que a \
        categoria de processo será tratada como ativa. Ao invés de excluir a categoria, desmarque isso.')

    class Meta:
        verbose_name = 'Argumento da categoria da atividade'
        verbose_name_plural = 'Argumentos das categorias das atividades'
        db_table = 'argumento_categoria'

    def __str__(self):
        return '%s' % (self.campo)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.campo)
        super(ArgumentoCategoria, self).save(*args, **kwargs)

    def categorias(self):
        return ', '.join([p.nome for p in self.categoria_atividade.all()])
    categorias.short_description = "Categorias associados ao argumento"


class ParametroSistema(models.Model):
    nome = models.CharField('Nome do parâmetro', max_length=150)
    descricao = models.TextField('Descrição do parâmetro', blank=True, null=True)
    tipo_dado = models.CharField('Tipo de dado do parâmetro', max_length=20, choices=TIPO_DADO)
    valor = models.CharField('Valor do parâmetro', max_length=50)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que o \
        parâmetro do sistema será tratado como ativo. Ao invés de excluir, desmarque isso.')

    class Meta:
        ordering = ('nome',)
        verbose_name = 'Parâmetro do Sistema'
        verbose_name_plural = 'Parâmetros do Sistema'
        db_table = 'parametro_sistema'

    def __str__(self):
        return self.nome


class ResponsavelUnidade(models.Model):
    CHEFE = 'C'
    VICE_CHEFIA = 'V'
    SECRETARIA = 'S'
    SUPERVISOR = 'A'
    servidor = models.ForeignKey('authentication.ServidorProfile', on_delete=models.PROTECT, related_name='responsaveis_unidade')
    unidade = models.ForeignKey(EstruturaOrganizacional, on_delete=models.PROTECT, related_name='responsaveis_unidade')
    nivel_responsabilidade = models.CharField('Nível de responsabilidade', max_length=5, choices=TIPO_NIVEL_RESPONSABILIDADE)
    data_inicio = models.DateField('Data de início')
    data_termino = models.DateField('Data de termíno', blank=True, null=True)
    id_responsabilidade_sig = models.IntegerField('ID da responsabilidade nos SIGs', blank=True, null=True, unique=True)

    objects = ResponsavelUnidadeQuerySet.as_manager()

    class Meta:
        verbose_name = 'Responsável da Unidade'
        verbose_name_plural = 'Responsáveis da Unidade'
        ordering = ('data_inicio', 'data_termino', 'unidade',)
        db_table = 'responsavel_unidade'

    def __str__(self):
        return f"{self.get_nivel_responsabilidade_display()} da {self.unidade.nome}."


class FluxoProcesso(models.Model):
    PRINCIPAL = 'P'
    RECURSO = 'R'
    CONSULTA = 'C'
    nome = models.CharField('Nome do fluxo do processo', max_length=150, unique=True)
    tipo_processo = models.ForeignKey(CategoriaProcesso, on_delete=models.PROTECT, related_name='fluxos')
    tipo_fluxo = models.CharField('Tipo do fluxo do processo', max_length=5, default=PRINCIPAL,choices=TIPO_FLUXO_PROCESSO)
    unidade = models.ForeignKey(EstruturaOrganizacional, on_delete=models.PROTECT, related_name='fluxos_processo_unidade', blank=True, null=True)
    is_ativo = models.BooleanField('Fluxo ativo?', default=True, help_text='Indica que o \
                                   fluxo será tratado como ativo. Ao invés de excluir o fluxo, desmarque isso.')

    objects = FluxoProcessoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Fluxo do Processo'
        verbose_name_plural = 'Fluxos dos Processos'
        db_table = 'fluxo_processo'
        ordering = ['is_ativo', 'nome', 'tipo_processo']

    def __str__(self):
        return f"{self.nome} - '{self.tipo_fluxo}' do {self.unidade} do processo de {self.tipo_processo}."


class UnidadeFluxoProcesso(models.Model):
    unidade = models.ForeignKey(EstruturaOrganizacional, on_delete=models.PROTECT, related_name='unidades_fluxo_processo')
    fluxo_processo = models.ForeignKey(FluxoProcesso, on_delete=models.PROTECT, related_name='unidades_fluxo_processo')
    ordem = models.PositiveSmallIntegerField('Ordem')
    is_avaliadora = models.BooleanField('Unidade Avaliadora?', default=False, help_text='Indica que os \
        membros da unidade poderão avaliar as atividades informadas no PIT/RIT.')
    is_ativo = models.BooleanField('Fluxo ativo?', default=True, help_text='Indica que a \
                                   unidade será tratado como ativa no fluxo. Ao invés de excluir a unidade, desmarque isso.')

    objects = UnidadeFluxoProcessoQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['unidade', 'fluxo_processo'], condition=Q(is_ativo=True), name='unique_active_unidade')
        ]
        verbose_name = 'Unidade do Fluxo do Processo'
        verbose_name_plural = 'Unidades do Fluxo do Processo'
        ordering = ['is_ativo', 'ordem']
        db_table = 'unidades_fluxo_processo'

    def __str__(self):
        return f"{self.unidade}"

    def clean(self):

        unidade_fluxo_qs = UnidadeFluxoProcesso.objects.filter(fluxo_processo=self.fluxo_processo, is_ativo=True)
        if unidade_fluxo_qs.exists():
            if not self.pk:
                self.ordem = unidade_fluxo_qs.last().ordem + 1
                if unidade_fluxo_qs.filter(unidade=self.unidade).exists():
                    raise ValidationError({'unidade': f"A unidade '{self.unidade}' já está cadastra neste fluxo."})
            else:
                unidade_exitente = unidade_fluxo_qs.filter(ordem=self.ordem).first()
                if unidade_exitente and unidade_exitente.unidade != self.unidade:
                    raise ValidationError({'ordem': f"A ordem {self.ordem} está vinculada à unidade '{unidade_exitente}'."})
        else:
            self.ordem = 1


class VinculoServidorUnidade(models.Model):
    PRESIDENTE = 'P'
    VICE_PRESIDENTE = 'V'
    SECRETARIO = 'S'
    MEMBRO = 'M'
    unidade = models.ForeignKey(EstruturaOrganizacional, on_delete=models.PROTECT, related_name='servidores_unidade')
    servidor = models.ForeignKey('authentication.ServidorProfile', on_delete=models.PROTECT, related_name='vinculos_unidade')
    portaria = models.CharField('Portaria', max_length=150)
    tipo_vinculo = models.CharField('Tipo Vinculo', max_length=5, choices=TIPO_VINCULO)
    data_inicio = models.DateField('Data de início')
    data_termino = models.DateField('Data de termíno', blank=True, null=True)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que este vínculo será tratado como ativo. Ao invés de excluir o vínculo, desmarque isso.')

    objects = VinculoServidorUnidadeQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['unidade', 'servidor'], condition=Q(is_ativo=True), name='unique_active_vinculo_servidor')
        ]
        verbose_name = 'Vínculo de Servidor com a Unidade'
        verbose_name_plural = 'Vínculo de Servidores com as Unidades'
        ordering = ['is_ativo', 'unidade']
        db_table = 'vinculo_servidor_unidade'

    def __str__(self):
        return f"{self.servidor} tem vinculo de {self.get_tipo_vinculo_display()} com {self.unidade}."

    # def servidores(self):
    #     return ', '.join([p.nome for p in self.servidor.all()])
    # servidores.short_description = "Servidores viculados com a unidade"
