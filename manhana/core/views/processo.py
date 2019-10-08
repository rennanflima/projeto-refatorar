from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.views import generic
from datetime import datetime as dt
from django.views.generic.base import RedirectView
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from validate_email import validate_email
from pprint import pprint
from django.db import transaction
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from manhana.core.models.processo import *
from manhana.core.forms.processo import *
from manhana.core.forms.principal import ConfirmPasswordForm
from manhana.core.models.parametro import *
from manhana.authentication.models import *
from manhana.core.services import *
from django.template.loader import render_to_string
from manhana.core.filters import ProcessoFilter
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType
from django import forms
import logging
import requests, json



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
            if self.request.session['tipo_perfil']:
                if self.request.session['tipo_perfil'] == 'Docente':
                    perfil = DocenteProfile.objects.get(pk=self.request.session['perfil'])
                    
                    self.object = form.save(commit=False)
                    self.object.interessado = perfil
                    self.object.criado_por = self.request.user
                    self.object.modificado_por = self.request.user
                    self.object.save()
                    logger.info("O usuário '%s' criou o processo '%s'" % (self.request.user, str(self.object)))
                    return redirect('core:processo-editar', pk=self.object.pk)
                else:
                    messages.error(self.request, 'Só usuários com vínculo de Docente podem criar um novo registro.')
                    logger.error("O usuário '%s' do tipo %s tem tentou criar um processo mas não conseguiu, pois só usuários com vínculo de Docente podem criar um novo registro." % (self.request.user, self.request.session['tipo_perfil']))
            else:
                logger.warning('O usuário %s não está com o perfil registrado na sessão', self.request.user)
                return redirect('auth:selecao_perfil')
        
        except IntegrityError as e:
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
        return ServidorProfile.objects.get(pk=self.request.session['perfil'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.processo = get_object_or_404(Processo, pk=self.processo_id)
        context['processo'] = self.processo
        try:
            tipo_atividade = CategoriaAtividade.objects.get(slug='atividades-de-ensino')
            self.registro = RegistroAtividade.objects.filter(processo=self.processo, atividade__categoria_atividade=tipo_atividade)
            context['registros'] = self.registro
        except:
            context['registros'] = None
        self.informacao = InformacaoArgumento.objects.filter(registro_atividade__in=self.registro)
        context['informacao'] = self.informacao
       
        context['slug'] = 'atividades-de-ensino'
        context['categorias_atividades'] = self.processo.tipo_processo.categoria_atividade.all()
        # context['editando'] = False
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
        
        user = request.user
        if user == self.processo.interessado.pessoa.user or user == self.processo.criado_por:
            if self.processo.situacao.slug != 'rascunho' and self.processo.situacao.slug != 'alteracoes-necessarias' and self.processo.situacao.slug != 'envio-recusado':
                messages.error(request, 'Somente processo com situação RASCUNHO, ALTERAÇÕES NECESSÁRIAS ou ENVIO RECUSADO pode ser editado!')
                logger.warning(f"O usuário '{user}' tentou editar o processo '{self.processo}' que tem situação '{self.processo.situacao.nome}'.")
                return redirect('core:caixa-entrada')
        else:
            messages.error(request, 'Só o criador ou interessado pode Editar o processo!')
            logger.warning(f"O usuário '{user}' tentou editar o {self.processo} que foi criado por '{self.processo.criado_por}' e tem como interessado o '{self.processo.interessado}'.")
            return redirect('core:caixa-entrada')

        # Alerta de Categorias de Atividade com carga horárias semanal abaixo da mínima
        if self.processo.registros_atividade.all().exists():
            for k, v in self.processo.subtotal_ch_semanal_tipo_atividade().items():
                if k.is_restricao_ch_semanal:
                    limitacao =  CHSemanalCategoriaAtividade.objects.filter(grupo_docente=self.processo.interessado.grupo, categoria_atividade=k).first()
                    if limitacao.ch_minima > 0 and v < limitacao.ch_minima:
                        messages.warning(request, f"A carga horária mínima semanal das suas {k.label} para o {self.processo.interessado.grupo} está abaixo da regulamentada, que é de {limitacao.ch_minima} horas.")

            if self.processo.ch_semanal_total() != self.processo.interessado.grupo.ch_semanal:
                messages.warning(request, f"A carga horária semanal do seu {self.processo.tipo_processo} está diferente da regulamentada para o seu grupo, que é de {self.processo.interessado.grupo.ch_semanal} horas.")

        if self.processo.situacao.slug != 'rascunho':
            if self.processo.ultima_movimentacao().exists():
                tramite = self.processo.ultima_movimentacao()
                tramite.data_recebimento = dt.now()
                tramite.servidor_recebimento = ServidorProfile.objects.get(pessoa__user=request.user)
                tramite.save()

        return render(request, self.template_name, self.context)

    def post(self, request, *args, **kwargs):
        return render(request, self.template_name, self.context)

    def carregar_context(self, request):
        self.processo = get_object_or_404(Processo, pk=self.processo_id)
        self.context['processo'] = self.processo
        try:
            tipo_atividade = CategoriaAtividade.objects.get(slug='atividades-de-ensino')
            self.registro = RegistroAtividade.objects.filter(processo=self.processo, atividade__categoria_atividade=tipo_atividade)
            self.context['registros'] = self.registro
        except:
            self.context['registros'] = None
        self.informacao = InformacaoArgumento.objects.filter(registro_atividade__in=self.registro)
        self.context['informacao'] = self.informacao
       
        self.context['slug'] = 'atividades-de-ensino'

        self.context['categorias_atividades'] = self.processo.tipo_processo.categoria_atividade.all()
        self.context['editando'] = True
        #self.context['categorias_atividades'] = self.processo.tipo_processo.categoria_atividade.filter(categoria_pai__isnull=True)


class CaixaEntradaView(LoginRequiredMixin, generic.ListView):
    model = Processo
    context_object_name = 'processo_list'
    paginate_by = 10
    template_name = 'core/processo/caixa_entrada.html'

    def get_queryset(self):
        nome = self.request.GET.get('nome', '')
        servidor = ServidorProfile.objects.get(pk=self.request.session['perfil'])

        vinculos = VinculoServidorUnidade.objects.filter(servidor=servidor, is_ativo=True)
        
        lista_processos = []
        for v in vinculos:
            proc_l = Processo.objects.filter(unidade_interessada=v.unidade, situacao__slug='rascunho')
            for p in proc_l:
                if p not in lista_processos:
                    lista_processos.append(p.id)

            tramites = Tramite.objects.filter(unidade_destino=v.unidade)
            for t in tramites:
                if t.processo.ultima_movimentacao().unidade_destino == v.unidade:
                    if t.processo not in lista_processos:
                        lista_processos.append(t.processo.id)


        funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=servidor) & Q(data_termino__isnull=True) & (Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))

        for fg in funcoes_gratificadas:
            procfg_l = Processo.objects.filter(unidade_interessada=fg.unidade, situacao__slug='rascunho')
            for p in procfg_l:
                if p not in lista_processos:
                    lista_processos.append(p.id)

            tramites = Tramite.objects.filter(unidade_destino=fg.unidade)
            for t in tramites:
                if t.processo.ultima_movimentacao().unidade_destino == fg.unidade:
                    if t.processo not in lista_processos:
                        lista_processos.append(t.processo.id)

        tramites = Tramite.objects.filter(servidor_destino=servidor)
        for t in tramites:
            if t.processo.ultima_movimentacao().servidor_destino == servidor:
                if t.processo not in lista_processos:
                    lista_processos.append(t.processo.id)

        all_processos = self.model.objects.filter(id__in=lista_processos)

        if '/' in nome:
            s = nome.split('/')
            if s[0].isdigit() and s[1].isdigit():
                ano = int(s[0])
                semestre = int(s[1])
                processo_pessoal = self.model.objects.filter(Q(interessado__pessoa=self.request.user.pessoa) & (Q(tipo_processo__nome__icontains = nome) | Q(assunto__icontains=nome) | (Q(ano=ano) & Q(semestre=semestre))) & (Q(situacao__slug='rascunho') | Q(situacao__slug='alteracoes-necessarias')))
                return processo_pessoal | all_processos.filter(Q(tipo_processo__nome__icontains = nome) | Q(assunto__icontains=nome) | (Q(ano=ano) & Q(semestre=semestre)))
            else:
                if s[0].isdigit():
                    ano = int(s[0])
                    processo_pessoal = self.model.objects.filter(Q(interessado__pessoa=self.request.user.pessoa) & (Q(tipo_processo__nome__icontains = nome) | Q(assunto__icontains=nome) | Q(ano=ano) | Q(semestre=ano)) & (Q(situacao__slug='rascunho') | Q(situacao__slug='alteracoes-necessarias')))
                    return processo_pessoal | all_processos.filter(Q(tipo_processo__nome__icontains = nome) | Q(assunto__icontains=nome) | Q(ano=ano) | Q(semestre=ano))
                if s[1].isdigit():
                    semestre = int(s[1])
                    processo_pessoal = self.model.objects.filter(Q(interessado__pessoa=self.request.user.pessoa) & (Q(tipo_processo__nome__icontains = nome) | Q(assunto__icontains=nome) | Q(ano=semestre) | Q(semestre=semestre)) & (Q(situacao__slug='rascunho') | Q(situacao__slug='alteracoes-necessarias')))
                    return processo_pessoal | all_processos.filter(Q(tipo_processo__nome__icontains = nome) | Q(assunto__icontains=nome) | Q(ano=semestre) | Q(semestre=semestre)) 

        if nome.isdigit():
            processo_pessoal = self.model.objects.filter(Q(interessado__pessoa=self.request.user.pessoa) & (Q(ano=int(nome)) | Q(semestre=int(nome))) & (Q(situacao__slug='rascunho') | Q(situacao__slug='alteracoes-necessarias')))
            return processo_pessoal | all_processos.filter(Q(ano=int(nome)) | Q(semestre=int(nome)))
        
        
        processo_pessoal = self.model.objects.filter(Q(interessado__pessoa=self.request.user.pessoa) & (Q(tipo_processo__nome__icontains = nome) | Q(assunto__icontains=nome)) & (Q(situacao__slug='rascunho') | Q(situacao__slug='alteracoes-necessarias')))
        
        return processo_pessoal | all_processos.filter(Q(tipo_processo__nome__icontains = nome) | Q(assunto__icontains=nome))

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
            if user == processo.interessado.pessoa.user or user == processo.criado_por:
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
        resultado = importSig.importar_disciplina(processo.interessado, processo.ano)
        print(resultado)
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
    if ResponsavelUnidade.objects.filter(servidor__pessoa__user=request.user, nivel_responsabilidade='C', data_termino__isnull=True).exists():
        try:
            responsavel = ResponsavelUnidade.objects.get(servidor__pessoa__user=request.user, nivel_responsabilidade='C', data_termino__isnull=True)
            logger.info(f"Para o usuario '{request.user}' foi encontrada a seguinte unidade na qual ele é responsável: {responsavel.unidade.nome}" )
            messages.success(request, 'Unidade responsável por vossa gestão localizada com sucesso.')
            tipo_atividade = get_object_or_404(CategoriaAtividade, slug='atividades-de-gestao')
            form = RegistroAtividadeForm(initial={'processo': processo,'descricao': responsavel.get_nivel_responsabilidade_display() + ': ' + responsavel.unidade.sigla + ' - ' + responsavel.unidade.nome})
            form.fields['atividade'].queryset = Atividade.objects.filter(categoria_atividade=tipo_atividade, is_ativo=True)
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
                if not RegistroAtividade.objects.filter(atividade=registro.atividade, processo=processo).exists():
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
        resultado = importSig.importar_disciplina(processo.interessado, processo.ano)
        add = 0
        alt = 0
        if resultado:
            if resultado['objects']:
                disciplinas = limpar_disciplinas_importadas(resultado, processo.semestre)
                for r in disciplinas:
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
                    argumento = ArgumentoCategoria.objects.filter(categoria_atividade=atividade.categoria_atividade)

                    atividade_existe = InformacaoArgumento.objects.filter(argumento__campo='Disciplina', valor_texto=disciplina, registro_atividade__processo=processo).exists()
                    if not atividade_existe:
                        ch_semanal = CalculaCargahorariaSemanal()
                        qtd_aulas = ch_semanal.calcular_qtdaulas(horario, ch_diciplina, ch_docente)
                        registro_atividade = RegistroAtividade(atividade=atividade, processo=processo, ch_semanal=arredondamento.qtd_horas_aula(qtd_aulas), is_obrigatorio=True, is_editavel=False)
                        registro_atividade.save()
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
                        
                        registro = InformacaoArgumento.objects.filter(argumento__campo='Disciplina', valor_texto=disciplina, registro_atividade__processo=processo).first().registro_atividade
                        
                        if processo.situacao.slug == 'alteracoes-necessarias':
                            reg_ativ = registro.registro_atividade
                            reg_ativ.situacao = RegistroAtividade.EDITADA
                            reg_ativ.save()
                            
                        ch_semanal = CalculaCargahorariaSemanal()
                        qtd_aulas = ch_semanal.calcular_qtdaulas(horario)
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
                informacao = InformacaoArgumento.objects.filter(registro_atividade=registro)
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
    registros_list = RegistroAtividade.objects.filter(Q(processo=processo) & (Q(atividade__categoria_atividade=tipo_atividade) | Q(atividade__categoria_atividade__categoria_pai=tipo_atividade)))
    informacao = InformacaoArgumento.objects.filter(registro_atividade__in=registros_list)
    context['registros'] = registros_list
    context['informacao'] = informacao
    if processo.situacao.slug != 'rascunho' and processo.ultima_movimentacao().exists():
        unidade_avaliadora = UnidadeFluxoProcesso.objects.filter(unidade=processo.ultima_movimentacao().unidade_destino, is_ativo=True, is_avaliadora=True).first()
        if unidade_avaliadora:
            context['in_unidade_avaliadora'] = unidade_avaliadora.is_avaliadora
        else:
            context['in_unidade_avaliadora'] = False
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
    processo = get_object_or_404(Processo, pk=pk)
    tipo_atividade = get_object_or_404(CategoriaAtividade, slug=slug)
    verificar_atividade = VerificarAtividadesObrigatorias()
    atividades_obg = verificar_atividade.verificar_atividades_obrigatorias(processo, tipo_atividade)
    atividades = Atividade.objects.filter(categoria_atividade=tipo_atividade, is_ativo=True)
    ensino = CategoriaAtividade.objects.get(slug='atividades-de-ensino')
    comp_ensino = CategoriaAtividade.objects.get(slug='atividades-complementares-de-ensino')
    logger.info(f'O usuário {request.user} solicitou para adicionar uma atividade da categoria "{tipo_atividade}" no processo {processo}, mas o sistema está verificando se existe atividades obrigatórias a serem inseridas.')

    atividades_ensino = RegistroAtividade.objects.filter(atividade__categoria_atividade=ensino, processo=processo)
    

    if not atividades_ensino.exists():
        logger.warning(f'O usuário {request.user} não importou as {ensino} do SIGAA para o processo {processo}, antes de adicionar uma nova {tipo_atividade}.')
        messages.error(request, f'Antes de cadastrar as {tipo_atividade} primeiro você tem que importar as {ensino} do SIGAA.')
        return redirect('core:processo-editar', pk=processo.pk)

    if tipo_atividade != comp_ensino and not RegistroAtividade.objects.filter(atividade__categoria_atividade=comp_ensino, processo=processo).exists():
        logger.warning(f'O usuário {request.user} não adicionou as {comp_ensino} obrigatórias para o processo {processo}, antes de adicionar uma nova {tipo_atividade}.')
        messages.error(request, f'Antes de cadastrar as {tipo_atividade} primeiro você tem que adicionar as {comp_ensino} obrigatórias.')
        return redirect('core:processo-editar', pk=processo.pk)

    atividades_cadastradas = RegistroAtividade.objects.filter(atividade__in=atividades_obg, processo=processo)
    if len(atividades_obg) > 0:
        if atividades_cadastradas.count() == len(atividades_obg):
            logger.info(f'O usuário {request.user} já adicionou todas as {len(atividades_obg)} atividade(s) obrigatórias da categoria "{tipo_atividade}" no processo {processo}.')
            return redirect('core:atividade-novo', pk=processo.pk, slug=tipo_atividade.slug)
    else:
        logger.info(f'A categoria "{tipo_atividade}" não possui atividades obrigatórias para serem adicionadas no processo {processo}.')
        return redirect('core:atividade-novo', pk=processo.pk, slug=tipo_atividade.slug)

    argumento_ensino = ArgumentoCategoria.objects.get(categoria_atividade=ensino, campo='Tipo de curso')
    registro_atividade_ensino = RegistroAtividade.objects.filter(atividade__categoria_atividade=ensino, processo=processo)
    informacoes_argumentos_ensino = InformacaoArgumento.objects.filter(argumento=argumento_ensino, registro_atividade__in=registro_atividade_ensino)

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
        form.fields['atividade'].queryset = Atividade.objects.filter(categoria_atividade=tipo_atividade, is_ativo=True)
        form.fields['atividade'].widget.attrs['readonly'] = True

    if request.method == 'POST':
        formset = RegistroAtividadeFormSet(request.POST)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    cont = 0
                    for form in formset:
                        registro = form.save(commit=False)
                        if not RegistroAtividade.objects.filter(atividade=registro.atividade, processo=processo).exists():
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
        kwargs['atividade'] = Atividade.objects.filter(categoria_atividade=self.categoria_atividade, is_ativo=True)
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

                if RegistroAtividade.objects.filter(atividade=self.object.atividade, processo=self.processo).exists():
                    raise ValidationError('A atividade "{}" já foi cadastrada neste processo.'.format(self.object.atividade.descricao))
                    return render(self.request, self.template_name, self.get_context_data())
                
                if self.categoria_atividade.slug != 'atividades-complementares-de-ensino':
                    ch_semanal = self.object.ch_semanal
                    if self.categoria_atividade.is_restricao_ch_semanal:
                        ch_semanal_maxima = CHSemanalCategoriaAtividade.objects.get(categoria_atividade=self.categoria_atividade, grupo_docente=self.grupo_docente)
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
                    argumento = ArgumentoCategoria.objects.filter(categoria_atividade=self.categoria_atividade)
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
        argumento = ArgumentoCategoria.objects.filter(categoria_atividade=self.categoria_atividade)
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
        return ArgumentoCategoria.objects.filter(categoria_atividade=self.categoria_atividade)

    def get_initial(self, *args, **kwargs):
        initial = super(EditarRegistroAtividadeView, self).get_initial(**kwargs)
        initial['processo'] = self.processo
        initial['atividade'] = self.registro.atividade
        
        return initial

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(EditarRegistroAtividadeView, self).get_form_kwargs(*args, **kwargs)
        kwargs['atividade'] = Atividade.objects.filter(categoria_atividade=self.categoria_atividade, is_ativo=True)
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
                    ch_semanal_maxima = CHSemanalCategoriaAtividade.objects.get(categoria_atividade=self.categoria_atividade, grupo_docente=self.grupo_docente)
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
        kwargs['atividade'] = Atividade.objects.filter(categoria_atividade=self.categoria_atividade, is_ativo=True)
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
                
                if InformacaoArgumento.objects.filter(argumento__campo='Título', registro_atividade__processo=self.processo, valor_texto=titulo).exists():
                    raise ValidationError('O projeto "{}" já foi cadastrado neste processo.'.format(titulo))
                
                if self.categoria_atividade.is_restricao_ch_semanal:
                    ch_semanal = self.object.ch_semanal
                    ch_semanal_maxima = CHSemanalCategoriaAtividade.objects.get(categoria_atividade=self.categoria_atividade.categoria_pai, grupo_docente=self.grupo_docente)
                    retorno_subtotal = self.processo.subtotal_ch_semanal_tipo_atividade()
                    subtotal_semanal = Decimal(retorno_subtotal[self.categoria_atividade.categoria_pai])

                    if Decimal(ch_semanal_maxima.ch_maxima) < (subtotal_semanal + ch_semanal):
                        raise ValidationError('Esta atividade possui uma Carga Horária que estrapolará a cota máxima de Carga Horária Semanal para %s.' % self.categoria_atividade.nome)
                
                self.object.save()

                argumento = ArgumentoCategoria.objects.filter(categoria_atividade=self.categoria_atividade)

                for a in argumento:
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
        return InformacaoArgumento.objects.filter(registro_atividade=self.registro)

    @property
    def argumentos(self):
        return ArgumentoCategoria.objects.filter(categoria_atividade=self.categoria_atividade)

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
        kwargs['atividade'] = Atividade.objects.filter(categoria_atividade=self.categoria_atividade, is_ativo=True)
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)

                titulo = form.cleaned_data['titulo']
                
                if_ag = InformacaoArgumento.objects.filter(argumento__campo='Título', registro_atividade__processo=self.processo, valor_texto=titulo)
                if if_ag.exists():
                    if_ag = if_ag.first()
                    if if_ag.registro_atividade.pk != self.object.pk:
                        raise ValidationError('O projeto "{}" já foi cadastrado neste processo.'.format(titulo))
                
                if self.categoria_atividade.is_restricao_ch_semanal:
                    ch_semanal = self.object.ch_semanal
                    ch_semanal_maxima = CHSemanalCategoriaAtividade.objects.get(categoria_atividade=self.categoria_atividade.categoria_pai, grupo_docente=self.grupo_docente)
                    retorno_subtotal = self.processo.subtotal_ch_semanal_tipo_atividade()
                    subtotal_semanal = Decimal(retorno_subtotal[self.categoria_atividade.categoria_pai]) - Decimal(self.registro.ch_semanal)
                    
                    if Decimal(ch_semanal_maxima.ch_maxima) < (subtotal_semanal + ch_semanal):
                        raise ValidationError('Esta atividade possui uma Carga Horária que estrapolará a cota máxima de Carga Horária Semanal para {}.'.format(self.categoria_atividade.nome))
                
                if self.processo.situacao.slug == 'alteracoes-necessarias':
                    self.object.situacao = RegistroAtividade.EDITADA

                self.object.save()

                argumento = ArgumentoCategoria.objects.filter(categoria_atividade=self.categoria_atividade)

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
            limitacao =  CHSemanalCategoriaAtividade.objects.filter(grupo_docente=processo.interessado.grupo, categoria_atividade=k).first()
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
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])

    if request.method == 'POST':
        form = ConfirmPasswordForm(request.POST, instance=request.user)
    
        if form.is_valid():

            fluxo = FluxoProcesso.objects.filter(tipo_fluxo=FluxoProcesso.PRINCIPAL, tipo_processo=processo.tipo_processo, is_ativo=True, unidade=processo.interessado.unidade_responsavel).first()
            
            if processo.situacao.slug != 'alteracoes-necessarias':
                ''' Caso a carga horária de ensino esteja abaixo da regulamentada '''
                for k, v in processo.subtotal_ch_semanal_tipo_atividade().items():
                    if k.slug == 'atividades-de-ensino':
                        limitacao =  CHSemanalCategoriaAtividade.objects.filter(grupo_docente=processo.interessado.grupo, categoria_atividade=k).first()
                        if v < limitacao.ch_minima:
                            proxima_unidade = processo.interessado.unidade_lotacao
                        else:
                            proxima_unidade = UnidadeFluxoProcesso.objects.filter(fluxo_processo=fluxo).first().unidade
            else:
                proxima_unidade = UnidadeFluxoProcesso.objects.filter(fluxo_processo=fluxo).first().unidade


            if processo.interessado.unidade_exercicio:
                unidade_origem = processo.interessado.unidade_exercicio
            else:
                unidade_origem = processo.interessado.unidade_lotacao
            
            tramite = cria_tramite(processo.interessado, unidade_origem, processo, proxima_unidade)

            assinatura = cria_assinatura(tramite, servidor, True)

            situacao = SituacaoProcesso.objects.get(slug='enviado', categorias_processo=processo.tipo_processo)
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
    processos_list = Processo.objects.all().exclude(situacao__slug='rascunho')
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
    tramites = processo.processo_tramitado.all()
    context['tramites'] = tramites
    data['html_item_list'] = render_to_string('core/ajax/partial_tramite_list_mov.html', context, request=request,)
    return JsonResponse(data)


