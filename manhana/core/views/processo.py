import json
import logging
from datetime import datetime as dt
from pprint import pprint

import requests
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import (LoginRequiredMixin,
                                        PermissionRequiredMixin)
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.base import RedirectView
from django.views.generic.edit import UpdateView
from validate_email import validate_email

from manhana.authentication.models import *
from manhana.core.filters import ProcessoFilter
from manhana.core.forms.principal import ConfirmPasswordForm
from manhana.core.forms.processo import *
from manhana.core.models.parametro import *
from manhana.core.models.processo import *
from manhana.core.services import *

# Create a custom logger
logger = logging.getLogger(__name__)


# Create your views here.
class AuditableMixin(object):
    def form_valid(self, form):
        if not form.instance.criado_por:
            form.instance.criado_por = self.request.user
        form.instance.modificado_por = self.request.user
        return super(AuditableMixin, self).form_valid(form)


class ProcessoNovoView(LoginRequiredMixin, SuccessMessageMixin, generic.CreateView):
    model = Processo
    form_class = ProcessoForm
    template_name = 'core/processo/novo.html'
    success_message = "Processo criado com sucesso."

    def form_valid(self, form):
        try:
            if not self.request.session['tipo_perfil']:
                logger.warning('O usuário %s não está com o perfil registrado na sessão', self.request.user)
                return redirect('auth:selecao_perfil')
            else:
                if self.request.session['tipo_perfil'] != 'Docente':
                    messages.error(self.request, 'Só usuários com vínculo de Docente podem criar um novo registro.')
                    logger.error("O usuário '%s' do tipo %s tem tentou criar um processo mas não conseguiu, pois só usuários com vínculo de Docente podem criar um novo registro." % (self.request.user, self.request.session['tipo_perfil']))
                else:
                    perfil = DocenteProfile.objects.get(pk=self.request.session['perfil'])

                    self.object = form.save(commit=False)
                    self.object.interessado = perfil
                    self.object.criado_por = self.request.user
                    self.object.modificado_por = self.request.user
                    self.object.save()
                    logger.info("O usuário '%s' criou o processo '%s'" % (self.request.user, str(self.object)))
                    return redirect('core:processo-editar', pk=self.object.pk)

        except IntegrityError as e:
            # personaliza mensagem da restrição unique_together
            if 'UNIQUE constraint' in str(e):
                messages.error(self.request, 'Não é possível criar um novo registro: Só pode ser criado um %s para %d/%d' % (self.object.tipo_processo, self.object.ano, self.object.semestre))            
                logger.exception('Ocorreu uma exceção: Não é possível criar um novo registro: Só pode ser criado um %s para %d/%d' % (self.object.tipo_processo, self.object.ano, self.object.semestre))
        except Exception as ex:
            messages.error(self.request, 'Não é possível criar um novo registro: %s' % str(ex))
            logger.exception('Ocorreu uma exceção: Não é possível criar um novo registro: %s' % str(ex))

        return render(self.request, self.template_name, self.get_context_data())    

    def get_context_data(self, **kwargs):
        context = super(ProcessoNovoView, self).get_context_data(**kwargs)
        logger.info(f'O usuário {self.request.user} acessou o formulário de criação de um processo.')
        context['progress'] = 10
        return context


class ProcessoDetalheView(LoginRequiredMixin, generic.DetailView):
    model = Processo
    context_object_name = 'processo'
    template_name = 'core/processo/detalhe.html'

    processo = Processo()
    registro = RegistroAtividade()
    informacao = InformacaoArgumento()

    @property
    def processo_id(self):
        return int(self.kwargs['pk'])

    @property
    def servidor(self):
        return get_object_or_404(ServidorProfile, pk=self.request.session['perfil'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.processo = get_object_or_404(Processo, pk=self.processo_id)
        context['processo'] = self.processo
        # carrega por padrão os dados da categoria Atividades de Ensino
        try:
            tipo_atividade = CategoriaAtividade.objects.get(slug='atividades-de-ensino')
            self.registro = self.processo.registros_atividade.encontra_por_categoria(tipo_atividade).prefetch_related('informacoes_argumentos')
            context['registros'] = self.registro
        except CategoriaAtividade.DoesNotExist as e:
            context['registros'] = None

        context['categorias_atividades'] = self.processo.tipo_processo.categoria_atividade.all()
        context['editando'] = False
        if self.servidor == self.processo.interessado:
            context['is_interessado'] = True
        return context


class EditarProcessoView(LoginRequiredMixin, generic.View):
    template_name = 'core/processo/adicionar_atividades.html'
    context = {}
    processo = Processo()
    registro = RegistroAtividade()
    informacao = InformacaoArgumento()

    @property
    def processo_id(self):
        return int(self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.carregar_context(request)
        logger.info("O usuário '%s' acessou o processo '%s' para editar as atividades." % (request.user, str(self.processo)))

        # Verifica se o usuário logado é o interessado do processo
        user = request.user
        if user == self.processo.interessado.pessoa.user or user == self.processo.criado_por:
            # Verifica se processo não está com a situação: rascunho, alterações necessárias, envio recusado
            if self.processo.situacao.slug not in ('rascunho', 'alteracoes-necessarias', 'envio-recusado'):
                messages.error(request, 'Somente processo com situação RASCUNHO, ALTERAÇÕES NECESSÁRIAS ou ENVIO RECUSADO pode ser editado!')
                logger.warning(f"O usuário '{user}' tentou editar o processo '{self.processo}' que tem situação '{self.processo.situacao.nome}'.")
                return redirect('core:caixa-entrada')
        else:
            messages.error(request, 'Só o criador ou interessado pode Editar o processo!')
            logger.warning(f"O usuário '{user}' tentou editar o {self.processo} que foi criado por '{self.processo.criado_por}' e tem como interessado o '{self.processo.interessado}'.")
            return redirect('core:caixa-entrada')

        # Imprime alertas do processo
        for msg in self.processo.alertas():
            messages.add_message(request, messages.WARNING, msg)

        # Dá o recebimento no processo
        if self.processo.tramites.ultima_movimentacao():
            tramite = self.processo.tramites.ultima_movimentacao()
            tramite.data_recebimento = dt.now()
            tramite.servidor_recebimento = ServidorProfile.objects.get(pessoa__user=request.user)
            tramite.save()

        return render(request, self.template_name, self.context)

    def post(self, request, *args, **kwargs):
        return render(request, self.template_name, self.context)

    def carregar_context(self, request):
        self.processo = get_object_or_404(Processo, pk=self.processo_id)
        self.context['processo'] = self.processo
        # Carrega por padrão os dados da categoria Atividades de Ensino
        try:
            tipo_atividade = CategoriaAtividade.objects.get(slug='atividades-de-ensino')
            self.registro = self.processo.registros_atividade.encontra_por_categoria(tipo_atividade).prefetch_related('informacoes_argumentos')
            self.context['registros'] = self.registro
        except CategoriaAtividade.DoesNotExist as e:
            self.context['registros'] = None

        self.context['categorias_atividades'] = self.processo.tipo_processo.categoria_atividade.all()
        self.context['editando'] = True


class CaixaEntradaView(LoginRequiredMixin, generic.ListView):
    model = Processo
    context_object_name = 'processo_list'
    paginate_by = 10
    template_name = 'core/processo/caixa_entrada.html'

    def get_queryset(self):
        nome = self.request.GET.get('nome', '')
        servidor = get_object_or_404(ServidorProfile, pk=self.request.session['perfil'])

        vinculos = servidor.vinculos_unidade.ativo()

        lista_processos = []
        # Monta lista de ID's dos processos relacionados a unidade a qual o servidor está vinculado
        for v in vinculos:
            # Monta lista de ID's dos processos que tem como unidade interessada a unidade a qual o servidor está vinculado
            proc_l = Processo.objects.rascunho().filter(unidade_interessada=v.unidade)
            for p in proc_l:
                if p not in lista_processos:
                    lista_processos.append(p.id)
            # Monta lista de ID's dos processos que foram enviados para unidade a qual o servidor está vinculado
            tramites = Tramite.objects.filter(unidade_destino=v.unidade)
            for t in tramites:
                if t.processo.tramites.ultima_movimentacao().unidade_destino == v.unidade:
                    if t.processo not in lista_processos:
                        lista_processos.append(t.processo.id)

        funcoes_gratificadas = servidor.responsaveis_unidade.responde_por()
        # Monta lista de ID's dos processos relacionados a unidade a qual o servidor responde como chefe ou vice
        for fg in funcoes_gratificadas:
            procfg_l = Processo.objects.rascunho().filter(unidade_interessada=fg.unidade)
            # Monta lista de ID's dos processos que tem como unidade interessada a unidade a qual o servidor responde como chefe ou vice
            for p in procfg_l:
                if p not in lista_processos:
                    lista_processos.append(p.id)

            tramites = Tramite.objects.filter(unidade_destino=fg.unidade)
            # Monta lista de ID's dos processos que foram enviados para unidade a qual o servidor responde como chefe ou vice
            for t in tramites:
                if t.processo.tramites.ultima_movimentacao().unidade_destino == fg.unidade:
                    if t.processo not in lista_processos:
                        lista_processos.append(t.processo.id)

        tramites = Tramite.objects.filter(servidor_destino=servidor)
        # Monta lista de ID's dos processos que foram enviados para o servidor
        for t in tramites:
            if t.processo.tramites.ultima_movimentacao().servidor_destino == servidor:
                if t.processo not in lista_processos:
                    lista_processos.append(t.processo.id)

        # Busca os processo com a lista de ID's montada acima
        all_processos = self.model.objects.filter(id__in=lista_processos)
        # faz filtro nos processos que o usuário é o interessado
        processo_pessoal = self.model.objects.editavel().encontra_por_tipo_ou_assunto(tipo=nome, assunto=nome).filter(Q(interessado__pessoa=self.request.user.pessoa))

        # verifica se a string de busca possui uma /
        if '/' in nome:
            s = nome.split('/')
            if s[0].isdigit() and s[1].isdigit():
                ano = int(s[0])
                semestre = int(s[1])
                processo_pessoal = processo_pessoal.encontra_por_ano(ano=ano).encontra_por_semestre(semestre=semestre)
                # junta os filtros com OU
                return processo_pessoal | all_processos.encontra_por_tipo_ou_assunto(tipo=nome, assunto=nome) | all_processos.encontra_por_ano(ano=ano).encontra_por_semestre(semestre=semestre)
            else:
                if s[0].isdigit():
                    ano = int(s[0])
                    processo_pessoal = processo_pessoal.encontra_por_ano_ou_semestre(ano=ano, semestre=ano)
                    # junta os filtros com OU
                    return processo_pessoal | all_processos.encontra_por_tipo_ou_assunto(tipo=nome, assunto=nome) | all_processos.encontra_por_ano_ou_semestre(ano=ano, semestre=ano)
                if s[1].isdigit():
                    semestre = int(s[1])
                    processo_pessoal = processo_pessoal.encontra_por_ano_ou_semestre(ano=semestre, semestre=semestre)
                    # junta os filtros com OU
                    return processo_pessoal | all_processos.encontra_por_tipo_ou_assunto(tipo=nome, assunto=nome) | all_processos.encontra_por_ano_ou_semestre(ano=semestre, semestre=semestre)

        # verifica se a string de busca só contem números
        if nome.isdigit():
            processo_pessoal = processo_pessoal.encontra_por_ano_ou_semestre(ano=int(nome), semestre=int(nome))
            # junta os filtros com OU
            return processo_pessoal | all_processos.encontra_por_ano_ou_semestre(ano=int(nome), semestre=int(nome))

        return processo_pessoal | all_processos.encontra_por_tipo_ou_assunto(tipo=nome, assunto=nome)

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)


@login_required
def excluir_processo(request):
    if request.method == 'POST':
        id = request.POST.get('idprocesso')
        processo = get_object_or_404(Processo, pk=id)
        user = request.user 
        logger.info(f'O usuário {user} solicitou o exclusão do processo {processo}.')
        try:
            # verifica se o usuario é o interessado ou o criador
            if user == processo.interessado.pessoa.user or user == processo.criado_por:
                # só pode excluir o processo se estiver com situação igual a RASCUNHO
                if processo.situacao.slug == 'rascunho':
                    processo.delete()
                    logger.info("O usuário '%s' excluiu o processo '%s'" % (request.user, processo))
                    messages.success(request, 'Processo excluído com sucesso!')
                else:
                    messages.error(request, 'Somente processo com situação RASCUNHO pode ser excluído!')
                    logger.warning(f"O usuário '{user}' tentou excluir o processo '{processo}' que tem situação '{processo.situacao.nome}'.")
            else:
                messages.error(request, 'Só o criador pode Excluir o processo!')
                logger.warning(f"O usuário '{user}' tentou excluir o processo '{processo}' que foi criado por '{processo.criado_por}' e tem como interessado o '{processo.interessado}'.")
        except Exception as ex:
            messages.error(request, 'Não é possível excluir o registro: %s' % str(ex))
            logger.exception('Ocorreu uma exceção: Não é possível excluir o registro: %s' % str(ex))

    return redirect('core:caixa-entrada')


class VerificarCategoriaAtividadeImportacaoView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        processo = get_object_or_404(Processo, pk=kwargs['pk'])
        slug = kwargs['slug']
        if slug == 'atividades-de-ensino':
            return reverse('core:importar_atividade_ensino', kwargs={'pk' :processo.pk})
        elif slug == 'atividades-de-gestao':
            return reverse('core:importar_atividade_gestao', kwargs={'pk' :processo.pk})


class VerificarCategoriaAtividadeNovoView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        processo = get_object_or_404(Processo, pk=kwargs['pk'])
        slug = kwargs['slug']
        if 'atividade' in slug:
            return reverse('core:verificar-atividades-obrigatorias', kwargs={'pk' :processo.pk, 'slug': slug})
        elif 'projeto' in slug:
            return reverse('core:projeto-novo', kwargs={'pk' :processo.pk, 'slug': slug})


@login_required
def importar_atividade_ensino(request, pk):
    importSig = ImportarInformacoesSIG()
    processo = get_object_or_404(Processo, pk=pk)
    logger.info(f"O usuário '{request.user}' solicitou a importação das suas turmas ABERTAS do SIGAA para ser inserida nas atividades de ensino do PIT do processo {processo}.")
    try:
        # Importa as turmas da API do SIGAA
        resultado = importSig.importar_disciplina(processo.interessado, processo.ano)
        # Chama a função para limpar a lista das disciplinas importadas
        disciplinas = limpar_disciplinas_importadas(resultado, processo.semestre)
        logger.info("Para o usuario '%s' foram encontradas %d turmas ABERTAS no SIGAA com os seguintes parametros de buscas: %s (docente), %d (ano) e %d (semestre)." % (request.user, resultado['meta']['total_count'], processo.interessado, processo.ano, processo.semestre))
        messages.success(request, 'Disciplinas encontradas com sucesso.')
        return render(request, 'core/processo/atividades/importar_atividades_ensino.html', {'processo': processo, 'disciplinas': disciplinas,})
    except Exception as ex:
        messages.error(request, 'Não é possível encontrar os registros: %s' % str(ex))
        logger.exception('Ocorreu uma exceção: Não é possível encontrar os registros: %s' % str(ex))

    return render(request, 'core/processo/atividades/importar_atividades_ensino.html', {'processo': processo, 'disciplinas': resultado['objects'],})


def limpar_disciplinas_importadas(resultado, semestre):
    disciplina = []
    for r in resultado['objects']:
        if r['nivel'] != 'INTEGRADO':
            if r['periodo'] == semestre:
                disciplina.append(r)
        else:
            disciplina.append(r)
    return disciplina


@login_required
@transaction.atomic
def importar_atividade_gestao(request, pk):
    processo = get_object_or_404(Processo, pk=pk)
    logger.info(f"O usuário '{request.user}' solicitou a importação de atividade de gestão ATIVAS para ser inserida nas atividades de gestão do PIT do processo {processo}.")
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])
    # verifica se o usuário é chefe de algum setor
    if servidor.responsaveis_unidade.chefe().exists():
        try:
            responsavel = servidor.responsaveis_unidade.chefe().first()
            logger.info(f"Para o usuario '{request.user}' foi encontrada a seguinte unidade na qual ele é responsável: {responsavel.unidade.nome}" )
            messages.success(request, 'Unidade responsável por vossa gestão localizada com sucesso.')
            # busca a categoria Gestão
            tipo_atividade = get_object_or_404(CategoriaAtividade, slug='atividades-de-gestao')
            # inicia o form com os dados
            form = RegistroAtividadeForm(initial={'processo': processo,'descricao': responsavel.get_nivel_responsabilidade_display() + ': ' + responsavel.unidade.sigla + ' - ' + responsavel.unidade.nome})
            # filtra a listagem do select pela atividades da categoria Gestão
            form.fields['atividade'].queryset = Atividade.objects.encontra_por_categoria(tipo_atividade)
        except Exception as ex:
            messages.error(request, 'Não é possível encontrar os registros: %s' % str(ex))
            logger.exception('Ocorreu uma exceção: Não é possível encontrar os registros: %s' % str(ex))
    else:
        messages.warning(request, 'Não foi localizada nenhuma atividade de gestão em que você esteja inserido!')
        logger.info(f"Não foi localizada nenhuma atividade de gestão para o usuario '{request.user}'" )
        return HttpResponseRedirect(reverse('core:processo-editar', kwargs={'pk' :processo.pk}))

    if request.method == 'POST':
        try:
            form = RegistroAtividadeForm(request.POST)
            if form.is_valid():                
                registro = form.save(commit=False)
                # verifica se já foi cadastrada a atividade no processo
                if not processo.registros_atividade.encontra_por_atividade(registro.atividade).exists():
                    registro.save()
                    processo.save()
                    messages.success(request, 'Atividade de gestão importada com sucesso!')
                    return HttpResponseRedirect(reverse('core:processo-editar', kwargs={'pk' :processo.pk}))
                else:
                    messages.warning(request, 'Atividade de gestão já importada!')
        except Exception as ex:
            messages.error(request, f'Não é possível importar a atividade de gestão, pois: {ex}')
            logger.exception(f'Ocorreu uma exceção: Não é possível importar a atividade de gestão, pois: {ex}')
    
    return render(request, 'core/processo/atividades/importar_atividade_gestao.html', {'processo': processo, 'responsavel': responsavel, 'form': form, 'tipo_atividade': tipo_atividade})


