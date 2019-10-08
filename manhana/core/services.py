import json
import logging
from decimal import *
from pprint import pprint

import requests
from django.conf import settings
from django.db.models import Q

from manhana.core.models.parametro import *
from manhana.core.models.processo import *

# Create a custom logger
logger = logging.getLogger(__name__)

class Arredondamento:
    #Parametro do tempo em minutos de cada aula (Definida na ODP do Instituto)
    #Todo esse valor será substituído pelo definido no model de Parâmetros do sistema assim que for implementado
    parametro = 50

    '''
    def __init__():
        self.p = Parametro.objects.get(nome='QTD_TAMANHO_AULA')'''

    def qtd_horas_aula(self, numero_aulas):
        resultado = Decimal(numero_aulas) * self.parametro / Decimal(60)
        return self.arredondar_numero(resultado)

    def arredondar_numero(self, numero):
        return round(numero, 2)

class ImportarInformacoesSIG():

    def importar_disciplina(self, docente, ano):
        payload = {
            'format' : 'json',
            'docente' : docente.id_servidor_sig,
            'ano' : ano,
            'situacao': 'ABERTA',
        }
        results = {
                    "meta": {
                        "limit": 100,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 9
                    },
                    "objects": [
                        {
                        "ano": 2019,
                        "carga_horaria": 45,
                        "carga_horaria_docente": 45,
                        "componente_curricular": "COSLO013-02-SOCIOLOGIA APLICADA AS ORGANIZAÇÕES",
                        "curso": {
                            "id": 2728350,
                            "is_ativo": True,
                            "nivel": "GRADUAÇÃO",
                            "nome": "TECNOLOGIA EM LOGÍSTICA",
                            "resource_uri": "/api/sigs/cursos/2728350/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": None,
                            "turno": None,
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "6N234",
                        "id": 148805,
                        "local": "Campus Rio Branco",
                        "nivel": "GRADUAÇÃO",
                        "periodo": 1,
                        "resource_uri": "/api/sigs/turmas/148805/",
                        "situacao": "CONSOLIDADA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T02"
                        },
                        {
                        "ano": 2019,
                        "carga_horaria": 30,
                        "carga_horaria_docente": 30,
                        "componente_curricular": "COSMA - 304-SOCIOLOGIA DA EDUCAÇÃO",
                        "curso": {
                            "id": 2765716,
                            "is_ativo": True,
                            "nivel": "GRADUAÇÃO",
                            "nome": "LICENCIATURA EM MATEMÁTICA",
                            "resource_uri": "/api/sigs/cursos/2765716/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": None,
                            "turno": None,
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "5M23",
                        "id": 149232,
                        "local": "B",
                        "nivel": "GRADUAÇÃO",
                        "periodo": 1,
                        "resource_uri": "/api/sigs/turmas/149232/",
                        "situacao": "CONSOLIDADA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T3ºM"
                        },
                        {
                        "ano": 2019,
                        "carga_horaria": 30,
                        "carga_horaria_docente": 30,
                        "componente_curricular": "TIPI06-SOCIOLOGIA I",
                        "curso": {
                            "id": 138187603,
                            "is_ativo": True,
                            "nivel": "TÉCNICO",
                            "nome": "TÉCNICO EM INFORMÁTICA PARA INTERNET - MATUTINO",
                            "resource_uri": "/api/sigs/cursos/138187603/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": "Integrado",
                            "turno": "Matutino",
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "5M5",
                        "id": 149549,
                        "local": "Campus Rio Branco",
                        "nivel": "INTEGRADO",
                        "periodo": 1,
                        "resource_uri": "/api/sigs/turmas/149549/",
                        "situacao": "ABERTA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T01"
                        },
                        {
                        "ano": 2019,
                        "carga_horaria": 30,
                        "carga_horaria_docente": 30,
                        "componente_curricular": "TIPI06-SOCIOLOGIA I",
                        "curso": {
                            "id": 138187603,
                            "is_ativo": True,
                            "nivel": "TÉCNICO",
                            "nome": "TÉCNICO EM INFORMÁTICA PARA INTERNET - MATUTINO",
                            "resource_uri": "/api/sigs/cursos/138187603/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": "Integrado",
                            "turno": "Matutino",
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "6M3",
                        "id": 149634,
                        "local": "Campus Rio Branco",
                        "nivel": "INTEGRADO",
                        "periodo": 1,
                        "resource_uri": "/api/sigs/turmas/149634/",
                        "situacao": "ABERTA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T02"
                        },
                        {
                        "ano": 2019,
                        "carga_horaria": 30,
                        "carga_horaria_docente": 30,
                        "componente_curricular": "TIPI33-SOCIOLOGIA III",
                        "curso": {
                            "id": 138187603,
                            "is_ativo": True,
                            "nivel": "TÉCNICO",
                            "nome": "TÉCNICO EM INFORMÁTICA PARA INTERNET - MATUTINO",
                            "resource_uri": "/api/sigs/cursos/138187603/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": "Integrado",
                            "turno": "Matutino",
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "6M1",
                        "id": 149712,
                        "local": "Campus Rio Branco",
                        "nivel": "INTEGRADO",
                        "periodo": 1,
                        "resource_uri": "/api/sigs/turmas/149712/",
                        "situacao": "ABERTA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T01"
                        },
                        {
                        "ano": 2019,
                        "carga_horaria": 30,
                        "carga_horaria_docente": 30,
                        "componente_curricular": "TIPI20-SOCIOLOGIA II",
                        "curso": {
                            "id": 138187603,
                            "is_ativo": True,
                            "nivel": "TÉCNICO",
                            "nome": "TÉCNICO EM INFORMÁTICA PARA INTERNET - MATUTINO",
                            "resource_uri": "/api/sigs/cursos/138187603/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": "Integrado",
                            "turno": "Matutino",
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "6M4",
                        "id": 149761,
                        "local": "Campus Rio Branco",
                        "nivel": "INTEGRADO",
                        "periodo": 1,
                        "resource_uri": "/api/sigs/turmas/149761/",
                        "situacao": "ABERTA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T01"
                        },
                        {
                        "ano": 2019,
                        "carga_horaria": 30,
                        "carga_horaria_docente": 30,
                        "componente_curricular": "INFI1654-SOCIOLOGIA IV",
                        "curso": {
                            "id": 138187607,
                            "is_ativo": True,
                            "nivel": "TÉCNICO",
                            "nome": "TÉCNICO EM INFORMÁTICA - MATUTINO",
                            "resource_uri": "/api/sigs/cursos/138187607/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": "Integrado",
                            "turno": "Matutino",
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "6M5",
                        "id": 149771,
                        "local": "Campus Rio Branco",
                        "nivel": "INTEGRADO",
                        "periodo": 1,
                        "resource_uri": "/api/sigs/turmas/149771/",
                        "situacao": "ABERTA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T01"
                        },
                        {
                        "ano": 2019,
                        "carga_horaria": 45,
                        "carga_horaria_docente": 45,
                        "componente_curricular": "COSADM011-SOCIOLOGIA APLICADA ÀS ORGANIZAÇÕES",
                        "curso": {
                            "id": 2857773,
                            "is_ativo": True,
                            "nivel": "GRADUAÇÃO",
                            "nome": "BACHARELADO EM ADMINISTRAÇÃO",
                            "resource_uri": "/api/sigs/cursos/2857773/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": None,
                            "turno": None,
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "6T123",
                        "id": 150141,
                        "local": "Campus Rio Branco",
                        "nivel": "GRADUAÇÃO",
                        "periodo": 2,
                        "resource_uri": "/api/sigs/turmas/150141/",
                        "situacao": "ABERTA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T2°P VES"
                        },
                        {
                        "ano": 2019,
                        "carga_horaria": 30,
                        "carga_horaria_docente": 30,
                        "componente_curricular": "COSMA - 206-SOCIOLOGIA GERAL",
                        "curso": {
                            "id": 2765716,
                            "is_ativo": True,
                            "nivel": "GRADUAÇÃO",
                            "nome": "LICENCIATURA EM MATEMÁTICA",
                            "resource_uri": "/api/sigs/cursos/2765716/",
                            "tipo_oferta": "Anual",
                            "tipo_participacao": "Presencial",
                            "tipo_stricto": None,
                            "tipo_tecnico": None,
                            "turno": None,
                            "unidade_responsavel": "CAMPUS RIO BRANCO"
                        },
                        "docente": {
                            "cargo": "PROFESSOR ENS BASICO TECN TECNOLOGICO",
                            "categoria": "Docente                       ",
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "escolaridade": "Ensino superior                         ",
                            "formacao": "MESTRADO",
                            "id": 10711,
                            "nome": "Usuário Teste SisRAD",
                            "pessoa": {
                            "cpf_cnpj": 63844586083,
                            "data_nascimento": "1981-04-09",
                            "email": "sisrad.teste@ifac.edu.br",
                            "grupo_sanguineo": None,
                            "id": 65796,
                            "nome": "Usuário Teste SisRAD",
                            "nome_mae": "Mãe Usuário Teste SisRAD                     ",
                            "nome_pai": None,
                            "registro_geral": "238233728        ",
                            "resource_uri": "/api/sigs/pessoas/65796/",
                            "rg_data_expedicao": "1997-11-20T00:00:00",
                            "rg_orgao_expedidor": "SSP       ",
                            "rg_uf": 26,
                            "sexo": "F",
                            "tipo": "F"
                            },
                            "regime_trabalho": "Dedicação exclusiva",
                            "resource_uri": "/api/sigs/servidores/10711/",
                            "siape": 2218898,
                            "situacao": "Ativo          ",
                            "tipo_servidor": "Ativo Permanente",
                            "unidade_responsavel": "CAMPUS RIO BRANCO",
                            "unidadeexercicio": "DIR ENSINO, PESQUISA E EXTENSAO - CRB",
                            "unidadelotacao": "DIR ENSINO, PESQUISA E EXTENSAO - CRB"
                        },
                        "horario": "5M34",
                        "id": 150143,
                        "local": "campus Rio Branco",
                        "nivel": "GRADUAÇÃO",
                        "periodo": 2,
                        "resource_uri": "/api/sigs/turmas/150143/",
                        "situacao": "ABERTA",
                        "tipo_componente": "COMPONENTE CURRICULAR",
                        "tipo_turma": "REGULAR",
                        "turma": "T2ºM"
                        }
                    ]
                }
        if results:
            return results
        else:
            raise Exception('Nenhum dado encontrado.')


class CalculaCargahorariaSemanal():

    def calcular_qtdaulas(self, horario, ch_disciplina=None, ch_docente=None):
        
        if ch_disciplina and ch_docente:
            if ch_disciplina == ch_docente:
                return self.calcular_qtdaulas_horario(horario)    
            else:
                # Transforma a carga horaria do docente para minutos
                ch_docente_min = ch_docente * 60
                # Calcula a quantidade de aulas total da disciplina com base na carga horaria do docente
                qtd_aulas_total = Decimal(ch_docente / 50)
                # retorna a quantidade média de aulas, baseando-se em 20 semanas do semestre letivo 
                return round(qtd_aulas_total / 20)
        else:    
            return self.calcular_qtdaulas_horario(horario)

    def calcular_qtdaulas_horario(self, horario):
        soma = 0 
        if ' ' in horario:
            aux = horario.split(' ')
            for x in aux:
                if 'M' in x:
                    dia_semana, horarios = x.split('M')
                elif 'T' in x:
                    dia_semana, horarios = x.split('T')
                elif 'N' in x:
                    dia_semana, horarios = x.split('N')
                soma = soma + (len(horarios) * len(dia_semana))
        else:
            if 'M' in horario:
                dia_semana, horarios = horario.split('M')
            elif 'T' in horario:
                dia_semana, horarios = horario.split('T')
            elif 'N' in horario:
                dia_semana, horarios = horario.split('N')
            soma = len(horarios) * len(dia_semana)
        
        return soma
        


class VerificarAtividadesObrigatorias():

    def verificar_atividades_obrigatorias(self, processo, categoria_atividade):
        atividades = Atividade.objects.filter(Q(categoria_atividade=categoria_atividade) & Q(is_ativo=True) & (Q(ch_minima__gt=0) | Q(is_obrigatorio=True)))

        try:
            atividade_ensino = Atividade.objects.get(descricao='Aula')
            argumento_ensino = ArgumentoCategoria.objects.get(categoria_atividade=atividade_ensino.categoria_atividade, campo='Tipo de curso')
            registro_atividade_ensino = RegistroAtividade.objects.filter(atividade=atividade_ensino, processo=processo)
            informacoes_argumentos_ensino = InformacaoArgumento.objects.filter(argumento=argumento_ensino, registro_atividade__in=registro_atividade_ensino)

            atividades_obg = []

            # Obrigaatória pelo tipo de curso
            for a in atividades:
                
                if a.is_obrigatorio:
                    if not a in atividades_obg:
                        atividades_obg.append(a)

                for info in informacoes_argumentos_ensino:
                    if 'técnico' in info.valor_texto.lower():
                        if 'Integrado' in info.valor_texto:
                            if ('integrados' in a.descricao.lower() or 'integrado' in a.descricao.lower()) and ('obrigatório' in a.descricao.lower() or 'obrigatorio' in a.descricao.lower()):
                                if not a in atividades_obg:
                                    atividades_obg.append(a)
                        if 'Subsequente' in info.valor_texto:
                            if ('subsequentes' in a.descricao.lower() or 'subsequente' in a.descricao.lower()) and ('obrigatório' in a.descricao.lower() or 'obrigatorio' in a.descricao.lower()):
                                if not a in atividades_obg:
                                    atividades_obg.append(a)
                        if 'Concomitante' in info.valor_texto:
                            if ' concomitante ' in a.descricao.lower()  and ('obrigatório' in a.descricao.lower() or 'obrigatorio' in a.descricao.lower()):
                                if not a in atividades_obg:
                                    atividades_obg.append(a)
                        if 'eja' in info.valor_texto.lower():
                            if ' eja' in a.descricao.lower() and ('obrigatório' in a.descricao.lower() or 'obrigatorio' in a.descricao.lower()):
                                if not a in atividades_obg:
                                    atividades_obg.append(a)
                        if 'obrigatório' in a.descricao.lower() or 'obrigatorio' in a.descricao.lower():
                            if 'técnico' in a.descricao.lower() and 'integrado' not in a.descricao.lower() and 'subsequente' not in a.descricao.lower() and 'concomitante' not in a.descricao.lower() and 'eja' not in a.descricao.lower():
                                if not a in atividades_obg:
                                    atividades_obg.append(a)
                    
                    elif 'graduação' in info.valor_texto.lower():
                        if 'graduação' in a.descricao.lower() and ('obrigatório' in a.descricao.lower() or 'obrigatorio' in a.descricao.lower()):
                            if not a in atividades_obg:
                                atividades_obg.append(a)

            return atividades_obg
        except Exception as ex:
            logger.exception(f"Ocorreu uma exceção ao verificar atividades obrigatórias da categoria '{categoria_atividade.nome}' no processo {processo}: {ex}")


class ImportarUnidadesSIG:

    def buscar_unidade(self, payload):
        results = requests.get(settings.API_UNIDADES, params=payload, headers=settings.HEADER_AUTH)
        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            return None
            
    def buscar_por_id(self, id, payload):
        results = requests.get(settings.API_UNIDADES + '/%d/' % id, params=payload, headers=settings.HEADER_AUTH)
        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            return None

    def listar_todos(self, limit=None):
        if limit:
            results = requests.get(settings.API_UNIDADES, params={'limit' : limit},  headers=settings.HEADER_AUTH)
        else:
            results = requests.get(settings.API_UNIDADES, headers=settings.HEADER_AUTH)
        return json.loads(results.content.decode('utf-8'))

    def buscar_unidades_ativas(self):
        payload = {
            'format': 'json',
            'is_ativa': True,
            'limit': 500,
        }
        results = requests.get(settings.API_UNIDADES, params=payload, headers=settings.HEADER_AUTH)

        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            raise Exception('Nenhum dado encontrado.')


    def buscar_unidades_filhas(self, id_pai):
        payload = {
            'format': 'json',
            'unidade_responsavel': id_pai,
            'is_ativa': True,
            'limit': 500,
        }
        results = requests.get(settings.API_UNIDADES, params=payload, headers=settings.HEADER_AUTH)

        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            raise Exception('Nenhum dado encontrado.')

class IntegraResponsavelUnidadesSIG:

    def buscar_responsabilidade_servidor(self, id_servidor):
        payload = {
            'format': 'json',
            'servidor': id_servidor,
        }
        results = requests.get(settings.API_RESPONSAVEL_UNIDADE, params=payload, headers=settings.HEADER_AUTH)
        if results:
            return json.loads(results.content.decode('utf-8'))
        else:
            return None

    def listar_todos(self, limit=None):
        if limit:
            results = requests.get(settings.API_RESPONSAVEL_UNIDADE, params={'limit' : limit},  headers=settings.HEADER_AUTH)
        else:
            results = requests.get(settings.API_RESPONSAVEL_UNIDADE, headers=settings.HEADER_AUTH)
        return json.loads(results.content.decode('utf-8'))

    def buscar_responsabilidade_ativa(self, id_servidor):
        payload = {
            'format': 'json',
            'servidor': id_servidor,
            'nivel_responsabilidade': 'C',
            'data_fim': None,
        }
        results = requests.get(settings.API_RESPONSAVEL_UNIDADE, params=payload, headers=settings.HEADER_AUTH)
        if results:    
            return json.loads(results.content.decode('utf-8'))
        else:
            return None
