import json
import logging
from datetime import date, datetime
from pprint import pprint

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import (LoginRequiredMixin,
                                        PermissionRequiredMixin)
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify
from django.views import generic
from django.views.generic.base import RedirectView
from validate_email import validate_email

from manhana.authentication.models import *
from manhana.authentication.models import (DocenteProfile, ServidorProfile,
                                            TaeProfile)
from manhana.core.forms.principal import *
from manhana.core.models.parametro import (EstruturaOrganizacional,
                                            ResponsavelUnidade,
                                            VinculoServidorUnidade)
from manhana.core.services import (ImportarUnidadesSIG,
                                    IntegraResponsavelUnidadesSIG)

# Create a custom logger
logger = logging.getLogger(__name__)


class HomeView(generic.TemplateView):
    template_name = 'index.html'


class IndexView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'core/principal/index.html'

    def get(self, request, *args, **kwargs):
        if 'perfil' not in request.session:
            return redirect('auth:verifica_user')

        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['usuario'] = self.request.user
        context['titulo'] = 'Lista de PIT/RIT'
        context['texto'] = 'Seja bem-vindo ao sistema de regulamentação de atividades docentes.'
        return context


class UserDetalheView(LoginRequiredMixin, generic.TemplateView):
    model = User
    template_name = 'core/usuario/detalhe.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(UserDetalheView, self).get_context_data(**kwargs)
        user = self.request.user
        context['usuario'] = user
        perfis_servidor = ServidorProfile.objects.filter(pessoa=user.pessoa)
        context['servidores'] = perfis_servidor
        return context


class DocenteEditarView(LoginRequiredMixin, SuccessMessageMixin, generic.UpdateView):
    model = DocenteProfile
    form_class = DocenteForm
    template_name = 'core/usuario/perfil_docente_form.html'
    success_message = 'Perfil atualizado com sucesso.'
    success_url = reverse_lazy('core:user-detalhe')

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(DocenteEditarView, self).get_form_kwargs(*args, **kwargs)

        # filtra por grupos na hierarquia
        if self.object.grupo.grupo_pai:
            kwargs['grupo'] = GrupoDocente.objects.filtra_hierarquia(self.object.grupo.grupo_pai)
        else:
            kwargs['grupo'] = GrupoDocente.objects.filtra_hierarquia(self.object.grupo)
        return kwargs


@login_required
def detalha_servidor(request, pk):
    data = dict()
    perfil = get_object_or_404(ServidorProfile, pk=pk)
    context = {'perfil': perfil, }
    data['html_form'] = render_to_string('core/ajax/partial_servidor_detalhe.html', context, request=request,)
    return JsonResponse(data)


@login_required
def visualisar_organograma_sig(request):
    logger.info(f"O usuário '{request.user}' solicitou a importação do organograma do SIG.")
    importa_unidades = ImportarUnidadesSIG()
    resultado = importa_unidades.buscar_unidades_ativas()
    unidades = resultado['objects']
    root_node = 0
    hierarchy = []
    for u in unidades:
        if u['id'] == int(u['unidade_responsavel']):
            root_node = u['id']
            temp_obj = {}
            temp_obj['id'] = u['id']
            temp_obj['nome'] = u['nome']
            temp_obj['sigla'] = u['sigla']
            temp_obj['unidade_responsavel'] = u['unidade_responsavel']
            hierarchy.append(temp_obj)
            break

    hierarchy[0]['filhas'] = get_child_nodes(root_node)
    return render(request, 'core/unidades/importar.html', {'unidades': hierarchy,})


def get_child_nodes(node_id):
    importa_unidades = ImportarUnidadesSIG()
    resultado = importa_unidades.buscar_unidades_filhas(node_id)
    nodes = []
    for u in resultado['objects']:
        if u['id'] != int(node_id):
            temp_obj = {}
            temp_obj['id'] = u['id']
            temp_obj['nome'] = u['nome']
            temp_obj['sigla'] = u['sigla']
            temp_obj['unidade_responsavel'] = u['unidade_responsavel']
            temp_obj['filhas'] = get_child_nodes(temp_obj['id'])
            nodes.append(temp_obj)
    return nodes