@login_required
@transaction.atomic
def importar_disciplinas(request, pk):
    if request.method == 'POST':
        processo = get_object_or_404(Processo, pk=pk)
        logger.info(f"O usuário '{request.user}' concordou em importar as turmas ABERTAS encontradas no SIGAA para o processo {processo}.")
        importSig = ImportarInformacoesSIG()
        arredondamento = Arredondamento()
        # importa as disciplinas da API do SIGAA
        resultado = importSig.importar_disciplina(processo.interessado, processo.ano)
        add = 0
        alt = 0
        if resultado:
            if resultado['objects']:
                # limpa as disciplinas importadas
                disciplinas = limpar_disciplinas_importadas(resultado, processo.semestre)
                for r in disciplinas:
                    # Monta os campos a ser salvos para cada disciplina
                    if r['curso']['nivel'] == 'TÉCNICO':
                        tipo_curso = r['curso']['nivel']  + ' - ' + r['curso']['tipo_tecnico']
                    else:
                        tipo_curso = r['curso']['nivel']
                    disciplina = r['curso']['nome'] + ': ' + r['componente_curricular'] + ' ('+r['turma']+'/'+r['tipo_turma']+')'
                    horario = r['horario']
                    campus = r['curso']['unidade_responsavel']
                    atividade = Atividade.objects.get(descricao='Aula')
                    periodo_letivo = f"{r['ano']}/{r['periodo']}" 
                    ch_diciplina = Decimal(r['carga_horaria'])
                    ch_docente = Decimal(r['carga_horaria_docente'])
                    argumento = atividade.categoria_atividade.argumentos.all()

                    # Verifica se a turma já foi cadastrada no processo pelas informações dos campos adicionais
                    atividade_existe = InformacaoArgumento.objects.encontra_por_processo(processo).encontra_por_campo('Disciplina').filter(valor_texto=disciplina)
                    if not atividade_existe.exists():
                        ch_semanal = CalculaCargahorariaSemanal()
                        qtd_aulas = ch_semanal.calcular_qtdaulas(horario, ch_diciplina, ch_docente)
                        # cria o registro da atividade com os dados comuns a todas atividades e categorias
                        registro_atividade = RegistroAtividade.objects.create(atividade=atividade, processo=processo, ch_semanal=arredondamento.qtd_horas_aula(qtd_aulas), is_obrigatorio=True, is_editavel=False)
                        # Salva as informações dos campos adicionais para cada disciplina
                        for a in argumento:
                            informacao_argumento = InformacaoArgumento()
                            informacao_argumento.argumento = a
                            informacao_argumento.registro_atividade = registro_atividade
                            if a.slug == 'disciplina':
                                informacao_argumento.valor_texto = disciplina
                            if a.slug == 'tipo-de-curso':
                                informacao_argumento.valor_texto = tipo_curso
                            if a.slug == 'horario':
                                informacao_argumento.valor_texto = horario
                            if a.slug == 'quantidade-de-aulas':
                                informacao_argumento.valor_inteiro = qtd_aulas
                            if a.slug == 'campus':
                                informacao_argumento.valor_texto = campus
                            if a.slug == 'periodo-letivo':
                                informacao_argumento.valor_texto = periodo_letivo
                            if a.slug == 'carga-horaria-da-disciplina':
                                informacao_argumento.valor_decimal = ch_diciplina
                            if a.slug == 'carga-horaria-do-docente':
                                informacao_argumento.valor_decimal = ch_docente

                            informacao_argumento.save()
                        add = add + 1
                    else:
                        # Pega o registro da atividade das primeira informação retornada dos campos adicionais
                        registro = atividade_existe.first().registro_atividade
                        
                        # Se o precesso está com situação igual a "Alterações Necessárias" a situação do registro da atividade será "Editada"
                        if processo.situacao.slug == 'alteracoes-necessarias':
                            reg_ativ = registro.registro_atividade
                            reg_ativ.situacao = RegistroAtividade.EDITADA
                            reg_ativ.save()
                            
                        ch_semanal = CalculaCargahorariaSemanal()
                        qtd_aulas = ch_semanal.calcular_qtdaulas(horario)
                        # atualiza as informações dos campos adicionais para cada disciplina
                        for a in argumento:
                            for info in registro.informacoes_argumentos.all():
                                if info.argumento == a:
                                    if a.slug == 'disciplina':
                                        info.valor_texto = disciplina
                                    if a.slug == 'tipo-de-curso':
                                        info.valor_texto = tipo_curso
                                    if a.slug == 'horario':
                                        info.valor_texto = horario
                                    if a.slug == 'quantidade-de-aulas':
                                        info.valor_inteiro = qtd_aulas
                                    if a.slug == 'campus':
                                        info.valor_texto = campus
                                    if a.slug == 'periodo-letivo':
                                        info.valor_texto = periodo_letivo
                                    if a.slug == 'carga-horaria-da-disciplina':
                                        info.valor_decimal = ch_diciplina
                                    if a.slug == 'carga-horaria-do-docente':
                                        info.valor_decimal = ch_docente
                                    info.save()
                        alt = alt + 1

            messages.success(request, f'Importação de atividades de ensino realizada com Sucesso! Foram importadas {add} disciplinas e atualizadas {alt}!') 
            logger.info(f"Importação de atividades de ensino realizada com Sucesso para o processo {processo} do usuario: {request.user}.!\
                Foram importadas {add} disciplinas e atualizadas {alt}!")

            processo.save()
            
            return redirect('core:processo-editar', pk=processo.pk)


