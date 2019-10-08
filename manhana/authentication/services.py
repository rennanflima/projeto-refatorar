import requests, json
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.shortcuts import render, get_object_or_404
from django.utils import six
import hashlib
from pprint import pprint
from django.conf import settings
from unicodedata import normalize
from django.contrib.auth.decorators import login_required
from .models import Pessoa, DocenteProfile, GrupoDocente
from datetime import datetime  
from .choices import *
from .models import *
from manhana.core.services import IntegraResponsavelUnidadesSIG
from manhana.core.models.parametro import EstruturaOrganizacional, ResponsavelUnidade
from django.db.models import Q
import logging


# Create a custom logger
logger = logging.getLogger(__name__)



class GoogleEmailInstitucional:

    def verificar_email(self, email):
        payload = {'email': email,}
        results = requests.get(settings.API_CAMITA, params=payload)
        return json.loads(results.content.decode('utf-8'))


class Cadu:

    def salvar(self, usuario):
        user_cadu = requests.post(settings.API_CADU, json = usuario)
        return json.loads(user_cadu.content.decode('utf-8'))
    
    def editar(self, id, usuario):
        usuario = json.dumps(usuario, ensure_ascii=False)
        user_cadu = requests.put(settings.API_CADU + str(id) + '/', data = usuario, headers = {'Content-type': 'application/json'})
        return json.loads(user_cadu.content.decode('utf-8'))

    def excluir(self, id):
        r = requests.delete(settings.API_CADU + str(id))

    def buscar_todos(self):
        results = requests.get(settings.API_CADU)
        return json.loads(results.content.decode('utf-8'))

    def buscar_por_username(self, login):
        user_cadu = requests.get('https://cadu.ifac.edu.br/api/user/' + str(login))
        return json.loads(user_cadu.content.decode('utf-8'))

class SigServidores:
    
    def buscar_servidor(self, payload):
        results = requests.get(settings.API_SERVIDORES, params=payload, headers=settings.HEADER_AUTH)
        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            return None
    
    def buscar_por_id(self, id, payload):
        results = requests.get(settings.API_SERVIDORES + '/%d/' % id, params=payload, headers=settings.HEADER_AUTH)
        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            return None

    def listar_todos(self, limit=None):
        if limit:
            results = requests.get(settings.API_SERVIDORES, params={'limit' : limit},  headers=settings.HEADER_AUTH)
        else:
            results = requests.get(settings.API_SERVIDORES, headers=settings.HEADER_AUTH)
        return json.loads(results.content.decode('utf-8'))

class SigPessoas:
        
    def buscar_pessoa(self, payload):
        results = requests.get(settings.API_PESSOAS, params=payload, headers=settings.HEADER_AUTH)
        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            return None
            
    def buscar_por_id(self, id, payload):
        results = requests.get(settings.API_PESSOAS + '/%d/' % id, params=payload, headers=settings.HEADER_AUTH)
        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            return None

    def listar_todos(self, limit=None):
        if limit:
            results = requests.get(settings.API_PESSOAS, params={'limit' : limit},  headers=settings.HEADER_AUTH)
        else:
            results = requests.get(settings.API_PESSOAS, headers=settings.HEADER_AUTH)
        return json.loads(results.content.decode('utf-8'))


class Docente:
    def buscar_docente(self, cpf, siape):
        servidor = SigServidores()
        params = {'cpf_cnpj':cpf, 'siape': siape, 'cargo': 'Docente'}
        docente = servidor.buscar_servidor(payload=params)
        if docente:
            return docente
        else:
            return None


def remover_acentos(txt):
    return normalize('NFKD', txt).encode('ASCII', 'ignore').decode('ASCII')


def classifica_usuario(docente):
    if docente.tipo_servidor == 'Ativo Permanente':
        if docente.regime_trabalho == '20 horas semanais':
            grupo = GrupoDocente.objects.get(nome='Grupo 1')
        elif docente.regime_trabalho == '40 horas semanais' or docente.regime_trabalho == 'Dedicação exclusiva':
            grupo = GrupoDocente.objects.get(nome='Grupo 2')
    elif docente.tipo_servidor == 'Professor Temporario' or docente.tipo_servidor == 'Professor Substituto':
        if docente.regime_trabalho == '20 horas semanais':
            grupo = GrupoDocente.objects.get(nome='Grupo 3 (20 horas)')
        else:
            grupo = GrupoDocente.objects.get(nome='Grupo 3 (40 horas)')
    docente.grupo = grupo
    docente.save()