@login_required
def carregar_lista_tramite_detalhe(request, pk):
    data = dict()
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    tramites = processo.processo_tramitado.all()
    context['tramites'] = tramites
    data['html_item_list'] = render_to_string('core/ajax/partial_tramite_list.html', context, request=request,)
    return JsonResponse(data)


@login_required
@transaction.atomic
def receber_processo(request):
    url = 'core:caixa-entrada'
    if request.method == 'POST':
        if request.POST.get('idurl'):
            url = request.POST.get('idurl')
        processo = Processo.objects.get(pk=request.POST.get('idprocesso'))
        tramite = Tramite.objects.filter(processo=processo).last()
        tramite.data_recebimento = dt.now()
        tramite.servidor_recebimento = ServidorProfile.objects.get(pessoa__user=request.user)
        tramite.save()
        situacao = SituacaoProcesso.objects.get(slug='recebido', categorias_processo=processo.tipo_processo)
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
        return ServidorProfile.objects.get(pk=self.request.session['perfil'])

    def dispatch(self, request, *args, **kwargs):
        logger.info(f'O usuário {request.user} solicitou acesso a página de movimentação do "{self.processo}".')
        validar_acesso_movimentacao(request.user, self.processo, self.servidor)

        if self.processo.processo_pai:
            return redirect('core:consulta-movimentar', pk=self.processo.pk)

        return super().dispatch(request, *args, **kwargs)
        

    def get(self, request, *args, **kwargs):
        # Alerta de Categorias de Atividade com carga horárias semanal abaixo da mínima
        for k, v in self.processo.subtotal_ch_semanal_tipo_atividade().items():
            if k.is_restricao_ch_semanal:
                limitacao =  CHSemanalCategoriaAtividade.objects.filter(grupo_docente=self.processo.interessado.grupo, categoria_atividade=k).first()
                if limitacao.ch_minima > 0 and v < limitacao.ch_minima:
                    messages.warning(request, f"A carga horária mínima semanal das {k.label} para o {self.processo.interessado.grupo} está abaixo da regulamentada, que é de {limitacao.ch_minima} horas.")

        return render(request, self.template_name, self.carregar_context(request)) 

    def carregar_context(self, request):
        context = {}
        context['processo'] = self.processo
        try:
            tipo_atividade = CategoriaAtividade.objects.get(slug='atividades-de-ensino')
            self.registro = RegistroAtividade.objects.filter(processo=self.processo, atividade__categoria_atividade=tipo_atividade)
            context['registros'] = self.registro
        except:
            context['registros'] = None
        self.informacao = InformacaoArgumento.objects.filter(registro_atividade__in=self.registro)
        context['informacao'] = self.informacao
       
        context['slug'] = 'atividades-de-ensino'

        context['categorias_atividades'] = self.processo.tipo_processo.categoria_atividade.all()

        vinculos = VinculoServidorUnidade.objects.filter(servidor=self.servidor, is_ativo=True)
        
        if self.processo.ultima_movimentacao():
            unidade_avaliadora = UnidadeFluxoProcesso.objects.filter(unidade=self.processo.ultima_movimentacao().unidade_destino, is_ativo=True, is_avaliadora=True).first()
            if unidade_avaliadora:
                context['in_unidade_avaliadora'] = unidade_avaliadora.is_avaliadora
            else:
                context['in_unidade_avaliadora'] = False

            unidade_origem = self.processo.ultima_movimentacao().unidade_destino
            
            fluxo = FluxoProcesso.objects.filter(tipo_fluxo=FluxoProcesso.PRINCIPAL, tipo_processo=self.processo.tipo_processo, is_ativo=True, unidade=unidade_origem.estrutura_pai).first()
            unidades_fluxo  = fluxo.unidades_fluxo_processo.all()

            if unidades_fluxo.filter(unidade=unidade_origem, is_ativo=True).exists():
                context['is_unidade_fluxo'] = True
            else:
                context['is_unidade_fluxo'] = False

        for v in vinculos:
            if UnidadeFluxoProcesso.objects.filter(unidade=v.unidade, is_avaliadora=True, is_ativo=True).exists():
                self.request.session['avaliador'] = True

        tramite_ultimo = self.processo.ultima_movimentacao()
        if tramite_ultimo:
            vinculos_chefia = VinculoServidorUnidade.objects.filter(Q(servidor=self.servidor) & Q(is_ativo=True) & Q(unidade=tramite_ultimo.unidade_destino) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
            funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=self.servidor) & Q(data_termino__isnull=True) & Q(unidade=tramite_ultimo.unidade_destino) &(Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))
        if self.processo.unidade_interessada and self.processo.situacao.slug == 'rascunho':
            vinculos_chefia = VinculoServidorUnidade.objects.filter(Q(servidor=self.servidor) & Q(is_ativo=True) & Q(unidade=processo.unidade_interessada) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
            funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=self.servidor) & Q(data_termino__isnull=True) & Q(unidade=processo.unidade_interessada) &(Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))

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
    tramite_ultimo = processo.ultima_movimentacao()
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])

    logger.info(f'O usuário {request.user} acessou a página de criação de um despacho para o "{processo}".')
    
    validar_acesso_movimentacao(request.user, processo, servidor)
    if tramite_ultimo:
        vinculos = VinculoServidorUnidade.objects.filter(Q(servidor=servidor) & Q(is_ativo=True) & Q(unidade=tramite_ultimo.unidade_destino) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
        funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=servidor) & Q(data_termino__isnull=True) & Q(unidade=tramite_ultimo.unidade_destino) &(Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))
    if processo.unidade_interessada and processo.situacao.slug == 'rascunho':
        vinculos = VinculoServidorUnidade.objects.filter(Q(servidor=servidor) & Q(is_ativo=True) & Q(unidade=processo.unidade_interessada) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
        funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=servidor) & Q(data_termino__isnull=True) & Q(unidade=processo.unidade_interessada) &(Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))

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
        
        if processo.registros_atividade.filter(situacao=RegistroAtividade.INVALIDA).exists():
            texto = '<p>Justificativas cadastradas para as atividades inválidas:</p>'
            texto = texto + "<ul>"
            for r in processo.registros_atividade.filter(situacao=RegistroAtividade.INVALIDA): 
                texto = texto + f'<li>A atividade "{r}" está inválida, pois {r.justificativa}.</li>'
            
            texto = texto + "</ul>"
            
            form.fields['texto'].initial = str(form.fields['texto']) + texto


    if request.method == 'POST':
        form = DocumentoForm(request.POST)
    
        if form.is_valid():
            documento = form.save(commit=False)

            documento.processo = processo
            documento.criado_por = request.user
            documento.modificado_por = request.user

            documento.save()
            messages.success(request, f'O {documento} foi salvo com sucesso!')
            return redirect('core:processo-movimentar', pk=processo.pk)
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
    tramite_ultimo = processo.ultima_movimentacao()
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])

    logger.info(f'O usuário {request.user} acessou a página de criação de um despacho para o "{processo}".')
    
    validar_acesso_movimentacao(request.user, processo, servidor)

    if documento.assinaturas.all().exists():
        if documento.criado_por != request.user or not documento.assinaturas.filter(servidor_assinante=servidor).exists():
            raise PermissionDenied(f'O usuário {request.user} não tem permissão para editar o {documento}, pois somente quem o criou ou o assinou pode editá-lo.')

    vinculos = VinculoServidorUnidade.objects.filter(Q(servidor=servidor) & Q(is_ativo=True) & Q(unidade=tramite_ultimo.unidade_destino) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
    funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=servidor) & Q(data_termino__isnull=True) & Q(unidade=tramite_ultimo.unidade_destino) &(Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))

    form = DocumentoForm(instance=documento)

    if vinculos.exists() or funcoes_gratificadas.exists():
        context['tipo_documento'] = documento.get_tipo_documento_display()
    else:
        context['tipo_documento'] = documento.get_tipo_documento_display()
        form.fields['tipo_documento'].widget = forms.HiddenInput()


    if request.method == 'POST':
        form = DocumentoForm(request.POST, instance=documento)
    
        if form.is_valid():
            documento = form.save(commit=False)
            documento.modificado_por = request.user
            documento.save()
            
            for ass in documento.assinaturas.all():
                ass.delete()

            messages.success(request, f'O {documento} foi salvo com sucesso!')
            return redirect('core:processo-movimentar', pk=processo.pk)
    context['processo'] = processo
    context['form'] = form
    # context['ass_form'] = ass_form
    return render(request, 'core/processo/documento/form.html', context)