@login_required
@transaction.atomic
def excluir_atividade(request):
    if request.method == 'POST':
        idprocesso = request.POST.get('idprocesso')
        processo = Processo.objects.get(id=idprocesso)
        idregistro = request.POST.get('idregistroatividade')
        registro = RegistroAtividade.objects.get(id=idregistro)
        logger.info(f"O usuário {request.user} solicitou a exclusão da atividade {registro.atividade.descricao}\
            do processo {processo}.")

        if not registro.is_obrigatorio:
            try:
                informacao = registro.informacoes_argumentos.all()
                for i in informacao:
                    i.delete()
                registro.delete()
                processo.save()
                messages.success(request, 'Atividade excluída com sucesso!')
                logger.info('Atividade excluída com sucesso!')
            except Exception as ex:
                messages.error(request, f'Não é possível excluir o registro: {ex}')
                logger.exception(f'Ocorreu uma exceção: Não é possível excluir o registro: {ex}')
                return redirect('core:processo-editar', pk=processo.pk)        
        else:
            logger.warning(f"O usuário {request.user} não realizou a exclusão da atividade {registro.atividade.descricao},\
                 pois se trata de uma atividade obrigatória!")
            messages.warning(request, f'A atividade {registro.atividade.descricao} não pode ser excluída por ser Obrigatória!')
    return redirect('core:processo-editar', pk=processo.pk)


@login_required
def detalha_atividade(request, pk):
    data = dict()
    registro = get_object_or_404(RegistroAtividade, pk=pk)
    context = {'registro': registro, 'dados_registro': registro.informacoes_argumentos.all()}
    data['html_form'] = render_to_string('core/ajax/partial_atividade_detalhe.html', context, request=request,)
    return JsonResponse(data)


def cria_contexto_lista_atividades(pk, id_tipo_atividade):
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    tipo_atividade = get_object_or_404(CategoriaAtividade, pk=id_tipo_atividade)
    registros_list = processo.registros_atividade.encontra_por_categoria_ou_categoria_pai(tipo_atividade).prefetch_related('informacoes_argumentos')
    if processo.tramites.ultima_movimentacao():
        unidade_avaliadora = UnidadeFluxoProcesso.objects.avaliadora().filter(unidade=processo.tramites.ultima_movimentacao().unidade_destino).first()
        if unidade_avaliadora:
            context['in_unidade_avaliadora'] = unidade_avaliadora.is_avaliadora
        else:
            context['in_unidade_avaliadora'] = False
    context['registros'] = registros_list
    return context


@login_required
def carregar_lista_atividades_editando(request, pk, id_tipo_atividade):
    data = dict()
    data['html_item_list'] = render_to_string('core/ajax/partial_atividade_list_edit.html', cria_contexto_lista_atividades(pk, id_tipo_atividade), request=request,)
    return JsonResponse(data)


@login_required
def carregar_lista_atividades_detalhe(request, pk, id_tipo_atividade):
    data = dict()
    data['html_item_list'] = render_to_string('core/ajax/partial_atividade_list.html', cria_contexto_lista_atividades(pk, id_tipo_atividade), request=request,)
    return JsonResponse(data)


@login_required
def verifica_atividades_obrigatorias_view(request, pk, slug):
    processo = get_object_or_404(Processo, pk=pk).select_related('registros_atividade')
    tipo_atividade = get_object_or_404(CategoriaAtividade, slug=slug)
    verificar_atividade = VerificarAtividadesObrigatorias()
    atividades_obg = verificar_atividade.verificar_atividades_obrigatorias(processo, tipo_atividade)
    atividades = Atividade.objects.encontra_por_categoria(tipo_atividade)
    ensino = CategoriaAtividade.objects.get(slug='atividades-de-ensino')
    comp_ensino = CategoriaAtividade.objects.get(slug='atividades-complementares-de-ensino')
    logger.info(f'O usuário {request.user} solicitou para adicionar uma atividade da categoria "{tipo_atividade}" no processo {processo}, mas o sistema está verificando se existe atividades obrigatórias a serem inseridas.')

    atividades_ensino = processo.registros_atividade.encontra_por_categoria(ensino)
    

    if not atividades_ensino.exists():
        logger.warning(f'O usuário {request.user} não importou as {ensino} do SIGAA para o processo {processo}, antes de adicionar uma nova {tipo_atividade}.')
        messages.error(request, f'Antes de cadastrar as {tipo_atividade} primeiro você tem que importar as {ensino} do SIGAA.')
        return redirect('core:processo-editar', pk=processo.pk)

    if tipo_atividade != comp_ensino and not processo.registros_atividade.encontra_por_categoria(comp_ensino).exists():
        logger.warning(f'O usuário {request.user} não adicionou as {comp_ensino} obrigatórias para o processo {processo}, antes de adicionar uma nova {tipo_atividade}.')
        messages.error(request, f'Antes de cadastrar as {tipo_atividade} primeiro você tem que adicionar as {comp_ensino} obrigatórias.')
        return redirect('core:processo-editar', pk=processo.pk)

    atividades_cadastradas = processo.registros_atividade.filter(atividade__in=atividades_obg)
    if len(atividades_obg) > 0:
        if atividades_cadastradas.count() == len(atividades_obg):
            logger.info(f'O usuário {request.user} já adicionou todas as {len(atividades_obg)} atividade(s) obrigatórias da categoria "{tipo_atividade}" no processo {processo}.')
            return redirect('core:atividade-novo', pk=processo.pk, slug=tipo_atividade.slug)
    else:
        logger.info(f'A categoria "{tipo_atividade}" não possui atividades obrigatórias para serem adicionadas no processo {processo}.')
        return redirect('core:atividade-novo', pk=processo.pk, slug=tipo_atividade.slug)

    argumento_ensino = ArgumentoCategoria.objects.get(categoria_atividade=ensino, campo='Tipo de curso')
    informacoes_argumentos_ensino = InformacaoArgumento.objects.filter(argumento=argumento_ensino, registro_atividade__in=atividades_ensino)

    data = []
    for a in atividades_obg:
        a_dict = {}
        a_dict['atividade'] = a
        if a.descricao == 'Preparação didática':
            ch_ensino = processo.subtotal_ch_semanal_tipo_atividade()[ensino]
            a_dict['ch_semanal'] = ch_ensino
        else:
            if a.validacao_ch_por == Atividade.TURMA:
                for info in informacoes_argumentos_ensino:
                    if 'técnico' in info.valor_texto.lower():
                        if 'técnico' in a.descricao.lower() and 'integrado' not in a.descricao.lower() and 'subsequente' not in a.descricao.lower() and 'concomitante' not in a.descricao.lower() and 'eja' not in a.descricao.lower():
                            a_dict['ch_semanal'] = a.ch_minima * processo.qtd_turma_por_tipo_curso('TÉCNICO')
                        else:
                            if 'Integrado' in info.valor_texto:
                                if 'integrados' in a.descricao.lower() or 'integrado' in a.descricao.lower():
                                    a_dict['ch_semanal'] = a.ch_minima * processo.qtd_turma_por_tipo_curso(info.valor_texto)
                            elif 'Subsequente' in info.valor_texto:
                                if 'subsequentes' in a.descricao.lower() or 'subsequente' in a.descricao.lower():
                                    a_dict['ch_semanal'] = a.ch_minima * processo.qtd_turma_por_tipo_curso(info.valor_texto)
                            elif 'Concomitante' in info.valor_texto:
                                if ' concomitante ' in a.descricao.lower():
                                    a_dict['ch_semanal'] = a.ch_minima * processo.qtd_turma_por_tipo_curso(info.valor_texto)
                            elif 'eja' in info.valor_texto.lower():
                                if ' eja' in a.descricao.lower():
                                    a_dict['ch_semanal'] = a.ch_minima * processo.qtd_turma_por_tipo_curso(info.valor_texto)
                    elif 'graduação' in info.valor_texto.lower():
                        if 'graduação' in a.descricao.lower():
                            a_dict['ch_semanal'] = a.ch_minima * processo.qtd_turma_por_tipo_curso(info.valor_texto)
                    else:
                        a_dict['ch_semanal'] = a.ch_minima * atividades_ensino.count()
            elif a.validacao_ch_por == Atividade.DISCIPLINA:
                a_dict['ch_semanal'] = a.ch_minima * processo.qtd_disciplinas()
            elif a.validacao_ch_por == Atividade.CURSO:
                print(f"{a} a.validacao_ch_por == Atividade.CURSO")
                for info in informacoes_argumentos_ensino:
                    if 'técnico' in info.valor_texto.lower():
                        if 'Integrado' in info.valor_texto:
                            if 'integrados' in a.descricao.lower() or 'integrado' in a.descricao.lower():
                                a_dict['ch_semanal'] = a.ch_minima * processo.qtd_cursos_por_tipo(info.valor_texto)
                        elif 'Subsequente' in info.valor_texto:
                            if 'subsequentes' in a.descricao.lower() or 'subsequente' in a.descricao.lower():
                                a_dict['ch_semanal'] = a.ch_minima * processo.qtd_cursos_por_tipo(info.valor_texto)
                        elif 'Concomitante' in info.valor_texto:
                            if ' concomitante ' in a.descricao.lower():
                                a_dict['ch_semanal'] = a.ch_minima * processo.qtd_cursos_por_tipo(info.valor_texto)
                        elif 'eja' in info.valor_texto.lower():
                            if ' eja' in a.descricao.lower():
                                a_dict['ch_semanal'] = a.ch_minima * processo.qtd_cursos_por_tipo(info.valor_texto)
                    elif 'graduação' in info.valor_texto.lower():
                        if 'graduação' in a.descricao.lower():
                            a_dict['ch_semanal'] = a.ch_minima * processo.qtd_cursos_por_tipo(info.valor_texto)
            else:
                a_dict['ch_semanal'] = a.ch_minima
        a_dict['processo'] = processo
        data.append(a_dict)

    formset = RegistroAtividadeFormSet(initial=data)
    for form in formset:
        form.fields['atividade'].queryset = Atividade.objects.encontra_por_categoria(tipo_atividade)
        form.fields['atividade'].widget.attrs['readonly'] = True

    if request.method == 'POST':
        formset = RegistroAtividadeFormSet(request.POST)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    cont = 0
                    for form in formset:
                        registro = form.save(commit=False)
                        if not processo.registros_atividade.encontra_por_atividade(registro.atividade).exists():
                            if registro.atividade.descricao == 'Preparação didática':
                                registro.is_editavel = False
                            registro.is_obrigatorio = True
                            registro.save()
                            cont = cont + 1
                        else:
                            messages.warning(request, 'A atividade "{}" já foi cadastrada neste processo.'.format(registro.atividade.descricao))
                            logger.warning("A atividade  '{}' já foi importada para o processo {} do usuario: {}.".format(registro.atividade.descricao, processo, request.user))
                    messages.success(request, f'Foram adicionadas {cont} atividades obrigatórias da categoria {tipo_atividade}.')
                    logger.info(f'Foram adicionadas {cont} atividades obrigatórias da categoria {tipo_atividade} ao o processo {processo}')
                    return redirect('core:processo-editar', pk=processo.pk)
                    processo.save()
            except Exception as ex:
                messages.error(self.request, f'Operação não foi realizada, pois: {ex.message}')
                logger.exception('Ocorreu uma exceção: Não é possível adicionar as atividades de ensino: %s' % str(ex))

    return render(request, 'core/processo/atividades/obrigatorias.html', {'processo': processo, 'atividades': atividades_obg, 'categoria': tipo_atividade, 'formset': formset,})


