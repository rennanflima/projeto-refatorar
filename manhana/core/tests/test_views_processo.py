from django.test import TestCase, RequestFactory
from mixer.backend.django import mixer
from django.urls import reverse
from django.contrib.auth.models import User, AnonymousUser
from unittest.mock import patch, MagicMock
from manhana.core.views.processo import *
import pytest

class ProcessoNovoViewTest(TestCase):
    
    def setUp(self):
        self.url = reverse('core:processo-novo')
        self.factory = RequestFactory()

    def test_processo_novo_redirect_if_not_logged_in(self):
        # request = self.client.get(self.url)
        # request.user = AnonymousUser()
        response = self.client.get(self.url)
        # response = ProcessoNovoView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/admin/processo/novo/', status_code=302, target_status_code=302)