class InformacoesSIG():

    def carregar_informacoes_pessoais(self, user):
        sig_pessoa = SigPessoas()
        dados_pessoa = {'format' : 'json',}
        pessoa = sig_pessoa.buscar_por_id(user.pessoa.id_pessoa_sig, dados_pessoa)

        if pessoa:
        
            user.pessoa.cpf = pessoa['cpf_cnpj']
            user.pessoa.data_nascimento = pessoa['data_nascimento']
            user.pessoa.nome_mae = pessoa['nome_mae'].strip().title().replace(' De ', ' de ').replace(' Da ', ' da ').replace(' Do ', ' do ').replace(' Das ', ' das ').replace(' Dos ', ' dos ').replace(' E ', ' e ')
            if pessoa['nome_pai']:
                user.pessoa.nome_pai = pessoa['nome_pai'].strip().title().replace(' De ', ' de ').replace(' Da ', ' da ').replace(' Do ', ' do ').replace(' Das ', ' das ').replace(' Dos ', ' dos ').replace(' E ', ' e ')
            user.pessoa.registro_geral = pessoa['registro_geral']
            user.pessoa.rg_orgao_expedidor = pessoa['rg_orgao_expedidor']
            # Converter data '2010-10-25T00:00:00' para o formato: AAAA-MM-DD
            user.pessoa.rg_data_expedicao = datetime.strptime(pessoa['rg_data_expedicao'], '%Y-%m-%dT%H:%M:%S')
            user.pessoa.rg_uf = pessoa['rg_uf']
            user.pessoa.sexo = pessoa['sexo']
            user.pessoa.grupo_sanguineo = pessoa['grupo_sanguineo']

            user.save()

    def carregar_informacoes_funcionais(self, user, servidor_id=None, perfil=None):
        sig_servidor = SigServidores()
        dados_servidor = {'format' : 'json',}

        if perfil:
            servidor = sig_servidor.buscar_por_id(perfil.id_servidor_sig, dados_servidor)
        else:
            servidor = sig_servidor.buscar_por_id(servidor_id, dados_servidor)
        
        if servidor['categoria'].strip() == 'Técnico Administrativo':
            if perfil:
                perfil = perfil
            else:
                perfil = TaeProfile()

            perfil.siape = servidor['siape']
            
            try:
                unidade_lotacao = EstruturaOrganizacional.objects.filter(Q(is_ativo=True) & (Q(id_unidade_sig=servidor['unidade_lotacao']['id']) | Q(nome=servidor['unidade_lotacao']['nome'].strip()))).first()
                perfil.unidade_lotacao = unidade_lotacao
            except Exception as e:
                logger.exception(f'Ocorreu uma exceção ao víncular a unidade de lotação: {e}')
                unidade_lotacao = EstruturaOrganizacional.objects.filter(nome='INDEFINIDO', is_ativo=True).first()
                perfil.unidade_lotacao = unidade_lotacao

            try:
                unidade_exercicio = EstruturaOrganizacional.objects.filter(Q(is_ativo=True) & (Q(id_unidade_sig=servidor['unidade_exercicio']['id']) | Q(nome=servidor['unidade_exercicio']['nome'].strip()))).first()
                perfil.unidade_exercicio = unidade_exercicio
            except Exception as e:
                logger.exception(f'Ocorreu uma exceção ao víncular a unidade de exercício: {e}')
                unidade_exercicio = EstruturaOrganizacional.objects.filter(nome='INDEFINIDO', is_ativo=True).first()
                perfil.unidade_exercicio = unidade_exercicio

            try:                
                if unidade_exercicio.estrutura_pai.tipo_estrutura == EstruturaOrganizacional.CAMPUS:
                    perfil.unidade_responsavel = unidade_exercicio.estrutura_pai

                elif unidade_exercicio.estrutura_pai.estrutura_pai and unidade_exercicio.estrutura_pai.estrutura_pai.tipo_estrutura == EstruturaOrganizacional.CAMPUS:
                    perfil.unidade_responsavel = unidade_exercicio.estrutura_pai.estrutura_pai
                
                else:
                    unidade_responsavel = EstruturaOrganizacional.objects.filter(Q(is_ativo=True) & (Q(id_unidade_sig=servidor['unidade_responsavel']['id']) | Q(nome=servidor['unidade_responsavel']['nome'].strip()))).first()
                    perfil.unidade_responsavel = unidade_responsavel

            except Exception as e:
                logger.exception(f'Ocorreu uma exceção ao víncular a unidade responsável: {e}')
                unidade_responsavel = EstruturaOrganizacional.objects.filter(nome='INDEFINIDO', is_ativo=True).first()
                perfil.unidade_responsavel = unidade_responsavel


            perfil.cargo = servidor['cargo'].strip().title().replace(' De ', ' de ').replace(' Da ', ' da ').replace(' Do ', ' do ').replace(' Das ', ' das ').replace(' Dos ', ' dos ').replace(' E ', ' e ')
            perfil.tipo_servidor = servidor['tipo_servidor'].strip()
            perfil.categoria = servidor['categoria'].strip().title()
            perfil.regime_trabalho = servidor['regime_trabalho'].strip()
            perfil.situacao = servidor['situacao'].strip()
            perfil.titulacao = servidor['formacao'].strip().title()
            perfil.id_servidor_sig = servidor['id']

        elif servidor['categoria'].strip() == 'Docente':
            if perfil:
                perfil = perfil
            else:
                perfil = DocenteProfile()

            perfil.siape = servidor['siape']
            
            try:
                unidade_lotacao = EstruturaOrganizacional.objects.filter(Q(is_ativo=True) & (Q(id_unidade_sig=servidor['unidade_lotacao']['id']) | Q(nome=servidor['unidade_lotacao']['nome'].strip()))).first()
                perfil.unidade_lotacao = unidade_lotacao
            except Exception as e:
                logger.exception(f'Ocorreu uma exceção ao víncular a unidade de lotação: {e}')
                unidade_lotacao = EstruturaOrganizacional.objects.filter(nome='INDEFINIDO', is_ativo=True).first()
                perfil.unidade_lotacao = unidade_lotacao

            try:
                unidade_exercicio = EstruturaOrganizacional.objects.filter(Q(is_ativo=True) & (Q(id_unidade_sig=servidor['unidade_exercicio']['id']) | Q(nome=servidor['unidade_exercicio']['nome'].strip()))).first()
                perfil.unidade_exercicio = unidade_exercicio
            except Exception as e:
                logger.exception(f'Ocorreu uma exceção ao víncular a unidade de exercício: {e}')
                unidade_exercicio = EstruturaOrganizacional.objects.filter(nome='INDEFINIDO', is_ativo=True).first()
                perfil.unidade_exercicio = unidade_exercicio
                
            try:                
                if unidade_exercicio.estrutura_pai.tipo_estrutura == EstruturaOrganizacional.CAMPUS:
                    perfil.unidade_responsavel = unidade_exercicio.estrutura_pai

                elif unidade_exercicio.estrutura_pai.estrutura_pai and unidade_exercicio.estrutura_pai.estrutura_pai.tipo_estrutura == EstruturaOrganizacional.CAMPUS:
                    perfil.unidade_responsavel = unidade_exercicio.estrutura_pai.estrutura_pai
                
                else:
                    unidade_responsavel = EstruturaOrganizacional.objects.filter(Q(is_ativo=True) & (Q(id_unidade_sig=servidor['unidade_responsavel']['id']) | Q(nome=servidor['unidade_responsavel']['nome'].strip()))).first()
                    perfil.unidade_responsavel = unidade_responsavel

            except Exception as e:
                logger.exception(f'Ocorreu uma exceção ao víncular a unidade responsável: {e}')
                unidade_responsavel = EstruturaOrganizacional.objects.filter(nome='INDEFINIDO', is_ativo=True).first()
                perfil.unidade_responsavel = unidade_responsavel

            perfil.cargo = servidor['cargo'].strip().title().replace(' De ', ' de ').replace(' Da ', ' da ').replace(' Do ', ' do ').replace(' Das ', ' das ').replace(' Dos ', ' dos ').replace(' E ', ' e ')
            perfil.tipo_servidor = servidor['tipo_servidor'].strip()
            perfil.categoria = servidor['categoria'].strip()
            perfil.regime_trabalho = servidor['regime_trabalho'].strip()
            perfil.situacao = servidor['situacao'].strip()
            perfil.titulacao = servidor['formacao'].strip().title()
            perfil.id_servidor_sig = servidor['id']

        
        perfil.pessoa = user.pessoa
        perfil.save()

        if servidor['categoria'].strip() == 'Docente':
            if isinstance(perfil, DocenteProfile) and not perfil.grupo:
                classifica_usuario(perfil)   

        self.carrega_responsabilidades_sig(perfil)


    def carrega_responsabilidades_sig(self, servidor):   
        responsavel_sig = IntegraResponsavelUnidadesSIG()
        responsabilidades_servidor = ResponsavelUnidade.objects.filter(servidor=servidor)
        retorno = responsavel_sig.buscar_responsabilidade_servidor(servidor.id_servidor_sig)
        responsabilidades = retorno['objects']
        for r in responsabilidades:
            estrutura = EstruturaOrganizacional.objects.filter(id_unidade_sig=r['unidade']['id'], is_ativo=True).first()
            if estrutura:
                if not responsabilidades_servidor.exists():
                    funcao = ResponsavelUnidade()
                    funcao.servidor = servidor
                    funcao.unidade = estrutura
                    funcao.nivel_responsabilidade = r['nivel_responsabilidade']
                    funcao.data_inicio = r['data_inicio']
                    funcao.id_responsabilidade_sig = int(r['id'])
                    if r['data_fim']:
                        funcao.data_termino = r['data_fim']
                    funcao.save()
                elif responsabilidades_servidor.count() < retorno['meta']['total_count']:
                    try:
                        ru = ResponsavelUnidade.objects.get(servidor=servidor, id_responsabilidade_sig=int(r['id']))
                        if not ru.data_termino:
                            if r['data_fim']:
                                ru.data_termino = r['data_fim']
                            ru.save()
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
                else:
                    for ru in responsabilidades_servidor:
                        if ru.id_responsabilidade_sig == int(r['id']):
                            if not ru.data_termino:
                                if r['data_fim']:
                                    ru.data_termino = r['data_fim']
                            ru.id_responsabilidade_sig = int(r['id'])
                            ru.save()