#Atividades
class RegistroAtividadeNovoView(LoginRequiredMixin, SuccessMessageMixin, generic.CreateView):
    model = RegistroAtividade
    form_class = RegistroAtividadeForm
    template_name = 'core/processo/atividades/form.html'
    success_message = "Atividade inserida com sucesso."

    @property
    def processo(self):
        processo = get_object_or_404(Processo, pk=self.kwargs.get('pk'))
        return processo

    @property
    def info_form_class(self):
        new_fields = {}
        DynamicInformacoesRegistroForm = type('DynamicInformacoesRegistroForm', (InformacoesRegistroForm,), new_fields)
        info_form = DynamicInformacoesRegistroForm()
        return info_form

    @property
    def grupo_docente(self):
        processo = get_object_or_404(Processo, pk=self.kwargs.get('pk'))
        return processo.interessado.grupo

    @property
    def categoria_atividade(self):
        tipo_atividade = get_object_or_404(CategoriaAtividade, slug=self.kwargs['slug'])
        return tipo_atividade

    def get_initial(self, *args, **kwargs):
        initial = super(RegistroAtividadeNovoView, self).get_initial(**kwargs)
        initial['processo'] = self.processo
        return initial

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(RegistroAtividadeNovoView, self).get_form_kwargs(*args, **kwargs)
        Atividade.objects.encontra_por_categoria(tipo_atividade)
        kwargs['atividade'] = Atividade.objects.encontra_por_categoria(self.categoria_atividade)
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                ctx = self.get_context_data()
                self.object = form.save(commit=False)
                
                if 'info_form' in ctx:
                    info_form = ctx['info_form']
                else:
                    info_form = None

                if self.processo.registros_atividade.encontra_por_atividade(self.object.atividade).exists():
                    raise ValidationError('A atividade "{}" já foi cadastrada neste processo.'.format(self.object.atividade.descricao))
                    return render(self.request, self.template_name, self.get_context_data())
                
                if self.categoria_atividade.slug != 'atividades-complementares-de-ensino':
                    ch_semanal = self.object.ch_semanal
                    if self.categoria_atividade.is_restricao_ch_semanal:
                        ch_semanal_maxima = self.categoria_atividade.carga_horaria_semanal_categoria_atividade.filter(grupo_docente=self.processo.interessado.grupo).first()
                        retorno_subtotal = self.processo.subtotal_ch_semanal_tipo_atividade()
                        subtotal_semanal = Decimal(retorno_subtotal[self.categoria_atividade])
                        if Decimal(ch_semanal_maxima.ch_maxima) < (subtotal_semanal + ch_semanal):
                            raise ValidationError('Esta atividade possui uma Carga Horária que estrapolará a cota máxima de Carga Horária Semanal para %s.' % self.categoria_atividade.nome)
                

                if info_form:
                    if 'Quantidade' in self.request.POST:
                        qtd = Decimal(self.request.POST.get('Quantidade'))
                        if self.object.atividade.validacao_ch_por == Atividade.QUANTIDADE:
                            if qtd == 0:
                                raise ValidationError('O valor do campo "Quantidade" deve ser maior que zero.')
                            if ch_semanal > (self.object.atividade.ch_maxima * qtd):
                                raise ValidationError('Esta atividade possui uma Carga Horária que estrapolará a cota máxima de Carga Horária Semanal definida para a atividade "{}", que é de {} horas ({}).'.format(self.object.atividade.descricao, self.object.atividade.ch_maxima, self.object.atividade.observacao))
                    else:
                        if self.object.atividade.validacao_ch_por == Atividade.QUANTIDADE:
                            raise ValidationError('O campo "Quantidade" é obrigatório para a atividade "{}"'.format(self.object.atividade.descricao))

                self.object.save()
                
                if info_form:
                    argumento = self.categoria_atividade.argumentos.all()
                    for a in argumento:
                        informacao_argumento = InformacaoArgumento()
                        informacao_argumento.argumento = a
                        informacao_argumento.registro_atividade = self.object
                        if a.campo in self.request.POST:
                            if a.tipo_dado == ArgumentoCategoria.TEXTO:
                                informacao_argumento.valor_texto = self.request.POST.get(a.campo)
                            elif a.tipo_dado == ArgumentoCategoria.INTEIRO:
                                informacao_argumento.valor_inteiro = self.request.POST.get(a.campo)
                            elif a.tipo_dado == ArgumentoCategoria.DECIMAL:
                                informacao_argumento.valor_decimal = self.request.POST.get(a.campo)
                            elif a.tipo_dado == ArgumentoCategoria.BOOLEAN:
                                informacao_argumento.valor_boolean = iself.request.POST.get(a.campo)
                            elif a.tipo_dado == ArgumentoCategoria.DATA:
                                informacao_argumento.valor_data = self.request.POST.get(a.campo)
                            elif a.tipo_dado == ArgumentoCategoria.HORA:
                                informacao_argumento.valor_hora = self.request.POST.get(a.campo)
                            elif a.tipo_dado == ArgumentoCategoria.DATA_HORA:
                                informacao_argumento.valor_data_hora = self.request.POST.get(a.campo)
                            informacao_argumento.save()
                self.processo.save()
                messages.success(self.request, '%s adicionada com Sucesso!'%(self.categoria_atividade.nome))
        
        
        except ValidationError as e:
            messages.error(self.request, f'Não foi possível cadastrar a atividade, pois: {e.message}')
            logger.warning(f"Ocorreu uma exceção de validação quando o usuário {self.request.user} tentou salvar a atividade '{self.object.atividade}' na categoria '{self.categoria_atividade}' do processo {self.processo}: {e}")
            return render(self.request, self.template_name, self.get_context_data())
        except Exception as e:
            messages.error(self.request, f'Não foi possível cadastrar a atividade, pois: {e.message}')
            logger.exception(f'Ocorreu uma exceção: Não é possível adicionar uma {self.categoria_atividade}: {e}')
            return render(self.request, self.template_name, self.get_context_data())

        return redirect('core:processo-editar', pk=self.processo.pk)

    def get_context_data(self, **kwargs):
        context = super(RegistroAtividadeNovoView, self).get_context_data(**kwargs)
        logger.info(f'O usuário {self.request.user} solicitou para adicionar uma atividade da categoria "{self.categoria_atividade}" no processo {self.processo}.')
        context['categoria'] = self.categoria_atividade
        context['processo'] = self.processo
        argumento = self.categoria_atividade.argumentos.all()
        if argumento.exists():
            new_fields = {}
            for a in argumento:
                if a.tipo_dado == ArgumentoCategoria.TEXTO:
                    new_fields[a.campo] = forms.CharField()
                elif a.tipo_dado == ArgumentoCategoria.INTEIRO:
                    new_fields[a.campo] = forms.IntegerField()
                elif a.tipo_dado == ArgumentoCategoria.DECIMAL:
                    new_fields[a.campo] = forms.DecimalField()
                elif a.tipo_dado == ArgumentoCategoria.BOOLEAN:
                    new_fields[a.campo] = forms.BooleanField()
                elif a.tipo_dado == ArgumentoCategoria.DATA:
                    new_fields[a.campo] = forms.DateField(help_text='Ex: 15/11/2002', input_formats=["%d/%m/%Y",], widget=forms.DateInput(format='%d/%m/%Y'))
                elif a.tipo_dado == ArgumentoCategoria.HORA:
                    new_fields[a.campo] = forms.TimeField()
                elif a.tipo_dado == ArgumentoCategoria.DATA_HORA:
                    new_fields[a.campo] = forms.DateTimeField()
            DynamicInformacoesRegistroForm = type('DynamicInformacoesRegistroForm', (InformacoesRegistroForm,), new_fields)
            InfoForm = DynamicInformacoesRegistroForm()
            context['info_form'] = InfoForm
        return context


