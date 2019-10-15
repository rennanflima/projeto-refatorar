import json
import logging
from datetime import datetime
from pprint import pprint

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import (LoginRequiredMixin,
                                        PermissionRequiredMixin)
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.base import RedirectView
from validate_email import validate_email

from manhana.authentication.forms import *
from manhana.authentication.models import *
from manhana.authentication.services import *
from manhana.core.models.parametro import (UnidadeFluxoProcesso,
                                            VinculoServidorUnidade)

# Create a custom logger
logger = logging.getLogger(__name__)


# Create your views here.
class VerificaUsuarioView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        cadu = Cadu()

        if not user.first_name or not user.last_name or not user.email:
            user_cadu = cadu.buscar_por_username(user.username)
            if 'error' not in user_cadu:
                user.first_name = user_cadu['first_name']
                user.last_name = user_cadu['last_name']
                user.email = user_cadu['email']
                user.save()

        if not user.pessoa.id_pessoa_sig:
            return reverse('auth:info_adicional_user')
        else:
            perfis_servidor = ServidorProfile.objects.encontra_pela_pessoa(user.pessoa)
            perfis_discente = DiscenteProfile.objects.encontra_pela_pessoa(user.pessoa)

            if perfis_servidor.count() == 1:
                if perfis_discente.count() == 0:
                    try:
                        servidor = perfis_servidor.first()
                        self.request.session['qtd_perfil'] = 1
                        self.request.session['tipo_perfil'] = servidor.categoria
                        self.request.session['perfil'] = servidor.pk
                        self.request.session['unidade_responsavel'] = servidor.unidade_responsavel.nome
                        return reverse('core:vw_index')
                    except Exception as ex:
                        messages.error(self.request, f'Não é possível carregar as suas informações funcionais: {ex}')
                        logger.exception(f'Ocorreu uma exceção: Não é possível carregar as suas informações funcionais: {ex}')
                        return redirect('auth:selecao_vinculo')
                else:
                    return reverse('core:selecao_perfil')
            else:
                return reverse('core:selecao_perfil')

            if perfis_discente.count() == 1 :
                if perfis_servidor.count() == 0:
                    self.request.session['qtd_perfil'] = 1
                    self.request.session['tipo_perfil'] = 'Discente'
                    for aluno in perfis_discente:
                        self.request.session['perfil'] = aluno.pk
                    return reverse('core:vw_index')
                else:
                    return reverse('core:selecao_perfil')


class InfoAdicionaisUserView(LoginRequiredMixin, generic.FormView):
    template_name = 'authentication/usuario/info_adicionais.html'
    form_class = BuscaPessoaForm

    success_url = reverse_lazy('core:vw_index')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                sig = SigPessoas()
                info_sigs = InformacoesSIG()
                user = self.request.user
                dt = form.cleaned_data['dataNasc']
                dt = dt.strftime('%Y-%m-%d')
                cadu = Cadu()

                if not user.first_name or not user.last_name or not user.email:
                    user_cadu = cadu.buscar_por_username(user.username)
                    if 'error' not in user_cadu:
                        user.first_name = user_cadu['first_name']
                        user.last_name = user_cadu['last_name']
                        user.email = user_cadu['email']
                        user.save()

                dados = {
                    'format': 'json',
                    'cpf_cnpj': form.cleaned_data['cpf'],
                    'data_nascimento': dt,
                    'situacao__istartswith': 'Ativo',
                }
                pessoas = sig.buscar_pessoa(dados)
                if pessoas['meta']['total_count'] == 1:
                    for p in pessoas['objects']:

                        user.pessoa.id_pessoa_sig = p['id']
                        user.save()

                        info_sigs.carregar_informacoes_pessoais(user)

                        perfis_docente = DocenteProfile.objects.encontra_pela_pessoa(user.pessoa)
                        perfis_discente = DiscenteProfile.objects.encontra_pela_pessoa(user.pessoa)
                        perfis_tae = TaeProfile.objects.encontra_pela_pessoa(user.pessoa)

                        if perfis_tae or perfis_docente or perfis_discente:
                            request.session['perfis_tae'] = perfis_tae if perfis_tae else None
                            request.session['perfis_docente'] = perfis_docente if perfis_docente else None
                            request.session['perfis_discente'] = perfis_discente if perfis_discente else None
                            return redirect('auth:verifica_user')

                        return redirect('auth:selecao_vinculo')
                elif pessoas['meta']['total_count'] == 0:
                    messages.error(self.request, 'Não encontramos nenhuma pessoa com esses dados. Por favor, verifique os dados informados tente novamente!')
                    return render(self.request, self.template_name, self.get_context_data())

        except IntegrityError as e:
            if 'UNIQUE constraint' in str(e):
                messages.error(self.request, 'O CPF e a data de nascimento informados já estão cadastrados como outro usuário!')
                user2 = User.objects.get(pessoa__cpf=form.cleaned_data['cpf'], pessoa__data_nascimento=dt)          
                logger.exception(f'Ocorreu uma exceção: O usuário "{user}" tentou buscar os dados dx "{user2.get_full_name()}" que já está cadastrada com o usuário "{user2}".')
                return render(self.request, self.template_name, self.get_context_data())


    def get_context_data(self, **kwargs):
        context = super(InfoAdicionaisUserView, self).get_context_data(**kwargs)
        context['progress'] = 10
        context['titulo'] = 'Informações Adicionais'
        context['texto'] = 'Seja bem-vindo ao sistema do PIT/RIT, para prosseguir necessitamos de algumas informações adicionais.'
        return context 