@login_required
@transaction.atomic
def importar_unidades(request):
    if request.method == 'POST':
        logger.info(f"O usuário '{request.user}' confirmou a importação do organograma do SIG.")
        importa_unidades = ImportarUnidadesSIG()
        resultado = importa_unidades.buscar_unidades_ativas()
        unidades = resultado['objects']
        add = 0
        alt = 0
        try:
            for u in unidades:

                estrutura = EstruturaOrganizacional.objects.filter(id_unidade_sig=u['id'], is_ativo=True).first()

                if estrutura:
                    estrutura.nome = u['nome']
                    estrutura.sigla = u['sigla']

                    if u['id'] != int(u['unidade_responsavel']):
                        responsavel = EstruturaOrganizacional.objects.filter(id_unidade_sig=int(u['unidade_responsavel']), is_ativo=True).first()
                        if responsavel:
                            estrutura.estrutura_pai = responsavel

                    estrutura.id_unidade_sig = u['id']
                    estrutura.save()
                    alt = alt + 1
                else:
                    est = EstruturaOrganizacional.objects.filter(nome__istartswith=u['nome'], is_ativo=True).first()
                    novo = False

                    if not est:
                        est = EstruturaOrganizacional()
                        add = add + 1
                        novo = True
                    else:
                        alt = alt + 1

                    est.nome = u['nome']
                    est.sigla = u['sigla']

                    if u['id'] != int(u['unidade_responsavel']):
                        responsavel = EstruturaOrganizacional.objects.filter(id_unidade_sig=int(u['unidade_responsavel']), is_ativo=True).first()
                        if responsavel:
                            est.estrutura_pai = responsavel
                        if not novo:   
                            est.tipo_estrutura = EstruturaOrganizacional.SETOR
                    else:
                        if not novo:   
                            est.tipo_estrutura = EstruturaOrganizacional.RAIZ

                    est.id_unidade_sig = u['id']
                    est.save()
        except Exception as ex:
            messages.error(request, 'Não é possível atualizar o organograma: %s' % str(ex))
            logger.exception('Ocorreu uma exceção - Não é possível atualizar o organograma: %s' % str(ex))

        logger.info(f"A importação do organograma do SIG foi realizada com sucesso, foram adicionadas {add} estruturas e atualizadas {alt}.")
        messages.success(request, f"Organograma atualizado com sucesso, foram adicionadas {add} estruturas e atualizadas {alt}.")
    return redirect('core:vw_index')


@login_required
@transaction.atomic
def importar_responsabilidades(request, slug, pk):
    context = {}
    servidor = get_object_or_404(ServidorProfile, pk=pk)
    responsavel_unidades = ResponsavelUnidade.objects.filter(servidor=servidor)
    context['servidor'] = servidor
    responsavel_sig = IntegraResponsavelUnidadesSIG()
    retorno = responsavel_sig.buscar_responsabilidade_servidor(servidor.id_servidor_sig)
    responsabilidades = retorno['objects']
    context['responsabilidades'] = retorno['objects']

    if request.method == 'POST':
        add = 0
        alt = 0
        try:
            for r in responsabilidades:
                estrutura = EstruturaOrganizacional.objects.filter(id_unidade_sig=r['unidade']['id'], is_ativo=True).first()
                if not responsavel_unidades.exists():
                    funcao = ResponsavelUnidade()
                    funcao.servidor = servidor
                    funcao.unidade = estrutura
                    funcao.nivel_responsabilidade = r['nivel_responsabilidade']
                    funcao.data_inicio = r['data_inicio']
                    funcao.id_responsabilidade_sig = int(r['id'])
                    if r['data_fim']:
                        funcao.data_termino = r['data_fim']
                    funcao.save()
                    add = add + 1
                elif responsavel_unidades.count() < retorno['meta']['total_count']:
                    try:
                        ru = ResponsavelUnidade.objects.get(servidor=servidor, id_responsabilidade_sig=int(r['id']))
                        if not ru.data_termino:
                            if r['data_fim']:
                                ru.data_termino = r['data_fim']
                            ru.save()
                            alt = alt + 1
                    except:
                        funcao = ResponsavelUnidade()
                        funcao.servidor = servidor
                        funcao.unidade = estrutura
                        funcao.nivel_responsabilidade = r['nivel_responsabilidade']
                        funcao.data_inicio = r['data_inicio']
                        funcao.id_responsabilidade_sig = int(r['id'])
                        if r['data_fim']:
                            funcao.data_termino = r['data_fim']
                        funcao.save()
                        add = add + 1
                else:
                    for ru in responsavel_unidades:
                        if ru.id_responsabilidade_sig == int(r['id']):
                            if not ru.data_termino:
                                if r['data_fim']:
                                    ru.data_termino = r['data_fim']
                            ru.id_responsabilidade_sig = int(r['id'])
                            ru.save()
                            alt = alt + 1

            logger.info(f"Suas responsabilidades foram importadas com sucesso. Foram adicionadas {add} estruturas e atualizadas {alt}.")
            messages.success(request, f"Suas responsabilidades foram importadas com sucesso. Foram adicionadas {add} estruturas e atualizadas {alt}.")
            return redirect('core:lista-responsabilidades', pk=servidor.pk, slug=slugify(servidor.categoria))
        except Exception as ex:
            messages.error(request, f'Não é possível importar suas responsabilidades do SIG: {ex}') 
            logger.exception(f'Ocorreu uma exceção - Não é possível importar suas responsabilidades do SIG: {ex}')

    return render(request, 'core/usuario/importar_responsabilidades.html', context=context)