class EditarRegistroAtividadeView(LoginRequiredMixin, generic.UpdateView):
    template_name = 'core/processo/atividades/form.html'
    model = RegistroAtividade
    form_class = RegistroAtividadeForm
    
    @property
    def registro(self):
        return get_object_or_404(RegistroAtividade, pk=self.kwargs.get('pk'))

    @property
    def processo(self):
        return get_object_or_404(Processo, pk=self.registro.processo.pk)

    @property
    def grupo_docente(self):
        return self.processo.interessado.grupo

    @property
    def categoria_atividade(self):
        return get_object_or_404(CategoriaAtividade, pk=self.registro.atividade.categoria_atividade.id)

    @property
    def informacao_argumento(self):
        return InformacaoArgumento.objects.filter(registro_atividade=self.registro)

    @property
    def argumentos(self):
        return self.categoria_atividade.argumentos.all()

    def get_initial(self, *args, **kwargs):
        initial = super(EditarRegistroAtividadeView, self).get_initial(**kwargs)
        initial['processo'] = self.processo
        initial['atividade'] = self.registro.atividade
        
        return initial

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(EditarRegistroAtividadeView, self).get_form_kwargs(*args, **kwargs)
        kwargs['atividade'] = Atividade.objects.encontra_por_categoria(self.categoria_atividade)
        return kwargs
        
    def form_valid(self, form):
        try:
            with transaction.atomic():
                ctx = self.get_context_data()
                self.object = form.save(commit=False)
                
                if 'info_form' in ctx:
                    info_form = ctx['info_form']
                else:
                    info_form = None

                ch_semanal = self.object.ch_semanal
                if self.categoria_atividade.is_restricao_ch_semanal:
                    ch_semanal_maxima = self.categoria_atividade.carga_horaria_semanal_categoria_atividade.filter(grupo_docente=self.processo.interessado.grupo).first()
                    retorno_subtotal = self.processo.subtotal_ch_semanal_tipo_atividade()
                    subtotal_semanal = Decimal(retorno_subtotal[self.categoria_atividade]) - Decimal(self.registro.ch_semanal)
                    if Decimal(ch_semanal_maxima.ch_maxima) < (subtotal_semanal + ch_semanal):
                        raise ValidationError('Esta atividade possui uma Carga Horária que estrapolará a cota máxima de Carga Horária Semanal para {}.'.format(self.categoria_atividade.nome))

                if info_form:
                    if 'Quantidade' in self.request.POST:
                        qtd = Decimal(self.request.POST.get('Quantidade'))
                        if self.object.atividade.validacao_ch_por == Atividade.QUANTIDADE:
                            if qtd == 0:
                                raise ValidationError('O valor do campo "Quantidade" deve ser maior que zero.')
                            if ch_semanal > (self.object.atividade.ch_maxima * qtd):
                                raise ValidationError('Esta atividade possui uma Carga Horária que estrapolará a cota máxima de Carga Horária Semanal definida para a atividade "{}", que é de {} horas ({}).'.format(self.object.atividade.descricao, self.object.atividade.ch_maxima, self.object.atividade.observacao))
                    else:
                        if self.object.atividade.validacao_ch_por == Atividade.QUANTIDADE:
                            raise ValidationError('O campo "Quantidade" é obrigatório para a atividade "{}"'.format(self.object.atividade.descricao))

                if self.processo.situacao.slug == 'alteracoes-necessarias':
                    self.object.situacao = RegistroAtividade.EDITADA

                self.object.save()

                if info_form:
                    for a in self.argumentos:
                        if a.campo in self.request.POST:
                            for info in self.informacao_argumento:
                                if info.argumento == a:
                                    if a.tipo_dado == ArgumentoCategoria.TEXTO:
                                        info.valor_texto = self.request.POST.get(a.campo)
                                    elif a.tipo_dado == ArgumentoCategoria.INTEIRO:
                                        info.valor_inteiro = self.request.POST.get(a.campo)
                                    elif a.tipo_dado == ArgumentoCategoria.DECIMAL:
                                        info.valor_decimal = self.request.POST.get(a.campo)
                                    elif a.tipo_dado == ArgumentoCategoria.BOOLEAN:
                                        info.valor_boolean = iself.request.POST.get(a.campo)
                                    elif a.tipo_dado == ArgumentoCategoria.DATA:
                                        info.valor_data = self.request.POST.get(a.campo)
                                    elif a.tipo_dado == ArgumentoCategoria.HORA:
                                        info.valor_hora = self.request.POST.get(a.campo)
                                    elif a.tipo_dado == ArgumentoCategoria.DATA_HORA:
                                        info.valor_data_hora = self.request.POST.get(a.campo)
                                    info.save()
                self.processo.save()
                messages.success(self.request, '%s atualizada com Sucesso!'%(self.categoria_atividade.nome))

        except CHSemanalCategoriaAtividade.DoesNotExist as e:
            messages.warning(self.request, f'As cargas horárias semanais máximas da categoria "{self.categoria_atividade.nome}" para o {self.grupo_docente} não foram definidas')
            logger.exception(f'As cargas horárias semanais máximas da categoria "{self.categoria_atividade.nome}" para o {self.grupo_docente} não foram definidas: {e}')
        except ValidationError as e:
            messages.error(self.request, f'Não foi possível salvar as alterações da atividade "{self.registro}", pois: {e.message}')
            logger.warning(f"Ocorreu uma exceção de validação quando o usuário {self.request.user} tentou salvar as alterações da atividade '{self.object.atividade}' na categoria '{self.categoria_atividade}' do processo {self.processo}: {e}")
            return render(self.request, self.template_name, self.get_context_data())
        except Exception as e:
            messages.error(self.request, f'Não foi possível salvar as alterações da atividade "{self.registro}", pois: {e.message}')
            logger.exception(f'Ocorreu uma exceção: Não foi possível salvar as alterações da atividade "{self.registro}", pois:: {e}')
            return render(self.request, self.template_name, self.get_context_data())

        return redirect('core:processo-editar', pk=self.processo.pk)

    def get_context_data(self, **kwargs):
        context = super(EditarRegistroAtividadeView, self).get_context_data(**kwargs)
        logger.info(f'O usuário {self.request.user} solicitou para edição da atividade "{self.registro}" da categoria "{self.categoria_atividade}" cadastrada no processo {self.processo}.')
        context['registro'] = self.registro
        context['processo'] = self.processo
        context['categoria'] = self.categoria_atividade
        if self.argumentos.exists():
            new_fields = {}
            initial_info = {}
            for a in self.argumentos:
                if a.tipo_dado == ArgumentoCategoria.TEXTO:
                    new_fields[a.campo] = forms.CharField()
                elif a.tipo_dado == ArgumentoCategoria.INTEIRO:
                    new_fields[a.campo] = forms.IntegerField()
                elif a.tipo_dado == ArgumentoCategoria.DECIMAL:
                    new_fields[a.campo] = forms.DecimalField()
                elif a.tipo_dado == ArgumentoCategoria.BOOLEAN:
                    new_fields[a.campo] = forms.BooleanField()
                elif a.tipo_dado == ArgumentoCategoria.DATA:
                    new_fields[a.campo] = forms.DateField(help_text='Ex: 15/11/2002', input_formats=["%d/%m/%Y",], widget=forms.DateInput(format='%d/%m/%Y'))
                elif a.tipo_dado == ArgumentoCategoria.HORA:
                    new_fields[a.campo] = forms.TimeField()
                elif a.tipo_dado == ArgumentoCategoria.DATA_HORA:
                    new_fields[a.campo] = forms.DateTimeField()

                for info in self.informacao_argumento:
                    if info.argumento == a:
                        if a.tipo_dado == ArgumentoCategoria.TEXTO:
                            initial_info[a.campo] = info.valor_texto
                        elif a.tipo_dado == ArgumentoCategoria.INTEIRO:
                            initial_info[a.campo] = info.valor_inteiro
                        elif a.tipo_dado == ArgumentoCategoria.DECIMAL:
                            initial_info[a.campo] = info.valor_decimal
                        elif a.tipo_dado == ArgumentoCategoria.BOOLEAN:
                            initial_info[a.campo] = info.valor_boolean
                        elif a.tipo_dado == ArgumentoCategoria.DATA:
                            initial_info[a.campo] = info.valor_data
                        elif a.tipo_dado == ArgumentoCategoria.HORA:
                            initial_info[a.campo] = info.valor_hora
                        elif a.tipo_dado == ArgumentoCategoria.DATA_HORA:
                            initial_info[a.campo] = info.valor_data_hora

            DynamicInformacoesRegistroForm = type('DynamicInformacoesRegistroForm', (InformacoesRegistroForm,), new_fields)            
            InfoForm = DynamicInformacoesRegistroForm(initial=initial_info)
            context['info_form'] = InfoForm
        return context


class ProjetoNovoView(LoginRequiredMixin, SuccessMessageMixin, generic.CreateView):
    model = RegistroAtividade
    form_class = ProjetoForm
    template_name = 'core/processo/projetos/form.html'

    @property
    def processo(self):
        processo = get_object_or_404(Processo, pk=self.kwargs.get('pk'))
        return processo
    
    @property
    def categoria_atividade(self):
        tipo_atividade = get_object_or_404(CategoriaAtividade, slug=self.kwargs['slug'])
        return tipo_atividade
    
    @property
    def grupo_docente(self):
        return self.processo.interessado.grupo

    def get_initial(self, *args, **kwargs):
        initial = super(ProjetoNovoView, self).get_initial(**kwargs)
        initial['processo'] = self.processo
        return initial

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(ProjetoNovoView, self).get_form_kwargs(*args, **kwargs)
        kwargs['atividade'] = Atividade.objects.encontra_por_categoria(self.categoria_atividade)
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super(ProjetoNovoView, self).get_context_data(**kwargs)
        logger.info(f'O usuário {self.request.user} solicitou para adicionar um projeto da categoria "{self.categoria_atividade}" no processo {self.processo}.')
        context['categoria'] = self.categoria_atividade
        context['processo'] = self.processo
        return context
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)

                titulo = form.cleaned_data['titulo']
                
                if InformacaoArgumento.objects.encontra_por_processo(processo).encontra_por_campo('Título').filter(valor_texto=titulo).exists():
                    raise ValidationError('O projeto "{}" já foi cadastrado neste processo.'.format(titulo))
                
                if self.categoria_atividade.is_restricao_ch_semanal:
                    ch_semanal = self.object.ch_semanal
                    ch_semanal_maxima = self.categoria_atividade.categoria_pai.carga_horaria_semanal_categoria_atividade.filter(grupo_docente=self.processo.interessado.grupo).first()
                    retorno_subtotal = self.processo.subtotal_ch_semanal_tipo_atividade()
                    subtotal_semanal = Decimal(retorno_subtotal[self.categoria_atividade.categoria_pai])

                    if Decimal(ch_semanal_maxima.ch_maxima) < (subtotal_semanal + ch_semanal):
                        raise ValidationError('Esta atividade possui uma Carga Horária que estrapolará a cota máxima de Carga Horária Semanal para %s.' % self.categoria_atividade.nome)
                
                self.object.save()

                argumentos = self.categoria_atividade.argumentos.all()

                for a in argumentos:
                    informacao_argumento = InformacaoArgumento()
                    informacao_argumento.argumento = a
                    informacao_argumento.registro_atividade = self.object
                    if a.campo == 'Título':
                        informacao_argumento.valor_texto = form.cleaned_data['titulo']
                    if a.campo == 'Número de participantes':
                        informacao_argumento.valor_inteiro = form.cleaned_data['numero_participantes']
                    if a.campo == 'Data de Início':
                        informacao_argumento.valor_data = form.cleaned_data['data_inicio']
                    if a.campo == 'Data de Término':
                        informacao_argumento.valor_data = form.cleaned_data['data_termino']
                    if a.campo == 'Resultados':
                        informacao_argumento.valor_texto = form.cleaned_data['resultados']
                    informacao_argumento.save()
                self.processo.save()
                messages.success(self.request, '%s adicionada com Sucesso!' % (self.categoria_atividade.nome))
        
        except CHSemanalCategoriaAtividade.DoesNotExist as e:
            messages.warning(self.request, f'As cargas horárias semanais máximas da categoria "{self.categoria_atividade.nome}" para o {self.grupo_docente} não foram definidas.')
            logger.exception(f'As cargas horárias semanais máximas da categoria "{self.categoria_atividade.nome}" para o {self.grupo_docente} não foram definidas: {e}')
        except ValidationError as e:
            messages.error(self.request, f'Não foi possível cadastrar o projeto, pois: {e.message}')
            logger.warning(f"Ocorreu uma exceção de validação quando o usuário {self.request.user} tentou salvar a atividade '{self.object.atividade}' na categoria '{self.categoria_atividade}' do processo {self.processo}: {e}")
            return render(self.request, self.template_name, self.get_context_data())
        except Exception as e:
            messages.error(self.request, f'Não foi possível cadastrar o projeto, pois: {e.message}')
            logger.exception(f'Ocorreu uma exceção: Não é possível adicionar uma {self.categoria_atividade}: {e}')
            return render(self.request, self.template_name, self.get_context_data())

        return redirect('core:processo-editar', pk=self.processo.pk)


