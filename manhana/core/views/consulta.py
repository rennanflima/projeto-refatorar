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
def consulta_detalhe(request, pk):
    template_name = 'core/processo/consulta/detalhe.html'
    context = {}
    processo = get_object_or_404(Processo, pk=pk)
    servidor = ServidorProfile.objects.get(pk=request.session['perfil'])

    context['processo'] = processo

    tramite_ultimo = processo.ultima_movimentacao()

    vinculos_chefia = self.servidor.vinculos_unidade.responde_por()
    funcoes_gratificadas = self.servidor.responsaveis_unidade.responde_por()

    if tramite_ultimo:
        vinculos_chefia = vinculos_chefia.filter(unidade=tramite_ultimo.unidade_destino)
        funcoes_gratificadas = funcoes_gratificadas.filter(unidade=tramite_ultimo.unidade_destino)
    if processo.unidade_interessada and processo.situacao.slug == 'rascunho':
        vinculos_chefia = vinculos_chefia.filter(unidade=processo.unidade_interessada)
        funcoes_gratificadas = funcoes_gratificadas.filter(unidade=processo.unidade_interessada)

    if vinculos_chefia.exists() or funcoes_gratificadas.exists():
        context['is_chefia'] = True
    else:
        context['is_chefia'] = False

    return render(request, template_name, context)