@login_required
def detalha_tramite(request, pk):
    data = dict()
    tramite = get_object_or_404(Tramite, pk=pk)
    context = {'tramite': tramite}
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])
    if servidor == tramite.processo.interessado:
        context['is_interessado'] = True
    data['html_form'] = render_to_string('core/ajax/partial_tramite_detalhe.html', context, request=request,)
    return JsonResponse(data)


@login_required
def detalha_tramite_movimentacao(request, pk):
    data = dict()
    tramite = get_object_or_404(Tramite, pk=pk)
    context = {'tramite': tramite}
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])
    data['html_form'] = render_to_string('core/ajax/partial_tramite_detalhe_mov.html', context, request=request,)
    return JsonResponse(data)


@login_required
def detalha_atividade_movimentacao(request, pk):
    data = dict()
    registro = get_object_or_404(RegistroAtividade, pk=pk)
    form = AvaliacaoAtividadeForm(instance=registro)
    context = {'registro': registro, 'dados_registro': registro.informacoes_argumentos.all(), 'form': form,}
    unidade_avaliadora = UnidadeFluxoProcesso.objects.filter(unidade=registro.processo.ultima_movimentacao().unidade_destino, is_ativo=True, is_avaliadora=True).first()
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
    ultimo_tramite = processo.ultima_movimentacao()

    vinculos = VinculoServidorUnidade.objects.filter(servidor=servidor, is_ativo=True)
    funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=servidor) & Q(data_termino__isnull=True) & (Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))

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
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])
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
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])
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
        servidor = ServidorProfile.objects.get(pk=request.session['perfil'])
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
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])

    if documento.criado_por != request.user:
        raise PermissionDenied(f'O usuário {request.user} não tem permissão para assinar digitalmente o {documento}, pois somente quem o criou ou o assiná-lo.')

    vinculos = VinculoServidorUnidade.objects.filter(Q(servidor=servidor) & Q(is_ativo=True) & Q(unidade=documento.processo.ultima_movimentacao().unidade_destino) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
    funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=servidor) & Q(data_termino__isnull=True) & (Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))


    if vinculos.exists() or funcoes_gratificadas.exists():
        is_autenticador = True
    else:
        is_autenticador = False

    if request.method == 'POST':
        form = ConfirmPasswordForm(request.POST, instance=request.user)
    
        if form.is_valid():

            assinatura = cria_assinatura(documento, servidor, is_autenticador)

            logger.info(f'O usuário {request.user} assinou digitalmente o documento {documento}')
            messages.success(request, f'O {documento} foi assinado digitalmento!')
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
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])

    logger.info(f'O usuário {request.user} acessou a página de criação de um despacho para o "{processo}".')
    
    validar_acesso_movimentacao(request.user, processo, servidor)

    unidade_origem = processo.ultima_movimentacao().unidade_destino
    
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
    
    unidade_avaliadora = UnidadeFluxoProcesso.objects.filter(unidade=unidade_origem, is_ativo=True, is_avaliadora=True).first()
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
    

    vinculos_pres = VinculoServidorUnidade.objects.filter(Q(servidor=servidor) & Q(is_ativo=True) & Q(unidade=unidade_origem) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
    
    fluxo = FluxoProcesso.objects.filter(tipo_fluxo=FluxoProcesso.PRINCIPAL, tipo_processo=processo.tipo_processo, is_ativo=True, unidade=unidade_origem.estrutura_pai).first()
    unidades_fluxo  = fluxo.unidades_fluxo_processo.all()
    

    primeira_unidade_fluxo = unidades_fluxo.first()

    lista_unidades = []

    ''' Verifica se a unidade é uma unidade do fluxo '''
    if not unidades_fluxo.filter(unidade=unidade_origem, is_ativo=True).exists():
        item = {
            'value': f'servidor-{processo.interessado.pk}',
            'str':processo.interessado,
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
                'value': f'servidor-{processo.interessado.pk}',
                'str':processo.interessado,
            }
            lista_unidades.append(item)
            ordem_proxima = primeira_unidade_fluxo.ordem + 1
            proxima_unidade = unidades_fluxo.filter(ordem=ordem_proxima, is_ativo=True).first().unidade
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
        proxima_unidade = unidades_fluxo.filter(ordem=ordem_proxima, is_ativo=True).first().unidade
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
                    presidente = VinculoServidorUnidade.objects.filter(is_ativo=True, tipo_vinculo=VinculoServidorUnidade.PRESIDENTE, unidade=unidade_origem).first().servidor
                    tramite.servidor_destino = presidente
                tramite.save()

                situacao = SituacaoProcesso.objects.get(slug='enviado', categorias_processo=processo.tipo_processo)
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

                unidade_avaliadora = UnidadeFluxoProcesso.objects.filter(unidade=unidade_origem, is_ativo=True, is_avaliadora=True).first()
                if unidade_avaliadora:
                    situacao = SituacaoProcesso.objects.get(slug='alteracoes-necessarias', categorias_processo=processo.tipo_processo)
                    processo.situacao = situacao
                    processo.save()
                else:
                    situacao = SituacaoProcesso.objects.get(slug='envio-recusado', categorias_processo=processo.tipo_processo)
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


# Consulta Comissão Central
@login_required
@transaction.atomic
def realizar_consulta_novo(request, pk):
    template_name = 'core/processo/consulta/novo.html'
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    categoria_processo = CategoriaProcesso.objects.filter(nome='Consulta', categoria_pai=processo.tipo_processo).first()
    unidade_interessada = processo.ultima_movimentacao().unidade_destino
    
    try:
        novo_processo = Processo.objects.get(~Q(situacao__slug='arquivado'), ano=processo.ano, semestre=processo.semestre, processo_pai=processo, tipo_processo=categoria_processo, unidade_interessada=unidade_interessada)
    except:
        novo_processo = Processo(ano=processo.ano, semestre=processo.semestre, processo_pai=processo, tipo_processo=categoria_processo, unidade_interessada=unidade_interessada, criado_por=request.user)

    novo_processo.assunto = f"{categoria_processo.nome} do {processo}"
    novo_processo.modificado_por = request.user
    novo_processo.save()

    form = DocumentoForm()

    context['tipo_documento'] = 'Solicitação'
    form.fields['tipo_documento'].widget = forms.HiddenInput()
    form.fields['tipo_documento'].initial = DocumentoProcesso.SOLICITACAO

    if request.method == 'POST':
        form = DocumentoForm(request.POST)
    
        if form.is_valid():
            documento = form.save(commit=False)

            documento.processo = novo_processo
            documento.criado_por = request.user
            documento.modificado_por = request.user

            documento.save()
            messages.success(request, f'O {documento} foi salvo com sucesso!')
            return redirect('core:processo-movimentar', pk=processo.pk)
    
    context['form'] = form
    context['processo'] = processo
    context['novo_processo'] = novo_processo

    return render(request, template_name, context)

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


@login_required
def consulta_detalhe(request, pk):
    template_name = 'core/processo/consulta/detalhe.html'
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])

    context['processo'] = processo

    tramite_ultimo = processo.ultima_movimentacao()
    if tramite_ultimo:
        vinculos_chefia = VinculoServidorUnidade.objects.filter(Q(servidor=servidor) & Q(is_ativo=True) & Q(unidade=tramite_ultimo.unidade_destino) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
        funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=servidor) & Q(data_termino__isnull=True) & Q(unidade=tramite_ultimo.unidade_destino) &(Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))
    if processo.unidade_interessada and processo.situacao.slug == 'rascunho':
        vinculos_chefia = VinculoServidorUnidade.objects.filter(Q(servidor=servidor) & Q(is_ativo=True) & Q(unidade=processo.unidade_interessada) & (Q(tipo_vinculo=VinculoServidorUnidade.PRESIDENTE) | Q(tipo_vinculo=VinculoServidorUnidade.VICE_PRESIDENTE)))
        funcoes_gratificadas = ResponsavelUnidade.objects.filter(Q(servidor=servidor) & Q(data_termino__isnull=True) & Q(unidade=processo.unidade_interessada) &(Q(nivel_responsabilidade=ResponsavelUnidade.CHEFE) | Q(nivel_responsabilidade=ResponsavelUnidade.VICE_CHEFIA)))

    if vinculos_chefia.exists() or funcoes_gratificadas.exists():
        context['is_chefia'] = True
    else:
        context['is_chefia'] = False

    return render(request, template_name, context)