class EditarProjetoView(LoginRequiredMixin, generic.UpdateView):
    model = RegistroAtividade
    form_class = ProjetoForm
    template_name = 'core/processo/projetos/form.html'

    @property
    def registro(self):
        return get_object_or_404(RegistroAtividade, pk=self.kwargs.get('pk'))

    @property
    def processo(self):
        return get_object_or_404(Processo, pk=self.registro.processo.pk)

    @property
    def grupo_docente(self):
        return self.processo.interessado.grupo

    @property
    def categoria_atividade(self):
        return get_object_or_404(CategoriaAtividade, pk=self.registro.atividade.categoria_atividade.id)
    
    @property
    def informacao_argumento(self):
        return self.registro.informacoes_argumentos.all()

    @property
    def argumentos(self):
        return self.categoria_atividade.argumentos.all()

    def get_initial(self, *args, **kwargs):
        initial = super(EditarProjetoView, self).get_initial(**kwargs)
        initial['processo'] = self.processo
        initial['atividade'] = self.registro.atividade

        for a in self.argumentos:
            for info in self.informacao_argumento:
                if info.argumento == a:
                    if a.campo == 'Título':
                        initial['titulo'] = info.valor_texto
                    if a.campo == 'Número de participantes':
                        initial['numero_participantes'] = info.valor_inteiro
                    if a.campo == 'Data de Início':
                        initial['data_inicio'] = info.valor_data
                    if a.campo == 'Data de Término':
                        initial['data_termino'] = info.valor_data
                    if a.campo == 'Resultados':
                        initial['resultados'] = info.valor_texto
        return initial

    def get_context_data(self, **kwargs):
        context = super(EditarProjetoView, self).get_context_data(**kwargs)
        logger.info(f'O usuário {self.request.user} solicitou para edição do projeto "{self.registro}" da categoria "{self.categoria_atividade}" cadastrada no processo {self.processo}.')
        context['categoria'] = self.categoria_atividade
        context['registro'] = self.registro
        context['processo'] = self.processo
        return context
    
    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(EditarProjetoView, self).get_form_kwargs(*args, **kwargs)
        kwargs['atividade'] = Atividade.objects.encontra_por_categoria(self.categoria_atividade)
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)

                titulo = form.cleaned_data['titulo']
                
                if_ag = InformacaoArgumento.objects.encontra_por_processo(processo).encontra_por_campo('Título').filter(valor_texto=titulo)
                if if_ag.exists():
                    if_ag = if_ag.first()
                    if if_ag.registro_atividade.pk != self.object.pk:
                        raise ValidationError('O projeto "{}" já foi cadastrado neste processo.'.format(titulo))
                
                if self.categoria_atividade.is_restricao_ch_semanal:
                    ch_semanal = self.object.ch_semanal
                    ch_semanal_maxima = self.categoria_atividade.categoria_pai.carga_horaria_semanal_categoria_atividade.filter(grupo_docente=self.processo.interessado.grupo).first()
                    retorno_subtotal = self.processo.subtotal_ch_semanal_tipo_atividade()
                    subtotal_semanal = Decimal(retorno_subtotal[self.categoria_atividade.categoria_pai]) - Decimal(self.registro.ch_semanal)
                    
                    if Decimal(ch_semanal_maxima.ch_maxima) < (subtotal_semanal + ch_semanal):
                        raise ValidationError('Esta atividade possui uma Carga Horária que estrapolará a cota máxima de Carga Horária Semanal para {}.'.format(self.categoria_atividade.nome))
                
                if self.processo.situacao.slug == 'alteracoes-necessarias':
                    self.object.situacao = RegistroAtividade.EDITADA

                self.object.save()

                argumento = self.categoria_atividade.argumentos.all()

                for a in self.argumentos:
                    for info in self.informacao_argumento:
                        if info.argumento == a:
                            if a.campo == 'Título':
                                info.valor_texto = form.cleaned_data['titulo']
                            if a.campo == 'Número de participantes':
                                info.valor_inteiro = form.cleaned_data['numero_participantes']
                            if a.campo == 'Data de Início':
                                info.valor_data = form.cleaned_data['data_inicio']
                            if a.campo == 'Data de Término':
                                info.valor_data = form.cleaned_data['data_termino']
                            if a.campo == 'Resultados':
                                info.valor_texto = form.cleaned_data['resultados']
                            info.save()
                self.processo.save()
                messages.success(self.request, '%s alterada com Sucesso!' % (self.categoria_atividade.nome))
        
        except CHSemanalCategoriaAtividade.DoesNotExist as e:
            messages.warning(self.request, f'As cargas horárias semanais máximas da categoria "{self.categoria_atividade.nome}" para o {self.grupo_docente} não foram definidas')
            logger.exception(f'As cargas horárias semanais máximas da categoria "{self.categoria_atividade.nome}" para o {self.grupo_docente} não foram definidas: {e}')
        except ValidationError as e:
            messages.error(self.request, f'Não foi possível salvar as alterações do projeto, pois: {e.message}')
            logger.warning(f"Ocorreu uma exceção de validação quando o usuário {self.request.user} tentou salvar a atividade '{self.object.atividade}' na categoria '{self.categoria_atividade}' do processo {self.processo}: {e}")
            return render(self.request, self.template_name, self.get_context_data())
        except Exception as e:
            messages.error(self.request, f'Não foi possível salvar as alterações do projeto, pois: {e.message}')
            logger.exception(f'Ocorreu uma exceção: Não é possível adicionar uma {self.categoria_atividade}: {e}')
            return render(self.request, self.template_name, self.get_context_data())

        return redirect('core:processo-editar', pk=self.processo.pk)


@login_required
def busca_observacao(request, idatividade):
    atividade = get_object_or_404(Atividade, pk=idatividade)
    observacao = atividade.observacao if atividade.observacao else ''
    retorno = [{'observacao': observacao}]
    return HttpResponse(json.dumps(retorno), content_type='application/json')


@login_required
def resumo_processo(request, pk, editando):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    context['processo'] = processo

    if editando == 'True':
        context['editando'] = True
    else:
        context['editando'] = False

    messages.warning(request, f"Verifique e confirme os dados do seu {processo.tipo_processo} antes de enviar.")

    pode_enviar = True
    
    if not processo.interessado.area_contratacao:
        pode_enviar = False
        messages.warning(request, f"Antes de enviar seu {processo.tipo_processo} é necessário indicar sua área de contratação.")    
    
    if not processo.interessado.lattes:
        pode_enviar = False
        messages.warning(request, f"Antes de enviar seu {processo.tipo_processo} é necessário indicar o link do seu currículo lattes.")
    
    for k, v in processo.subtotal_ch_semanal_tipo_atividade().items():
        if k.is_restricao_ch_semanal:
            limitacao = k.carga_horaria_semanal_categoria_atividade.filter(grupo_docente=self.processo.interessado.grupo).first()
            if limitacao.ch_minima > 0 and v < limitacao.ch_minima:
                messages.warning(request, f"A carga horária mínima semanal das suas {k.label} para o {processo.interessado.grupo} está abaixo da regulamentada, que é de {limitacao.ch_minima} horas.")

    
    if processo.ch_semanal_total() != processo.interessado.grupo.ch_semanal:
        pode_enviar = False
        messages.warning(request, f"A carga horária semanal do seu {processo.tipo_processo} está diferente da regulamentada para o seu grupo, que é de {processo.interessado.grupo.ch_semanal} horas.")
    
    context['pode_enviar'] = pode_enviar
    data['html_form'] = render_to_string('core/ajax/partial_resumo_processo.html', context, request=request,)
    return JsonResponse(data)


@login_required
def form_assinatura(request, pk):
    data = dict()
    context = {}
    context['form'] = ConfirmPasswordForm(instance=request.user)
    context['processo'] = get_object_or_404(Processo, pk=pk)
    data['html_form'] = render_to_string('core/ajax/partial_form_assinatura.html', context, request=request,)
    return JsonResponse(data)


@login_required
@transaction.atomic
def assinar_envio_processo(request, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    context['processo'] = processo
    form = ConfirmPasswordForm(instance=request.user)
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])

    if request.method == 'POST':
        form = ConfirmPasswordForm(request.POST, instance=request.user)
    
        if form.is_valid():

            fluxo = processo.tipo_processo.fluxos.fluxo_principal().filter(unidade=processo.interessado.unidade_responsavel).first()
            
            if processo.situacao.slug != 'alteracoes-necessarias':
                ''' Caso a carga horária de ensino esteja abaixo da regulamentada '''
                for k, v in processo.subtotal_ch_semanal_tipo_atividade().items():
                    if k.slug == 'atividades-de-ensino':
                        limitacao = k.carga_horaria_semanal_categoria_atividade.filter(grupo_docente=self.processo.interessado.grupo).first()
                        if v < limitacao.ch_minima:
                            proxima_unidade = processo.interessado.unidade_lotacao
                        else:
                            proxima_unidade = fluxo.unidades_fluxo.all().first().unidade
                            # proxima_unidade = UnidadeFluxoProcesso.objects.filter(fluxo_processo=fluxo).first().unidade
            else:
                # proxima_unidade = UnidadeFluxoProcesso.objects.filter(fluxo_processo=fluxo).first().unidade
                proxima_unidade = fluxo.unidades_fluxo.all().first().unidade


            if processo.interessado.unidade_exercicio:
                unidade_origem = processo.interessado.unidade_exercicio
            else:
                unidade_origem = processo.interessado.unidade_lotacao
            
            tramite = cria_tramite(processo.interessado, unidade_origem, processo, proxima_unidade)

            assinatura = cria_assinatura(tramite, servidor, True)

            situacao = processo.tipo_processo.situacao_processso.enviado()
            processo.situacao = situacao
            processo.save()

            logger.info(f'O usuário {request.user} assinou digitalmente o envio do {processo}')
            messages.success(request, f'O {processo} foi enviado com sucesso para a {proxima_unidade} do {processo.interessado.unidade_responsavel}!')
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
        
    context['form'] = form
    data['html_form'] = render_to_string('core/ajax/partial_form_assinatura.html', context, request=request,)
    return JsonResponse(data)


def cria_tramite(servidor_origem, unidade_origem, processo, proxima_unidade):
    tramite = Tramite()
    tramite.processo = processo
    tramite.servidor_origem = servidor_origem
    tramite.unidade_origem = unidade_origem
    tramite.data_envio = dt.now()
    tramite.data_despacho = dt.now()
    tramite.unidade_destino = proxima_unidade
    tramite.save()
    
    return tramite


def cria_assinatura(content_object, servidor, is_autenticador):
    assinatura = Assinatura()
    assinatura.content_object = content_object
    assinatura.servidor_assinante = servidor
    assinatura.is_autenticador = is_autenticador
    assinatura.save()
    return assinatura


@login_required
def busca_avancada_processo(request):
    context = {}
    processos_list = Processo.objects.pesquisaveis()
    processos_filter = ProcessoFilter(request.GET, queryset=processos_list)
    paginator = Paginator(processos_filter.qs, 20)

    page = request.GET.get('page')
    processos = paginator.get_page(page)

    context['processos'] = processos
    context['filter'] = processos_filter
    return render(request, 'core/processo/busca_processos_avancada.html', context)


@login_required
def carregar_lista_movimentacao(request, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    tramites = processo.tramites.all()
    context['tramites'] = tramites
    data['html_item_list'] = render_to_string('core/ajax/partial_tramite_list_mov.html', context, request=request,)
    return JsonResponse(data)


@login_required
def carregar_lista_tramite_detalhe(request, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    tramites = processo.tramites.all()
    context['tramites'] = tramites
    data['html_item_list'] = render_to_string('core/ajax/partial_tramite_list.html', context, request=request,)
    return JsonResponse(data)


@login_required
@transaction.atomic
def receber_processo(request):
    url = 'core:caixa-entrada'
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])
    if request.method == 'POST':
        if request.POST.get('idurl'):
            url = request.POST.get('idurl')
        processo = Processo.objects.get(pk=request.POST.get('idprocesso'))
        tramite = Tramite.objects.filter(processo=processo).last()
        tramite.data_recebimento = dt.now()
        tramite.servidor_recebimento = servidor
        tramite.save()
        situacao = processo.tipo_processo.situacao_processso.recebido()
        processo.situacao = situacao
        processo.save()
        logger.info(f'O usuário {request.user} recebeu digitalmente o envio do {processo}')
        messages.success(request, f'O {processo} foi recebido com sucesso pelo usuário {request.user}!')

    return redirect(url)    


