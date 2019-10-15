from django.db import models
from django.db.models import Q


class EstruturaOrganizacionalQuerySet(models.QuerySet):
    def encontra_por_nome(self, nome):
        return self.filter((Q(nome__icontains=nome) | Q(sigla=nome)) | (Q(estrutura_pai__nome__icontains=nome) | Q(estrutura_pai__sigla=nome)))


class ResponsavelUnidadeQuerySet(models.QuerySet):
    def chefe(self):
        return self.filter(data_termino__isnull=True, nivel_responsabilidade=self.model.CHEFE)

    def vice_chefe(self):
        return self.filter(data_termino__isnull=True, nivel_responsabilidade=self.model.VICE_CHEFIA)

    def responde_por(self):
        return self.filter(Q(data_termino__isnull=True) & (Q(nivel_responsabilidade=self.model.CHEFE) | Q(nivel_responsabilidade=self.model.VICE_CHEFIA)))

    def ativo(self):
        return self.filter(data_termino__isnull=True)


class VinculoServidorUnidadeQuerySet(models.QuerySet):
    def chefe(self):
        return self.filter(is_ativo=True, tipo_vinculo=self.model.PRESIDENTE)

    def vice_chefe(self):
        return self.filter(is_ativo=True, tipo_vinculo=self.model.VICE_PRESIDENTE)

    def responde_por(self):
        return self.filter(Q(is_ativo=True) & (Q(tipo_vinculo=self.model.PRESIDENTE) | Q(tipo_vinculo=self.model.VICE_PRESIDENTE)))

    def ativo(self):
        return self.filter(is_ativo=True)


class AtividadeQuerySet(models.QuerySet):
    def encontra_por_categoria(self, categoria):
        return self.filter(categoria_atividade=categoria, is_ativo=True)


class RegistroAtividadeQuerySet(models.QuerySet):
    def encontra_por_categoria(self, categoria):
        return self.filter(atividade__categoria_atividade=categoria)

    def encontra_por_categoria_ou_categoria_pai(self, categoria):
        return self.filter(Q(atividade__categoria_atividade=categoria) | Q(atividade__categoria_atividade__categoria_pai=categoria))

    def encontra_por_atividade(self, atividade):
        return self.filter(atividade=atividade)

    def invalida(self):
        return self.filter(situacao=self.model.INVALIDA)


class InformacaoArgumentoQuerySet(models.QuerySet):
    def encontra_por_campo(self, campo):
        return self.filter(argumento__campo=campo)

    def encontra_por_processo(self, processo):
        return self.filter(registro_atividade__processo=processo)


class UnidadeFluxoProcessoQuerySet(models.QuerySet):
    def avaliadora(self):
        return self.filter(is_avaliadora=True, is_ativo=True)

    def ativo(self):
        return self.filter(is_ativo=True)


class ProcessoQuerySet(models.QuerySet):
    RASCUNHO = 'rascunho'
    ALTERACOES_NECESSARIAS = 'alteracoes-necessarias'

    def rascunho(self):
        return self.filter(situacao__slug=self.RASCUNHO)

    def editavel(self):
        return self.filter(Q(situacao__slug=self.RASCUNHO) | Q(situacao__slug=self.ALTERACOES_NECESSARIAS))

    def encontra_por_ano_ou_semestre(self, ano, semestre):
        return self.filter(Q(ano=ano) | Q(semestre=semestre))

    def encontra_por_ano(self, ano):
        return self.filter(ano=ano)

    def encontra_por_semestre(self, semestre):
        return self.filter(semestre=semestre)

    def encontra_por_tipo_ou_assunto(self, tipo, assunto):
        return self.filter(Q(tipo_processo__nome__icontains=tipo) | Q(assunto__icontains=assunto))

    def pesquisaveis(self):
        return self.all().exclude(situacao__slug=self.RASCUNHO)


class TramiteQuerySet(models.QuerySet):
    def ultima_movimentacao(self):
        return self.last()


class FluxoProcessoQuerySet(models.QuerySet):
    def fluxo_principal(self):
        return self.filter(is_ativo=True, tipo_fluxo=self.model.PRINCIPAL)


class SituacaoProcessoQuerySet(models.QuerySet):
    ENVIADO = 'enviado'
    RECEBIDO = 'recebido'
    ALTERACOES_NECESSARIAS = 'alteracoes-necessarias'
    ENVIO_RECUSADO = 'envio-recusado'

    def enviado(self):
        return self.get(slug=self.ENVIADO)

    def recebido(self):
        return self.get(slug=self.RECEBIDO)

    def alteracoes_necessarias(self):
        return self.get(slug=self.ALTERACOES_NECESSARIAS)

    def envio_recusado(self):
        return self.get(slug=self.ENVIO_RECUSADO)
