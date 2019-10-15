import datetime

from ckeditor.fields import RichTextField
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models
from django.db.models import ProtectedError, Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.formats import localize

from manhana.authentication.models import DocenteProfile
from manhana.core.managers import (InformacaoArgumentoQuerySet,
                                    ProcessoQuerySet,
                                    RegistroAtividadeQuerySet, TramiteQuerySet)
from manhana.core.models.parametro import *
from manhana.core.models.publico import *


def current_year():
    return datetime.date.today().year


class Processo(Auditavel):
    numero_processo = models.CharField('Número do processo', max_length=60, blank=True, null=True)
    ano = models.PositiveIntegerField('Ano', default=current_year(), validators=[MinValueValidator(current_year()-1), MaxValueValidator(current_year()+1)])
    semestre = models.PositiveSmallIntegerField('Semestre', default=1, validators=[MinValueValidator(1), MaxValueValidator(4)])
    assunto = models.CharField('Assunto', max_length=255, blank=True)
    quantidade_leitura = models.PositiveIntegerField('Quantidade de leituras', default=0)
    processo_pai = models.ForeignKey('self', on_delete=models.PROTECT, related_name='processos_pai', blank=True, null=True)
    tipo_processo = models.ForeignKey(CategoriaProcesso, on_delete=models.PROTECT, related_name='processos')
    interessado = models.ForeignKey(DocenteProfile, on_delete=models.PROTECT, related_name='processos', blank=True, null=True)
    unidade_interessada = models.ForeignKey(EstruturaOrganizacional, on_delete=models.PROTECT, related_name='processos_unidade_interessada', blank=True, null=True)
    situacao = models.ForeignKey(SituacaoProcesso, on_delete=models.PROTECT, related_name='processos', default=1)

    objects = ProcessoQuerySet.as_manager()

    class Meta:
        ordering = ['ano', 'semestre']
        unique_together = ('ano', 'semestre', 'tipo_processo', 'interessado')
        verbose_name = 'Processo'
        verbose_name_plural = 'Processos'

    def __str__(self):
        return f'{self.tipo_processo} de N.º {self.numero_processo}'

    def get_absolute_url(self):
        return reverse('core:processo-detalhe', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.numero_processo:
            if self.interessado:
                numero_processo = f'{self.ano}{self.semestre}{self.tipo_processo.pk}/{self.interessado.pk}{self.interessado.unidade_responsavel.pk}'
            elif self.unidade_interessada:
                numero_processo = f'{self.ano}{self.semestre}{self.tipo_processo.pk}/{self.unidade_interessada.pk}{self.unidade_interessada.estrutura_pai.pk or ""}'

            num_existentes = Processo.objects.filter(numero_processo=numero_processo)
            if num_existentes.exists():
                num_filters = num_existentes.filter(numero_processo__icontains='-')
                if num_filters.exists():
                    self.numero_processo = f"{numero_processo}-{num_filters.count()+1}"
            else:
                self.numero_processo = numero_processo

        super(Processo, self).save(*args, **kwargs)

    def exibir_interessado(self):
        if self.interessado:
            return self.interessado.pessoa.user.get_full_name() 
        return self.unidade_interessada

    def subtotal_ch_semanal_tipo_atividade(self):
        valores = dict()
        tipo_atividade = self.tipo_processo.categoria_atividade.filter(categoria_pai__isnull=True)
        for ta in tipo_atividade:
            registros_list = RegistroAtividade.objects.filter(Q(processo=self) & (Q(atividade__categoria_atividade=ta) | Q(atividade__categoria_atividade__categoria_pai=ta)))
            subtotal = 0
            for r in registros_list:
                subtotal = subtotal + r.ch_semanal
            valores[ta] = subtotal

        return valores

    def categoria_status_avaliacao(self):
        valores = dict()
        tipo_atividade = self.tipo_processo.categoria_atividade.filter(categoria_pai__isnull=True)
        for ta in tipo_atividade:
            registros_list = RegistroAtividade.objects.filter(Q(processo=self) & (Q(atividade__categoria_atividade=ta) | Q(atividade__categoria_atividade__categoria_pai=ta)))
            total_atv_avaliadas = 0
            for r in registros_list:
                if r.situacao == RegistroAtividade.VALIDA or r.situacao == RegistroAtividade.INVALIDA:
                    total_atv_avaliadas = total_atv_avaliadas + 1

            if not registros_list.exists():
                valores[ta] = None
            elif total_atv_avaliadas < registros_list.count():
                valores[ta] = False
            else:
                valores[ta] = True

        return valores

    def ch_semanal_total(self):
        total = 0
        for k, v in self.subtotal_ch_semanal_tipo_atividade().items():
            total = total + v
        return total

    def qtd_disciplinas(self):
        atividade_ensino = Atividade.objects.get(descricao='Aula')
        argumento_ensino = ArgumentoCategoria.objects.get(categoria_atividade=atividade_ensino.categoria_atividade, campo='Disciplina')
        registro_atividade = RegistroAtividade.objects.filter(atividade=atividade_ensino, processo=self)
        informacoes_argumentos_ensino = InformacaoArgumento.objects.filter(argumento=argumento_ensino, registro_atividade__in=registro_atividade)
        disc = []
        for info in informacoes_argumentos_ensino:
            texto = info.valor_texto.split("(")[0].strip()

            if texto not in disc:
                disc.append(texto)

        return len(disc)

    def qtd_cursos(self):
        atividade_ensino = Atividade.objects.get(descricao='Aula')
        argumento_ensino = ArgumentoCategoria.objects.get(categoria_atividade=atividade_ensino.categoria_atividade, campo='Disciplina')
        registro_atividade = RegistroAtividade.objects.filter(atividade=atividade_ensino, processo=self)
        informacoes_argumentos_ensino = InformacaoArgumento.objects.filter(argumento=argumento_ensino, registro_atividade__in=registro_atividade)
        disc = []
        for info in informacoes_argumentos_ensino:
            texto = info.valor_texto.split(":")[0].strip()

            if texto not in disc:
                disc.append(texto)

        return len(disc)

    def qtd_cursos_por_tipo(self, tipo):
        atividade_ensino = Atividade.objects.get(descricao='Aula')
        argumento_ensino_disciplina = ArgumentoCategoria.objects.get(categoria_atividade=atividade_ensino.categoria_atividade, campo='Disciplina')
        argumento_ensino_tipo_curso = ArgumentoCategoria.objects.get(categoria_atividade=atividade_ensino.categoria_atividade, campo='Tipo de curso')
        registro_atividade = RegistroAtividade.objects.filter(atividade=atividade_ensino, processo=self)
        informacoes_argumentos_ensino_disciplina = InformacaoArgumento.objects.filter(argumento=argumento_ensino_disciplina, registro_atividade__in=registro_atividade)
        informacoes_argumentos_ensino_tipo_curso = InformacaoArgumento.objects.filter(argumento=argumento_ensino_tipo_curso, registro_atividade__in=registro_atividade)

        disc = []
        for info in informacoes_argumentos_ensino_disciplina:
            for ifo in informacoes_argumentos_ensino_tipo_curso:
                if info.registro_atividade == ifo.registro_atividade:
                    texto = info.valor_texto.split(":")[0].strip()
                    if tipo == ifo.valor_texto:
                        if texto not in disc:
                            disc.append(texto)

        return len(disc)

    def qtd_turma_por_tipo_curso(self, tipo):
        atividade_ensino = Atividade.objects.get(descricao='Aula')
        argumento_ensino_disciplina = ArgumentoCategoria.objects.get(categoria_atividade=atividade_ensino.categoria_atividade, campo='Disciplina')
        argumento_ensino_tipo_curso = ArgumentoCategoria.objects.get(categoria_atividade=atividade_ensino.categoria_atividade, campo='Tipo de curso')

        registro_atividade = RegistroAtividade.objects.filter(atividade=atividade_ensino, processo=self)
        informacoes_argumentos_ensino_disciplina = InformacaoArgumento.objects.filter(argumento=argumento_ensino_disciplina, registro_atividade__in=registro_atividade)
        informacoes_argumentos_ensino_tipo_curso = InformacaoArgumento.objects.filter(argumento=argumento_ensino_tipo_curso, registro_atividade__in=registro_atividade)

        disc = []
        for info in informacoes_argumentos_ensino_disciplina:
            for ifo in informacoes_argumentos_ensino_tipo_curso:
                if info.registro_atividade == ifo.registro_atividade:
                    texto = info.valor_texto.split(":")[1].strip()
                    if tipo == ifo.valor_texto or tipo in ifo.valor_texto:
                        if texto not in disc:
                            disc.append(texto)

        return len(disc)

    def timeline(self):
        timeline = []
        criacao = {}
        criacao['data'] = self.criado_em
        criacao['autor'] = self.criado_por.get_full_name()
        criacao['descricao'] = 'Criação do processo.'
        timeline.append(criacao)
        tramites = Tramite.objects.filter(processo=self)

        for t in tramites: 
            registro = {}
            registro['data'] = t.data_envio
            registro['autor'] = t.origem()
            registro['descricao'] = f"{self} enviado para {t.destino()}"
            if t.data_recebimento:
                registro['recebimento'] = f"{self} recebido em {t.data_recebimento.strftime('%d/%m/%Y %H:%M')}"
            timeline.append(registro)
        return timeline

    def get_interessado(self):
        if self.interessado:
            return self.interessado
        return self.unidade_interessada

    def alertas(self):
        msgs = []
        for k, v in self.subtotal_ch_semanal_tipo_atividade().items():
            if k.is_restricao_ch_semanal:
                limitacao = k.carga_horaria_semanal_categoria_atividade.filter(grupo_docente=self.interessado.grupo).first()
                if limitacao.ch_minima > 0 and v < limitacao.ch_minima:
                    msgs.append(f"A carga horária mínima semanal das suas {k.label} para o {self.interessado.grupo} está abaixo da regulamentada, que é de {limitacao.ch_minima} horas.")

        if self.ch_semanal_total() != self.interessado.grupo.ch_semanal:
            msgs.append(f"A carga horária semanal do seu {self.tipo_processo} está diferente da regulamentada para o seu grupo, que é de {self.interessado.grupo.ch_semanal} horas.")

        return msgs


@receiver(pre_delete, sender=Processo)
def validar_deleta_processo(sender, instance, **kwargs):
    if not instance.situacao.slug == 'rascunho':
        raise ValidationError('Só processos em rascunho podem ser deletados.')
    else:
        pass


class RegistroAtividade(models.Model):
    AGUARDANDO_VALIDACAO = 'AGUARDANDO_VALIDACAO'
    VALIDA = 'VALIDA'
    INVALIDA = 'INVALIDA'
    EDITADA = 'EDITADA'
    atividade = models.ForeignKey(Atividade, related_name='registros_atividade', on_delete=models.PROTECT)
    descricao = models.TextField('Descrição da Atividade', blank=True)
    ch_semanal = models.DecimalField('Carga horária semanal', max_digits=10, decimal_places=2)
    processo = models.ForeignKey(Processo, related_name='registros_atividade', on_delete=models.CASCADE)
    is_editavel = models.BooleanField('Editável?', default=True, help_text='Indica que a \
        atividade será tratada como editável.')
    is_obrigatorio = models.BooleanField('Atividade obrigatória?', default=False, help_text='Indica que a \
        atividade será tratada como obrigatória para o processo.')
    # Avaliação
    situacao = models.CharField('Situação atividade', max_length=30, choices=TIPO_STATUS_REGISTRO, default=AGUARDANDO_VALIDACAO)
    justificativa = models.TextField('Justificativa', blank=True, help_text='Caso a atividade seja inválida justifique')
    avaliador = models.ForeignKey('authentication.ServidorProfile', on_delete=models.PROTECT, related_name='registro_atividades', blank=True, null=True)
    data_avaliacao = models.DateTimeField('Data da avaliacao', blank=True, null=True)

    objects = RegistroAtividadeQuerySet.as_manager()

    class Meta:
        verbose_name = 'Registro da Atividade'
        verbose_name_plural = 'Registros das atividades'
        db_table = 'regitro_atividade'

    def __str__(self):
        return '%s, com carga horária semanal de %s' % (self.atividade, str(self.ch_semanal))

    def argumentos(self):
        return ', '.join([str(i) for i in self.informacoes_argumentos.all()])
    argumentos.short_description = "Argumentos do Registro da Atividade"


class InformacaoArgumento(models.Model):
    argumento = models.ForeignKey(ArgumentoCategoria, related_name='informacoes_argumentos', on_delete=models.PROTECT)
    valor_texto = models.TextField('Valor da informação em Texto', blank=True)
    valor_inteiro = models.IntegerField('Valor da informação em Número Inteiro', blank=True, null=True)
    valor_decimal = models.DecimalField('Valor da informação em Número Decimal', decimal_places=2, max_digits=10, blank=True, null=True)
    valor_data = models.DateField('Valor da informação em Data', blank=True, null=True)
    valor_hora = models.TimeField('Valor da informação em Hora', blank=True, null=True)
    valor_data_hora = models.DateTimeField('Valor da informação em Data/Hora', blank=True, null=True)
    valor_boolean = models.NullBooleanField('Valor da informação Verdadeiro ou Falso')
    valor_arquivo = models.FileField('Valor da informação Arquivo', upload_to = 'arquivos/', blank=True, null=True)
    registro_atividade = models.ForeignKey(RegistroAtividade, on_delete=models.CASCADE, related_name='informacoes_argumentos')

    objects = InformacaoArgumentoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Informação do Argumento'
        verbose_name_plural = 'Informações dos Argumentos'
        db_table = 'informacao_argumento'

    def __str__(self):
        if self.argumento.tipo_dado == 'TEXTO':
            return '{}: {}'.format(self.argumento, self.valor_texto)
        elif self.argumento.tipo_dado == 'INTEIRO':
            return '{}: {}'.format(self.argumento, self.valor_inteiro)
        elif self.argumento.tipo_dado == 'DECIMAL':
            return '{}: {}'.format(self.argumento, localize(self.valor_decimal))
        elif self.argumento.tipo_dado == 'BOOLEAN':
            return '{}: {}'.format(self.argumento, 'Sim' if self.valor_boolean else 'Não')
        elif self.argumento.tipo_dado == 'DATA':
            return '{}: {}'.format(self.argumento, localize(self.valor_data))
        elif self.argumento.tipo_dado == 'HORA':
            return '{}: {}'.format(self.argumento, self.valor_hora)
        elif self.argumento.tipo_dado == 'DATA_HORA':
            return '{}: {}'.format(self.argumento, self.valor_data_hora)

    def valor_argumento(self):
        if self.argumento.tipo_dado == 'TEXTO':
            return self.valor_texto
        elif self.argumento.tipo_dado == 'INTEIRO':
            return self.valor_inteiro
        elif self.argumento.tipo_dado == 'DECIMAL':
            return str(localize(self.valor_decimal))
        elif self.argumento.tipo_dado == 'BOOLEAN':
            return self.valor_boolean
        elif self.argumento.tipo_dado == 'DATA':
            return self.valor_data
        elif self.argumento.tipo_dado == 'HORA':
            return self.valor_hora
        elif self.argumento.tipo_dado == 'DATA_HORA':
            return self.valor_data_hora


class Assinatura(models.Model):
    data_assinatura = models.DateTimeField(auto_now_add=True)
    servidor_assinante = models.ForeignKey('authentication.ServidorProfile', on_delete=models.PROTECT, related_name='assinaturas')
    is_autenticador = models.BooleanField('Autenticador?', default=False)

    # Below the mandatory fields for generic relation
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    class Meta:
        ordering = ['data_assinatura']
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        db_table = 'assinatura'

    def __str__(self):
        return f'{self.servidor_assinante} (Autenticador?: {self.is_autenticador}) - {self.data_assinatura}'


class DocumentoProcesso(Auditavel):
    SOLICITACAO = 'SOLICITACAO'
    PARECER = 'PARECER'
    DESPACHO = 'DESPACHO'
    processo = models.ForeignKey(Processo, related_name='documentos_processo', on_delete=models.PROTECT)
    titulo = models.CharField('Título', max_length=255, blank=True)
    tipo_documento = models.CharField('Tipo do documento', max_length=20, choices=TIPO_DOCUMENTO, default=PARECER)
    texto = RichTextField(('Texto'), null=True, blank=True)
    arquivo = models.FileField('Arquivo', upload_to='documentos/', blank=True, null=True)

    assinaturas = GenericRelation(Assinatura, related_name='documentos_processo')

    class Meta:
        verbose_name = 'Documento do processo'
        verbose_name_plural = 'Documentos dos processos'
        db_table = 'documento_processo'

    def __str__(self):
        return f'{self.get_tipo_documento_display()}, {self.titulo} do {self.processo}'

    def assinaturas_lista(self):
        return ', '.join([str(a) for a in self.assinaturas.all()])
    assinaturas_lista.short_description = "Assinaturas associados ao documento"


class Tramite(models.Model):
    # origem do processo
    processo = models.ForeignKey(Processo, related_name='tramites', on_delete=models.PROTECT)
    servidor_origem = models.ForeignKey('authentication.ServidorProfile', on_delete=models.PROTECT, related_name='tramites_origem')
    unidade_origem = models.ForeignKey(EstruturaOrganizacional, on_delete=models.PROTECT, related_name='tramites_origem')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_envio = models.DateTimeField('Data de envio do processo', blank=True, null=True)
    # destino do processo
    servidor_destino = models.ForeignKey('authentication.ServidorProfile', on_delete=models.PROTECT, related_name='tramites_destino', blank=True, null=True)
    unidade_destino = models.ForeignKey(EstruturaOrganizacional, on_delete=models.PROTECT, related_name='tramites_destino', blank=True, null=True)
    data_recebimento = models.DateTimeField('Data do recebimento do processo', blank=True, null=True)
    servidor_recebimento = models.ForeignKey('authentication.ServidorProfile', on_delete=models.PROTECT, related_name='tramites_recebimento', blank=True, null=True)

    assinaturas = GenericRelation(Assinatura)

    objects = TramiteQuerySet.as_manager()

    class Meta:
        ordering = ['processo', 'data_criacao', 'data_envio']
        verbose_name = 'Tramitação de processo'
        verbose_name_plural = 'Tramitação de processos'
        db_table = 'tramite'

    def __str__(self):
        return f'{self.processo}: {self.unidade_origem} -> {self.unidade_destino}'

    def origem(self):
        if self.unidade_origem:
            return f"{self.servidor_origem.pessoa.user.get_full_name()} ({self.servidor_origem.siape}) - {self.unidade_origem}"

        return f"{self.servidor_origem.pessoa.user.get_full_name()} ({self.servidor_origem.siape})"

    def destino(self):
        if self.servidor_destino:
            if self.unidade_destino:
                return f"{self.servidor_destino.pessoa.user.get_full_name()} ({self.servidor_origem.siape}) - {self.unidade_destino}"
            return f"{self.servidor_destino.pessoa.user.get_full_name()} ({self.servidor_origem.siape})"

        return f"{self.unidade_destino}"