class MovimentaProcessoView(LoginRequiredMixin, generic.View):
    model = Processo
    context_object_name = 'processo'
    template_name = 'core/processo/movimentar/detalhe.html'

    registro = RegistroAtividade()
    informacao = InformacaoArgumento()

    @property
    def processo(self):
        return get_object_or_404(Processo, pk=self.kwargs.get('pk'))

    @property
    def servidor(self):
        return get_object_or_404(ServidorProfile, pk=self.request.session['perfil'])

    def dispatch(self, request, *args, **kwargs):
        logger.info(f'O usuário {request.user} solicitou acesso a página de movimentação do "{self.processo}".')
        validar_acesso_movimentacao(request.user, self.processo, self.servidor)

        if self.processo.processo_pai:
            return redirect('core:consulta-movimentar', pk=self.processo.pk)

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Alerta de Categorias de Atividade com carga horárias semanal abaixo da mínima
        for msg in self.processo.alertas():
            messages.add_message(request, messages.WARNING, msg)

        return render(request, self.template_name, self.carregar_context(request)) 

    def carregar_context(self, request):
        context = {}
        context['processo'] = self.processo
        try:
            tipo_atividade = CategoriaAtividade.objects.get(slug='atividades-de-ensino')
            self.registro = self.processo.registros_atividade.encontra_por_categoria(tipo_atividade).prefetch_related('informacoes_argumentos')
            context['registros'] = self.registro
        except CategoriaAtividade.DoesNotExist as e:
            context['registros'] = None
       
        context['slug'] = 'atividades-de-ensino'

        context['categorias_atividades'] = self.processo.tipo_processo.categoria_atividade.all()

        # vinculos = VinculoServidorUnidade.objects.filter(servidor=self.servidor, is_ativo=True)
        vinculos = self.servidor.vinculos_unidade.ativo()

        if self.processo.tramites.ultima_movimentacao():
            unidade_avaliadora = self.processo.tramites.ultima_movimentacao().unidade_destino.unidades_fluxo_processo.avaliadora().first()
            if unidade_avaliadora:
                context['in_unidade_avaliadora'] = unidade_avaliadora.is_avaliadora
            else:
                context['in_unidade_avaliadora'] = False

            unidade_origem = self.processo.tramites.ultima_movimentacao().unidade_destino

            fluxo = self.processo.tipo_processo.fluxos.fluxo_principal().filter(unidade=unidade_origem.estrutura_pai).first()

            unidades_fluxo = fluxo.unidades_fluxo_processo.all()

            if unidades_fluxo.ativo().filter(unidade=unidade_origem).exists():
                context['is_unidade_fluxo'] = True
            else:
                context['is_unidade_fluxo'] = False

        for v in vinculos:
            if UnidadeFluxoProcesso.objects.avaliadora().filter(unidade=v.unidade).exists():
                self.request.session['avaliador'] = True

        tramite_ultimo = self.processo.tramites.ultima_movimentacao()

        vinculos_chefia = self.servidor.vinculos_unidade.responde_por()
        funcoes_gratificadas = self.servidor.responsaveis_unidade.responde_por()
        
        if tramite_ultimo:
            vinculos_chefia = vinculos_chefia.filter(unidade=tramite_ultimo.unidade_destino)
            funcoes_gratificadas = funcoes_gratificadas.filter(unidade=tramite_ultimo.unidade_destino)
        
        elif self.processo.unidade_interessada and self.processo.situacao.slug == 'rascunho':
            vinculos_chefia = vinculos_chefia.filter(unidade=self.processo.unidade_interessada)
            funcoes_gratificadas = funcoes_gratificadas.filter(unidade=self.processo.unidade_interessada)

        if vinculos_chefia.exists() or funcoes_gratificadas.exists():
            context['is_chefia'] = True
        else:
            context['is_chefia'] = False
                
        return context


@login_required
@transaction.atomic
def criar_documento(request, pk):
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    tramite_ultimo = processo.tramites.ultima_movimentacao()
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])

    logger.info(f'O usuário {request.user} acessou a página de criação de um despacho para o "{processo}".')
    
    validar_acesso_movimentacao(request.user, processo, servidor)

    vinculos_chefia = servidor.vinculos_unidade.responde_por()
    funcoes_gratificadas = servidor.responsaveis_unidade.responde_por()
    if tramite_ultimo:
        vinculos_chefia = vinculos_chefia.filter(unidade=tramite_ultimo.unidade_destino)
        funcoes_gratificadas = funcoes_gratificadas.filter(unidade=tramite_ultimo.unidade_destino)
    elif processo.unidade_interessada and processo.situacao.slug == 'rascunho':
        vinculos_chefia = vinculos_chefia.filter(unidade=processo.unidade_interessada)
        funcoes_gratificadas = funcoes_gratificadas.filter(unidade=processo.unidade_interessada)

    form = DocumentoForm()

    if vinculos.exists() or funcoes_gratificadas.exists():
        if vinculos.exists() and not funcoes_gratificadas.exists():
            form.fields['tipo_documento'].initial = DocumentoProcesso.DESPACHO
        elif funcoes_gratificadas.exists() and not vinculos.exists():
            form.fields['tipo_documento'].widget = forms.HiddenInput()
            form.fields['tipo_documento'].initial = DocumentoProcesso.DESPACHO
        context['tipo_documento'] = 'Documento'
    elif processo.processo_pai and not tramite_ultimo and processo.situacao.slug == 'rascunho':
        context['tipo_documento'] = 'Solicitação'
        form.fields['tipo_documento'].widget = forms.HiddenInput()
        form.fields['tipo_documento'].initial = DocumentoProcesso.SOLICITACAO
    else:
        context['tipo_documento'] = 'Parecer'
        form.fields['tipo_documento'].widget = forms.HiddenInput()
        form.fields['tipo_documento'].initial = DocumentoProcesso.PARECER
        
        if processo.registros_atividade.invalida().exists():
            texto = '<p>Justificativas cadastradas para as atividades inválidas:</p>'
            texto = texto + "<ul>"
            for r in processo.registros_atividade.invalida(): 
                texto = texto + f'<li>A atividade "{r}" está inválida, pois {r.justificativa}.</li>'
            
            texto = texto + "</ul>"
            
            form.fields['texto'].initial = str(form.fields['texto']) + texto

    if request.method == 'POST':
        btn = request.POST
        form = DocumentoForm(request.POST)
    
        if form.is_valid():
            documento = form.save(commit=False)

            documento.processo = processo
            documento.criado_por = request.user
            documento.modificado_por = request.user

            documento.save()
            messages.success(request, f'O {documento} foi salvo com sucesso!')
            
            if '_save' in btn:
                return redirect('core:processo-movimentar', pk=processo.pk)
            elif '_continue' in btn:
                return redirect('core:documento-editar', id_processo=processo.pk, pk=documento.pk)

            
    context['processo'] = processo
    context['form'] = form
    # context['ass_form'] = ass_form
    return render(request, 'core/processo/documento/form.html', context)



@login_required
@transaction.atomic
def editar_documento(request, id_processo, pk):
    context = {}
    processo = get_object_or_404(Processo, pk=id_processo)
    documento = get_object_or_404(DocumentoProcesso, pk=pk)
    tramite_ultimo = processo.tramites.ultima_movimentacao()
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])

    logger.info(f'O usuário {request.user} acessou a página de criação de um despacho para o "{processo}".')
    
    validar_acesso_movimentacao(request.user, processo, servidor)

    if documento.assinaturas.all().exists():
        if documento.criado_por != request.user or not documento.assinaturas.filter(servidor_assinante=servidor).exists():
            raise PermissionDenied(f'O usuário {request.user} não tem permissão para editar o {documento}, pois somente quem o criou ou o assinou pode editá-lo.')

    if tramite_ultimo:
        unidade = tramite_ultimo.unidade_destino
    elif processo.situacao.slug == 'rascunho' and processo.unidade_interessada:
        unidade = processo.unidade_interessada

    vinculos = servidor.vinculos_unidade.responde_por().filter(unidade=unidade)
    funcoes_gratificadas = servidor.responsaveis_unidade.responde_por().filter(unidade=unidade)

    form = DocumentoForm(instance=documento)

    if vinculos.exists() or funcoes_gratificadas.exists():
        context['tipo_documento'] = documento.get_tipo_documento_display()
    else:
        context['tipo_documento'] = documento.get_tipo_documento_display()
        form.fields['tipo_documento'].widget = forms.HiddenInput()


    if request.method == 'POST':
        form = DocumentoForm(request.POST, instance=documento)
        btn = request.POST
    
        if form.is_valid():
            documento = form.save(commit=False)
            documento.modificado_por = request.user
            documento.save()
            
            for ass in documento.assinaturas.all():
                ass.delete()

            messages.success(request, f'O {documento} foi salvo com sucesso!')
            
            if '_save' in btn:
                return redirect('core:processo-movimentar', pk=processo.pk)
            elif '_continue' in btn:
                return redirect('core:documento-editar', id_processo=processo.pk, pk=documento.pk)

    context['processo'] = processo
    context['form'] = form
    context['documento'] = documento
    # context['ass_form'] = ass_form
    return render(request, 'core/processo/documento/form.html', context)


@login_required
def detalha_tramite(request, pk):
    data = dict()
    tramite = get_object_or_404(Tramite, pk=pk)
    context = {'tramite': tramite}
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])
    if servidor == tramite.processo.interessado:
        context['is_interessado'] = True
    data['html_form'] = render_to_string('core/ajax/partial_tramite_detalhe.html', context, request=request,)
    return JsonResponse(data)


@login_required
def detalha_tramite_movimentacao(request, pk):
    data = dict()
    tramite = get_object_or_404(Tramite, pk=pk)
    context = {'tramite': tramite}
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])
    data['html_form'] = render_to_string('core/ajax/partial_tramite_detalhe_mov.html', context, request=request,)
    return JsonResponse(data)


@login_required
def detalha_atividade_movimentacao(request, pk):
    data = dict()
    registro = get_object_or_404(RegistroAtividade, pk=pk)
    form = AvaliacaoAtividadeForm(instance=registro)
    context = {'registro': registro, 'dados_registro': registro.informacoes_argumentos.all(), 'form': form,}
    unidade_avaliadora = self.processo.tramites.ultima_movimentacao().unidade_destino.unidades_fluxo_processo.avaliadora().first()
    if unidade_avaliadora:
        context['in_unidade_avaliadora'] = unidade_avaliadora.is_avaliadora
    else:
        context['in_unidade_avaliadora'] = False
    
    data['html_form'] = render_to_string('core/ajax/partial_atividade_detalhe_mov.html', context, request=request,)
    return JsonResponse(data)


@login_required
def carregar_lista_atividades_movimentacao(request, pk, id_tipo_atividade):
    data = dict()
    data['html_item_list'] = render_to_string('core/ajax/partial_atividade_list_mov.html', cria_contexto_lista_atividades(pk, id_tipo_atividade), request=request,)
    return JsonResponse(data)


def validar_acesso_movimentacao(user, processo, servidor):
    ultimo_tramite = processo.tramites.ultima_movimentacao()

    vinculos = servidor.vinculos_unidade.ativo()
    funcoes_gratificadas = servidor.responsaveis_unidade.responde_por()

    com_processo = False
    
    for v in vinculos:
        if processo.unidade_interessada:
            if processo.unidade_interessada == v.unidade and processo.situacao.slug == 'rascunho':
                com_processo = True

        if ultimo_tramite and ultimo_tramite.unidade_destino == v.unidade:
            com_processo = True

    for fg in funcoes_gratificadas:
        if processo.unidade_interessada:
            if processo.unidade_interessada == fg.unidade and processo.situacao.slug == 'rascunho':
                com_processo = True

        if ultimo_tramite and ultimo_tramite.unidade_destino == fg.unidade:
            com_processo = True

    if  ultimo_tramite and ultimo_tramite.servidor_destino == servidor:
        com_processo = True

    if not com_processo:
        raise PermissionDenied(f'O usuário {user} não tem permissão para realizar movimentações no {processo}, pois o processo não se encontra com ele.')


@login_required
@transaction.atomic
def avaliar_atividade(request, id_processo, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=id_processo)
    registro = get_object_or_404(RegistroAtividade, pk=pk)
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])
    request.session['slug'] = registro.atividade.categoria_atividade.slug

    context['registro'] = registro
    context['dados_registro'] = registro.informacoes_argumentos.all()

    form = AvaliacaoAtividadeForm(instance=registro)
    if request.method == 'POST':
        try:
            form = AvaliacaoAtividadeForm(request.POST, instance=registro)
            if form.is_valid():                
                registro = form.save(commit=False)

                if form.cleaned_data['is_valida']:
                    registro.situacao = RegistroAtividade.VALIDA
                    registro.justificativa = ''
                else:
                    registro.situacao = RegistroAtividade.INVALIDA

                registro.data_avaliacao = dt.now()
                registro.avaliador = servidor
                registro.save()
                
                logger.info(f"O usuário {request.user} avaliou o '{registro}' como {registro.situacao}.")
                messages.success(request, f'A {registro} foi avaliada com sucesso!')
                data['form_is_valid'] = True
            else:
                data['form_is_valid'] = False
        except Exception as e:
            messages.error(request, f'Não foi possível salvar a validção da atividade, pois: {e}')
            logger.exception(f'Ocorreu uma exceção: Não foi possível salvar a validção da atividade, pois: {e}')

    context['form'] = form
    data['html_form'] = render_to_string('core/ajax/partial_atividade_detalhe_mov.html', context, request=request,)
    return JsonResponse(data)


