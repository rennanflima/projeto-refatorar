from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from manhana.core.views.principal import DocenteEditarView
from manhana.core.models.parametro import *
from manhana.authentication.models import *
from unittest.mock import patch, MagicMock
import pytest

class DocenteEditarViewTest(TestCase):
    
    fixtures = ['authentication/fixtures/authentication.json', 'core/fixtures/core.json',]
    
    @classmethod
    def setUpClass(cls):
        super(DocenteEditarViewTest, cls).setUpClass()
        cls.factory = RequestFactory()

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

        cls.url = reverse('core:docente-editar', kwargs={'pk': cls.docente.pk})

    @classmethod
    def tearDownClass(cls):
        super(DocenteEditarViewTest, cls).tearDownClass()

        cls.docente.delete()
        cls.user.delete()

    @patch('authentication.models.DocenteProfile.save', MagicMock(name="save"))
    def test_redirect_success_url(self):
        """Testa o redirecionamento de sucesso da view DocenteEditarView"""
        
        area_contratacao = AreaContratacao.objects.get(nome='Informática Geral/Banco de Dados/Redes')
        #Login
        self.client.login(username='testuser', password='secret')
        
        # Get response
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/usuario/perfil_docente_form.html')
        self.assertContains(response,'Editar Perfil Docente')

        #Post response
        post_data = {
            'lattes' : 'http://lattes.cnpq.br/2076449581151181',
            'area_contratacao': area_contratacao.pk
        }
        response = self.client.post(self.url, post_data, follow=True)
        self.assertNotContains(response,'Editar Perfil Docente')
        self.assertContains(response,'Detalhar Usuario')
        self.assertRedirects(response, '/admin/usuario/detalhe/')