class SelecionarVinculoView(LoginRequiredMixin, generic.View):
    template_name = 'authentication/usuario/selecao_vinculo.html'
    context = {}

    def post(self, request, *args, **kwargs):
        self.carregar_context()
        user = self.request.user

        if not user.email and not request.POST.get('email'):
            messages.error(request, 'O e-mail institucional é obrigatório!')
            return render(request, self.template_name, self.context)

        if not request.POST.get('perfil_servidor'):
            messages.error(request, 'Selecione no mínimo um vínculo.')
            return render(request, self.template_name, self.context)

        with transaction.atomic():
            if not user.email and request.POST.get('email'):
                email = request.POST.get('email')
                is_valid = validate_email(email)
                camita = GoogleEmailInstitucional()
                if is_valid:
                    retorno = camita.verificar_email(email)
                    if 'error' not in retorno:
                        user.email = email
                        user.save()
                    else:
                        messages.error(request, retorno['message'])
                        return render(request, self.template_name, self.context)

            info_sigs = InformacoesSIG()
            perfis_servidor = request.POST.getlist('perfil_servidor')

            for p in perfis_servidor:
                try:
                    info_sigs.carregar_informacoes_funcionais(user, servidor_id=int(p))
                    self.request.session['perfil'] = p
                except Exception as ex:
                    messages.error(self.request, f'Não é possível carregar as suas informações funcionais: {ex}')
                    logger.exception(f'Ocorreu uma exceção: Não é possível carregar as suas informações funcionais: {ex}')
                    return render(request, self.template_name, self.context)

            return redirect('auth:verifica_user')

        return render(request, self.template_name, self.context)

    def get(self, request, *args, **kwargs):
        self.carregar_context()

        return render(request, self.template_name, self.context)

    def carregar_context(self, **kwargs):
        self.context['progress'] = 66
        user = self.request.user
        sig = SigServidores()
        dados_servidor = {
            'format': 'json',
            'cpf_cnpj': user.pessoa.cpf,
            'situacao__istartswith': 'Ativo',
        }
        servidores = sig.buscar_servidor(dados_servidor)
        if servidores['meta']['total_count'] >= 1:
            self.context['servidores'] = servidores['objects']


class SelecionarPerfilView(LoginRequiredMixin, generic.View):
    template_name = 'authentication/usuario/selecione_perfil.html'
    context = {}

    def get(self, request, *args, **kwargs):
        self.carregar_context()
        return render(request, self.template_name, self.context)

    def carregar_context(self, **kwargs):
        user = self.request.user

        self.context['perfis_docente'] = DocenteProfile.objects.encontra_pela_pessoa(user.pessoa)
        self.context['perfis_discente'] = DiscenteProfile.objects.encontra_pela_pessoa(user.pessoa)
        self.context['perfis_tae'] = TaeProfile.objects.encontra_pela_pessoa(user.pessoa)


# class VerificaUsuarioView(LoginRequiredMixin, RedirectView):
#     permanent = False

#     def get_redirect_url(self, *args, **kwargs):
#         perfis_docente = DocenteProfile.objects.filter(pessoa=self.requet.user.pessoa, is_ativo=True)
#         perfis_discente = DiscenteProfile.objects.filter(pessoa=self.requet.user.pessoa, is_ativo=True)
#         perfis_tae = TaeProfile.objects.filter(pessoa=self.requet.user.pessoa, is_ativo=True)

#         if perfis_tae or perfis_docente or perfis_discente:
#             request.session['perfis_tae'] = perfis_tae if perfis_tae else None
#             request.session['perfis_docente'] = perfis_docente if perfis_docente else None
#             request.session['perfis_discente'] = perfis_discente if perfis_discente else None