@login_required
def carregar_lista_documentos(request, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    list_doc = []
    documentos = processo.documentos_processo.all()
    for doc in documentos:
        if doc.assinaturas.all().exists():
            list_doc.append(doc)
    context['documentos'] = list_doc
    data['html_item_list'] = render_to_string('core/ajax/partial_documento_list.html', context, request=request,)
    return JsonResponse(data)


@login_required
def carregar_lista_documentos_movimentacao(request, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    documentos = processo.documentos_processo.all()
    context['documentos'] = documentos
    data['html_item_list'] = render_to_string('core/ajax/partial_documento_list_mov.html', context, request=request,)
    return JsonResponse(data)


@login_required
def detalha_documento(request, pk):
    data = dict()
    documento = get_object_or_404(DocumentoProcesso, pk=pk)
    context = {'documento': documento}
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])
    data['html_form'] = render_to_string('core/ajax/partial_documento_detalhe.html', context, request=request,)
    return JsonResponse(data)


@login_required
@transaction.atomic
def excluir_documento(request):
    url = 'core:caixa-entrada'
    if request.method == 'POST':
        if request.POST.get('idurl'):
            url = request.POST.get('idurl')

        idprocesso = request.POST.get('idprocesso')
        iddocumento = request.POST.get('iddocumento')
        documento = DocumentoProcesso.objects.get(id=iddocumento)
        servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])
        logger.info(f"O usuário {request.user} solicitou a exclusão do documento '{documento}'.")
        
        if documento.assinaturas.all().exists():
            if documento.criado_por != request.user or not documento.assinaturas.filter(servidor_assinante=servidor).exists():
                raise PermissionDenied(f'O usuário {request.user} não tem permissão para editar o {documento}, pois somente quem o criou ou o assinou pode editá-lo.')
            
        try:
            documento.delete()
            messages.success(request, 'Documento excluído com sucesso!')
            logger.info('Documento excluído com sucesso!')
            return redirect('core:processo-movimentar', pk=processo.pk)
        except Exception as ex:
            messages.error(request, f'Não é possível excluir o documento: {ex}')
            logger.exception(f'Ocorreu uma exceção: Não é possível excluir o documento: {ex}')

    return redirect(url)


@login_required
@transaction.atomic
def assinar_documento(request, pk):
    data = dict()
    context = {}
    documento = get_object_or_404(DocumentoProcesso, pk=pk)
    form = ConfirmPasswordForm(instance=request.user)
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])

    if documento.criado_por != request.user:
        raise PermissionDenied(f'O usuário {request.user} não tem permissão para assinar digitalmente o {documento}, pois somente quem o criou ou o assiná-lo.')

    if documento.processo.situacao.slug == 'rascunho' and documento.processo.unidade_interessada:
        unidade = documento.processo.unidade_interessada
    elif tramite_ultimo:
        unidade = documento.processo.tramites.ultima_movimentacao()

    vinculos = servidor.vinculos_unidade.responde_por().filter(unidade=unidade)
    funcoes_gratificadas = servidor.responsaveis_unidade.responde_por().filter(unidade=unidade)

    if vinculos.exists() or funcoes_gratificadas.exists():
        is_autenticador = True
    else:
        is_autenticador = False

    if request.method == 'POST':
        form = ConfirmPasswordForm(request.POST, instance=request.user)
    
        if form.is_valid():

            assinatura = cria_assinatura(documento, servidor, is_autenticador)

            logger.info(f'O usuário {request.user} assinou digitalmente o documento {documento}')
            messages.success(request, f'O {documento} foi assinado digitalmente!')
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
        
    context['form'] = form
    context['documento'] = documento
    data['html_form'] = render_to_string('core/ajax/partial_form_ass_doc.html', context, request=request,)
    return JsonResponse(data)


@login_required
@transaction.atomic
def encaminhar_processo(request, pk):
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    servidor = get_object_or_404(ServidorProfile, pk=request.session['perfil'])

    logger.info(f'O usuário {request.user} acessou a página de criação de um despacho para o "{processo}".')
    
    validar_acesso_movimentacao(request.user, processo, servidor)

    if processo.tramites.ultima_movimentacao():
        unidade_origem = processo.tramites.ultima_movimentacao().unidade_destino
    elif processo.situacao.slug == 'rascunho' and processo.unidade_interessada:
        unidade_origem = processo.unidade_interessada
    
    ''' Verifica documentos sem assinatura'''
    doc_sem_ass = False
    for doc in processo.documentos_processo.all():
        if not  doc.assinaturas.all().exists():
            doc_sem_ass = True

    if doc_sem_ass:
        messages.warning(request, 'Há documentos sem assinatura!')
        return redirect('core:processo-movimentar', pk=processo.pk)
    
    ''' Verifica se tem atividade que não foi validada'''
    list_messages = []
    
    unidade_avaliadora = unidade_origem.unidades_fluxo_processo.avaliadora().first()
    
    if unidade_avaliadora:
        tem_atividade_nao_validada = False
        for at in processo.registros_atividade.all():
            if at.situacao != RegistroAtividade.VALIDA and at.situacao != RegistroAtividade.INVALIDA:
                tem_atividade_nao_validada = True
                list_messages.append(f'A "{at}" está pendente de avaliação!')

        if tem_atividade_nao_validada:
            for msg in list_messages:
                messages.warning(request, msg)
            return redirect('core:processo-movimentar', pk=processo.pk)

    context['processo'] = processo
    
    vinculos_pres = servidor.vinculos_unidade.responde_por().filter(unidade=unidade_origem)

    fluxo = processo.tipo_processo.fluxos.fluxo_principal()

    if processo.tipo_processo.nome not in ('Consulta', 'Recurso'):
        fluxo = fluxo.filter(unidade=unidade_origem.estrutura_pai).first()

    unidades_fluxo  = fluxo.unidades_fluxo_processo.all()
    
    primeira_unidade_fluxo = unidades_fluxo.first()

    lista_unidades = []
    
    vl_interessado_str = 'servidor' if isinstance(processo.get_interessado(), DocenteProfile) else 'unidade'
    
    ''' Verifica se a unidade é uma unidade do fluxo '''
    if not unidades_fluxo.ativo().filter(unidade=unidade_origem).exists():
        item = {
            'value': f'{vl_interessado_str}-{processo.get_interessado().pk}',
            'str':processo.get_interessado(),
        }
        lista_unidades.append(item)
        item = {
            'value': f'unidade-{primeira_unidade_fluxo.unidade.pk}',
            'str':primeira_unidade_fluxo.unidade,
        }
        lista_unidades.append(item)
    elif unidade_origem == primeira_unidade_fluxo.unidade:
        if vinculos_pres.exists():
            item = {
                'value': f'{vl_interessado_str}-{processo.get_interessado().pk}',
                'str':processo.get_interessado(),
            }
            lista_unidades.append(item)
            ordem_proxima = primeira_unidade_fluxo.ordem + 1
            proxima_unidade = unidades_fluxo.ativo().filter(ordem=ordem_proxima).first().unidade
            item = {
                'value': f'unidade-{proxima_unidade.pk}',
                'str':proxima_unidade,
            }
            lista_unidades.append(item)
        else:
            item = {
                'value': f'unidade-{unidade_origem.pk}',
                'str':unidade_origem,
            }
            lista_unidades.append(item)
    else:
        item = {
            'value': f'unidade-{unidade_origem.pk}',
            'str':unidade_origem,
        }
        lista_unidades.append(item)
        ordem_proxima = primeira_unidade_fluxo.ordem + 1
        proxima_unidade = unidades_fluxo.ativo().filter(ordem=ordem_proxima).first().unidade
        item = {
            'value': f'unidade-{proxima_unidade.pk}',
            'str':proxima_unidade,
        }
        lista_unidades.append(item)

    context['unidades_fluxo'] = lista_unidades

    if request.method == 'POST':
        un = request.POST.get('unidade')

        try:
            if not un.strip():
                raise ValidationError('O campo "Destino" é obrigatório!')
            if 'unidade' in un:
                id_unidade = int(un.split('-')[1])
                unidade = EstruturaOrganizacional.objects.get(pk=id_unidade)

                tramite = Tramite()
                tramite.processo = processo
                tramite.servidor_origem = servidor
                tramite.unidade_origem = unidade_origem
                tramite.data_envio = dt.now()
                tramite.unidade_destino = unidade
                # para o presidente
                if unidade == unidade_origem:
                    presidente = VinculoServidorUnidade.objects.chefe().filter(unidade=unidade_origem).first().servidor
                    tramite.servidor_destino = presidente
                tramite.save()

                situacao = processo.tipo_processo.situacao_processso.enviado()
                processo.situacao = situacao
                processo.save()

                logger.info(f'O usuário {request.user} enviou do {processo}')
                messages.success(request, f'O {processo} foi enviado com sucesso para a(o) {unidade} do(a) {unidade_origem}!')
                return redirect('core:caixa-entrada')

            elif 'servidor' in un:
                tramite = Tramite()
                tramite.processo = processo
                tramite.servidor_origem = servidor
                tramite.unidade_origem = unidade_origem
                tramite.data_envio = dt.now()
                tramite.servidor_destino = processo.interessado
                tramite.save()

                unidade_avaliadora = UnidadeFluxoProcesso.objects.avaliadora().filter(unidade=unidade_origem).first()
                if unidade_avaliadora:
                    situacao = processo.tipo_processo.situacao_processso.alteracoes_necessarias()
                    processo.situacao = situacao
                    processo.save()
                else:
                    situacao = processo.tipo_processo.situacao_processso.envio_recusado()
                    processo.situacao = situacao
                    processo.save()

                
                logger.info(f'O usuário {request.user} enviou do {processo}')
                messages.success(request, f'O {processo} foi enviado com sucesso para o servidor(a) {processo.interessado} do(a) {unidade_origem}!')
                return redirect('core:caixa-entrada')
        
        except ValidationError as e:
            messages.error(request, f'Não foi possível encaminhar o {processo}, pois: {e.message}')
            logger.warning(f"Ocorreu uma exceção de validação quando o usuário {request.user} tentou encaminhar o {processo}: {e}")
        except Exception as ex:
            messages.error(request, f'Não é possível encaminhar o {processo}: {ex}')
            logger.exception(f'Ocorreu uma exceção: Não é possível encaminhar o {processo}: {ex}')

    return render(request, 'core/processo/movimentar/encaminhar.html', context)


def carrega_texto_parecer_novo(request, pk):
    data = dict()
    processo = get_object_or_404(Processo, pk=pk)
    texto = '<p>Justificativas cadastradas para as atividades inválidas:</p>'
    texto = texto + "<ul>"
    for r in processo.registros_atividade.filter(situacao=RegistroAtividade.INVALIDA): 
        texto = texto + f'<li>A atividade "{r}" está inválida, pois {r.justificativa}.</li>'
    
    texto = texto + "</ul>"
    data['texto'] = texto
    return JsonResponse(data)


@login_required
def carregar_lista_processos_anexos(request, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    processo_anexos = list(Processo.objects.filter(processo_pai=processo))
    if processo.processo_pai:
        processo_anexos.append(processo.processo_pai)
    context['processo_anexos'] = processo_anexos
    data['html_item_list'] = render_to_string('core/ajax/partial_processos_anexos.html', context, request=request,)
    return JsonResponse(data)


@login_required
def carregar_lista_processos_anexos_movimentacao(request, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    processo_anexos = list(Processo.objects.filter(processo_pai=processo))
    if processo.processo_pai:
        processo_anexos.append(processo.processo_pai)
    context['processo_anexos'] = processo_anexos
    data['html_item_list'] = render_to_string('core/ajax/partial_processos_anexos_mov.html', context, request=request,)
    return JsonResponse(data)
