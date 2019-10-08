from django.test import TestCase
from manhana.core.models.processo import *
from manhana.core.models.parametro import *
from manhana.authentication.models import *
from mixer.backend.django import mixer
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError
from django.db.models import ProtectedError
import pytest
import pdb

class TestProcesso(TestCase): 

    fixtures = ['authentication/fixtures/authentication.json', 'core/fixtures/core.json',]

    @classmethod
    def setUpClass(cls):
        super(TestProcesso, cls).setUpClass()
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@email.com',
            password='secret'
        )
        cls.user.pessoa.cpf = '28675655029'
        cls.user.save()

        cls.grupo = GrupoDocente.objects.get(nome='Grupo 2')
        cls.estrutura_organizacional = EstruturaOrganizacional.objects.get(nome='CAMPUS RIO BRANCO')
        cls.docente = DocenteProfile.objects.create(
            siape='2063392',
            cargo='PROFESSOR ENS BASICO TECN TECNOLOGICO',
            unidade_lotacao = 'DIR ENSINO, PESQUISA E EXTENSAO - CRB',
            unidade_exercicio = 'DIRETORIA SISTEMICA DE GESTAO TECNOLOGIA DA INFORMACAO - DSGTI',
            unidade_responsavel = cls.estrutura_organizacional,
            tipo_servidor = 'Ativo Permanente',
            categoria = 'Docente',
            regime_trabalho = 'Dedicação exclusiva',
            situacao = 'Ativo',
            titulacao = 'ESPECIALIZAÇÃO',
            id_servidor_sig = 10790,
            grupo = cls.grupo,
            pessoa = cls.user.pessoa
        )
        cls.sp_rascunho = SituacaoProcesso.objects.get(nome='Rascunho')
        cls.sp_enviado, created  = SituacaoProcesso.objects.get_or_create(nome='Enviado')

        cls.tipo_processo = CategoriaProcesso.objects.get(nome='PIT', )
        cls.tipo_processo.situacao_processso.add(cls.sp_rascunho)
        cls.tipo_processo.situacao_processso.add(cls.sp_enviado)

        cls.processo = Processo.objects.create(
            ano = 2019,
            semestre = 1,
            interessado = cls.docente, 
            tipo_processo = cls.tipo_processo, 
            situacao = cls.sp_rascunho,
            criado_por = cls.user,
            modificado_por = cls.user
        )

    @classmethod
    def tearDownClass(cls):
        super(TestProcesso, cls).tearDownClass()
        cls.processo.delete()
        cls.sp_enviado.delete()       

        cls.docente.delete()
        cls.user.delete()
        
    def test_string_representation(self):
        """Testa a representação string do modelo Processo"""
        retorno_previsto = f'N.º {self.processo.numero_processo} - {self.processo.tipo_processo} ({self.processo.ano}/{self.processo.semestre}) do {self.processo.interessado.pessoa.user.get_full_name()}'
        self.assertEqual(str(self.processo), retorno_previsto)

    def test_get_absolute_url(self):
        """Testa o método get_absolute_url do modelo Processo"""
        self.assertEqual(self.processo.get_absolute_url(), '/admin/processo/{}/detalhe/'.format(self.processo.pk))
    
    def test_unique_together_ano_semestre_tipo_processo_interessado(self):
        """Testa criar um tipo de processo por ano e semestre para cada interessado"""
        with self.assertRaises(IntegrityError):
        # with pytest.raises(IntegrityError) as e:
            processo2 = Processo.objects.create(
                ano = 2019,
                semestre = 1,
                interessado = self.docente, 
                tipo_processo = self.tipo_processo, 
                situacao = self.sp_rascunho,
                criado_por = self.user,
                modificado_por = self.user
            )
        # assert str(e.value) == "Invalid email format"
    
    def test_delete_processo_rascunho(self):
        """Testa deletar processo em rascunho"""
        processo3 = Processo.objects.create(
                ano = 2019,
                semestre = 2,
                interessado = self.docente, 
                tipo_processo = self.tipo_processo, 
                situacao = self.sp_rascunho,
                criado_por = self.user,
                modificado_por = self.user
            )
        processo3.delete()

    def test_delete_processo_sem_ser_rascunho(self):
        """Testa deletar processo sem ser rascunho"""
        with pytest.raises(ValidationError) as excinfo:
            processo3 = Processo.objects.create(
                ano = 2019,
                semestre = 2,
                interessado = self.docente, 
                tipo_processo = self.tipo_processo, 
                situacao = self.sp_enviado,
                criado_por = self.user,
                modificado_por = self.user
            )

            self.assertEqual(2019, processo3.ano)
            self.assertEqual('Enviado', processo3.situacao.nome)
            processo3.delete()
        
        assert 'Só processos em rascunho podem ser deletados.' in str(excinfo.value)