# Novo Usuario
class UsuarioNovoView(generic.CreateView):
    template_name = 'authentication/usuario/novo/cadastrar_usuario.html'
    form_class = SignUpForm
    success_url = reverse_lazy('core:vw_index')

    @property
    def pessoa_id(self):
        return int(self.kwargs['id_pessoa_sig'])

    def form_valid(self, form):
        with transaction.atomic():
            cadu = Cadu()
            login = form.cleaned_data.get('username')
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            email = form.cleaned_data.get('email')
            senha = form.cleaned_data.get('password1')
            dados = {
                'username': login,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'password': senha,
                'is_staff': False,
                'is_active': True,
            }

            self.object = form.save()
            self.object.pessoa.id_pessoa_sig = self.pessoa_id
            self.object.save()

            info_sigs = InformacoesSIG()
            info_sigs.carregar_informacoes_pessoais(self.object)
            perfis_servidor = self.request.session['perfis_servidor']
            for p in perfis_servidor:
                info_sigs.carregar_informacoes_funcionais(self.object, servidor_id=int(p))

            retorno = cadu.salvar(dados)
            if 'error' in retorno:
                messages.error(request, 'Ocorreu o seguinte erro ao criar sua conta no CADU: "%s"' % retorno['error'])
            else:
                return redirect('auth:confirmacao_novo_user')
            return render(self.request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(UsuarioNovoView, self).get_context_data(**kwargs)
        context['progress'] = 10
        context['titulo'] = 'Criar usuário'
        return context

    def get_initial(self, *args, **kwargs):
        initial = super(UsuarioNovoView, self).get_initial(**kwargs)
        sig_pessoa = SigPessoas()
        dados_pessoa = {'format': 'json', }
        pessoa = sig_pessoa.buscar_por_id(self.pessoa_id, dados_pessoa)
        if pessoa['email']:
            initial['email'] = pessoa['email']
            login = pessoa['email'].split('@')
            login = login[0]
            initial['username'] = login

        nome_separado = pessoa['nome'].title().split()
        first_name = nome_separado[0]
        last_name = pessoa['nome'].replace(first_name.upper(), '').strip().title()
        last_name = last_name.replace('De', 'de').replace('Da', 'da').replace('Do', 'do').replace('Das', 'das').replace('Dos', 'dos').replace('E', 'e')
        initial['first_name'] = first_name
        initial['last_name'] = last_name
        return initial


class BuscaPessoaView(generic.FormView):
    template_name = 'authentication/usuario/novo/busca_pessoa.html'
    form_class = BuscaPessoaForm

    success_url = reverse_lazy('core:vw_index')

    def form_valid(self, form):
        sig = SigPessoas()
        dt = form.cleaned_data['dataNasc']
        dt = dt.strftime('%Y-%m-%d')
        dados = {
            'format': 'json',
            'cpf_cnpj': form.cleaned_data['cpf'],
            'data_nascimento': dt,
            'situacao__istartswith': 'Ativo',
        }
        pessoas = sig.buscar_pessoa(dados)
        if pessoas['meta']['total_count'] == 1:
            for s in pessoas['objects']:
                return redirect('auth:detalha_pessoa', id=s['id'])
        elif pessoas['meta']['total_count'] == 0:
            messages.error(self.request, 'Não encontramos nenhuma pessoa com esses dados. Por favor, verifique os dados informados tente novamente!')
            return render(self.request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(BuscaPessoaView, self).get_context_data(**kwargs)
        context['progress'] = 10
        context['titulo'] = 'Busca de Pessoa'
        context['texto'] = 'Para você criar uma conta, precisamos que informe alguns dados para lhe encontrarmos:'
        return context


class DetalhaPessoaView(generic.View):

    template_name = 'authentication/usuario/novo/detalha_pessoa.html'
    context = {}

    @property
    def pessoa_id(self):
        return int(self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        self.carregar_context()
        if not request.POST.get('perfil_servidor'):
            messages.error(request, 'Selecione no mínimo um vínculo.')
            if request.POST.get('email'):
                self.context['email'] = request.POST.get('email')
            return render(request, self.template_name, self.context)
        if not request.POST.get('email'):
            messages.error(request, 'O e-mail institucional é obrigatório!')
            return render(request, self.template_name, self.context)

        email = request.POST.get('email')
        perfis_selected = request.POST.getlist('perfil_servidor')
        request.session['perfis_servidor'] = perfis_selected
        is_valid = validate_email(email)
        camita = GoogleEmailInstitucional()
        cadu = Cadu()
        if is_valid:
            retorno = camita.verificar_email(email)
            if 'error' not in retorno:
                login = email.split('@')
                login = login[0]
                user_cadu = cadu.buscar_por_username(login)
                if 'error' not in user_cadu:
                    request.session['username'] = user_cadu['username']
                    return redirect('auth:conta_existe', id_pessoa_sig=self.pessoa_id)
                else:
                    request.session['email'] = email
                    messages.error(request, 'Não conseguimos encontrar sua conta no CADU com o seguinte login (nome de usuário): %s' %login)
                    return redirect('auth:confirma_username', id=self.pessoa_id)

                return render(request, self.template_name, self.context)
            else:
                messages.error(request, retorno['message'])
                return render(request, self.template_name, self.context)
        else:
            self.context['is_valid'] = is_valid
            messages.error(request, 'O e-mail informado não é um e-mail valido!')
            return render(request, self.template_name, self.context)

    def get(self, request, *args, **kwargs):
        self.carregar_context()
        return render(request, self.template_name, self.context)

    def carregar_context(self):
        self.context['progress'] = 66
        self.context['titulo'] = 'Confirmação dos Dados'
        sig_pessoa = SigPessoas()
        dados_pessoa = {'format': 'json', }
        pessoa = sig_pessoa.buscar_por_id(self.pessoa_id, dados_pessoa)
        self.context['pessoa'] = pessoa
        self.context['dtnasc'] = datetime.strptime(pessoa['data_nascimento'], "%Y-%m-%d").date()
        self.context['email'] = pessoa['email']
        sig = SigServidores()
        dados_servidor = {
            'format': 'json',
            'cpf_cnpj': pessoa['cpf_cnpj'],
            # 'data_nascimento' : dt,
            'situacao__istartswith': 'Ativo',
        }
        servidores = sig.buscar_servidor(dados_servidor)
        if servidores['meta']['total_count'] >= 1:
            self.context['servidores'] = servidores['objects']


class ConfirmaUsernameView(generic.View):
    template_name = 'authentication/usuario/novo/confirma_username.html'
    context = {}

    @property
    def pessoa_id(self):
        return int(self.kwargs['id'])

    def get(self, request, *args, **kwargs):
        self.carregar_context(request)
        return render(request, self.template_name, self.context)

    def post(self, request, *args, **kwargs):
        self.carregar_context(request)
        username = request.POST.get('username')
        cadu = Cadu()
        user_cadu = cadu.buscar_por_username(username)
        if 'error' not in user_cadu:
            sig_pessoa = SigPessoas()
            dados_pessoa = {'format': 'json', }
            pessoa = sig_pessoa.buscar_por_id(self.pessoa_id, dados_pessoa)
            nome_cadu = user_cadu['first_name'] + ' ' + user_cadu['last_name']
            nome_cadu = remover_acentos(nome_cadu)
            if nome_cadu.upper() in pessoa['nome'].upper() or pessoa['nome'].upper() in nome_cadu.upper():
                request.session['username'] = user_cadu['username']
                return redirect('auth:conta_existe', id_pessoa_sig=self.pessoa_id)
            else:
                messages.error(request, 'O nome de usuário informado pertence a outra pessoa.')
        else:
            # nao tem conta - encaminhar para a criação da conta de usuario
            return redirect('auth:user_novo', id_pessoa_sig=self.pessoa_id)
        return render(request, self.template_name, self.context)

    def carregar_context(self, request):
        self.context['progress'] = 67
        self.context['titulo'] = 'Verificação do nome de usuário'
        login = request.session['email'].split('@')
        login = login[0]
        self.context['username'] = login
        self.context['email'] = request.session['email']
        self.context['pessoa_id'] = self.pessoa_id


class UserExisteView(generic.TemplateView):
    template_name = 'authentication/usuario/novo/conta_existente.html'

    @property
    def pessoa_id(self):
        return int(self.kwargs['id_pessoa_sig'])

    def get(self, request, *args, **kwargs):
        with transaction.atomic():
            cadu = Cadu()
            user_cadu = cadu.buscar_por_username(request.session['username'])
            pprint(user_cadu)

            user, created = User.objects.get_or_create(username=user_cadu['username'],
                                                       first_name=user_cadu['first_name'],
                                                       last_name=user_cadu['last_name'],
                                                       email=user_cadu['email'],
                                                       password=user_cadu['password'])

            user.pessoa.id_pessoa_sig = self.pessoa_id
            user.save()

            info_sigs = InformacoesSIG()
            info_sigs.carregar_informacoes_pessoais(user)
            perfis_servidor = request.session['perfis_servidor']
            for p in perfis_servidor:
                info_sigs.carregar_informacoes_funcionais(user, servidor_id=int(p))
            return render(request, self.template_name, {'progress': 100})


class ConfirmacaoNovoUserView(generic.TemplateView):
    template_name = 'authentication/usuario/novo/confimacao.html'

    def get(self, request, *args, **kwargs):
        request.session['email'] = None
        return render(request, self.template_name, {'progress': 100})