class ListaResponsabilidadesServidorView(LoginRequiredMixin, generic.ListView):
    model = ResponsavelUnidade
    context_object_name = 'responsabilidades_list'
    paginate_by = 10
    template_name = 'core/usuario/lista_responsabilidades.html'

    @property
    def servidor(self):
        return get_object_or_404(ServidorProfile, pk=self.kwargs.get('pk'))

    def get_queryset(self):
        return ResponsavelUnidade.objects.filter(servidor=self.servidor)

    def get_context_data(self, **kwargs):
        context = super(ListaResponsabilidadesServidorView, self).get_context_data(**kwargs)
        context['servidor'] = self.servidor

        return context


@login_required
def detalha_responsabilidade(request, pk):
    data = dict()
    funcao = get_object_or_404(ResponsavelUnidade, pk=pk)
    context = {'funcao': funcao, }
    data['html_form'] = render_to_string('core/ajax/partial_responsabilidade_detalhe.html', context, request=request,)
    return JsonResponse(data)


class ListaEstruturaOrganizacionalView(LoginRequiredMixin, generic.ListView):
    model = EstruturaOrganizacional
    context_object_name = 'unidades_list'
    paginate_by = 25
    template_name = 'core/vinculos/unidades_lista.html'

    def get_queryset(self):
        nome = self.request.GET.get('nome', None)

        if nome:
            return self.model.objects.encontra_por_nome(nome)
        else:
            return self.model.objects.all()

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)


@login_required
def lista_servidores_vinculados(request, pk):
    context = {}
    unidade = get_object_or_404(EstruturaOrganizacional, pk=pk)
    vinculos = VinculoServidorUnidade.objects.filter(unidade=unidade)
    context['unidade'] = unidade
    context['vinculos'] = vinculos
    return render(request, 'core/vinculos/vincular_servidores.html', context=context)


class AdicionaVinculoServidorView(LoginRequiredMixin, SuccessMessageMixin, generic.CreateView):
    model = VinculoServidorUnidade
    form_class = VinculoServidorUnidadeForm
    template_name = 'core/vinculos/vinculo_servidor_form.html'
    success_message = "Vínculo adicionado com sucesso."

    @property
    def unidade(self):
        unidade = get_object_or_404(EstruturaOrganizacional, pk=self.kwargs.get('pk'))
        return unidade

    def get_initial(self, *args, **kwargs):
        initial = super(AdicionaVinculoServidorView, self).get_initial(**kwargs)
        initial['unidade'] = self.unidade
        return initial

    def get_context_data(self, **kwargs):
        context = super(AdicionaVinculoServidorView, self).get_context_data(**kwargs)
        context['unidade'] = self.unidade
        return context

    def get_success_url(self):
        return reverse('core:lista-servidores-vinculados', kwargs={'pk' :self.unidade.pk})


class EditarVinculoServidorView(LoginRequiredMixin, SuccessMessageMixin, generic.UpdateView):
    model = VinculoServidorUnidade
    form_class = VinculoServidorUnidadeForm
    template_name = 'core/vinculos/vinculo_servidor_form.html'
    success_message = "Vínculo alterado com sucesso."

    @property
    def vinculo(self):
        vinculo = get_object_or_404(VinculoServidorUnidade, pk=self.kwargs.get('pk'))
        return vinculo

    def get_context_data(self, **kwargs):
        context = super(EditarVinculoServidorView, self).get_context_data(**kwargs)
        context['unidade'] = self.vinculo.unidade
        return context

    def get_success_url(self):
        return reverse('core:lista-servidores-vinculados', kwargs={'pk' :self.vinculo.unidade.pk})


@login_required
def detalha_vinculo(request, pk):
    data = dict()
    vinculo = get_object_or_404(VinculoServidorUnidade, pk=pk)
    context = {'vinculo': vinculo}
    data['html_form'] = render_to_string('core/ajax/partial_vinculo_detalhe.html', context, request=request,)
    return JsonResponse(data)


@login_required
def inativar_vínculo(request):
    if request.method == 'POST':
        id = request.POST.get('idvinculo')
        data_termino = request.POST.get('data_termino')
        vinculo = get_object_or_404(VinculoServidorUnidade, pk=int(id))
        user = request.user 
        logger.info(f'O usuário {user} solicitou o invativar o vínculo do servidor {vinculo.servidor} com {vinculo.unidade}.')
        try:
            vinculo.data_termino = datetime.strptime(data_termino, '%d/%m/%Y').date()
            vinculo.is_ativo = False
            vinculo.save()
            logger.info(f"O usuário {user} invativar o vínculo: '{vinculo}'")
            messages.success(request, 'Vínculo inativado com sucesso!')    
        except Exception as ex:
            messages.error(request, f'Não é possível inativar o vínculo: {ex}')
            logger.exception(f'Ocorreu uma exceção: Não é possível inativar o vínculo: {ex}')

    return redirect('core:lista-servidores-vinculados', pk=vinculo.unidade.pk)
