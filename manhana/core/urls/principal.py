from django.urls import path, include
from django.conf.urls import url
from manhana.core.views import principal
from manhana.authentication.views import VerificaUsuarioView


app_name = 'core'
urlpatterns = [
    path('', VerificaUsuarioView.as_view(), name="verifica_user"),
    path('painel/', principal.IndexView.as_view(), name='vw_index'),
    path('usuario/detalhe/', principal.UserDetalheView.as_view(), name="user-detalhe"),
    path('usuario/perfil/docente/<int:pk>/', principal.DocenteEditarView.as_view(), name="docente-editar"),
    path('usuario/perfil/<slug:slug>/<int:pk>/responsabilidades/importar/', principal.importar_responsabilidades, name='importar-responsabilidades'),
    path('usuario/perfil/<slug:slug>/<int:pk>/responsabilidades/', principal.ListaResponsabilidadesServidorView.as_view(), name='lista-responsabilidades'),

    path('visualizar/unidades/sig/', principal.visualisar_organograma_sig, name='visualisar-organograma'),
    path('importar/unidades/sig/', principal.importar_unidades, name='importar-organograma'),


    path('vinculo/unidades/lista/', principal.ListaEstruturaOrganizacionalView.as_view(), name='lista-unidades-vinculo'),
    path('vinculo/unidades/<int:pk>/servidores/lista/', principal.lista_servidores_vinculados, name='lista-servidores-vinculados'),
    path('vinculo/unidades/<int:pk>/servidores/adicionar/', principal.AdicionaVinculoServidorView.as_view(), name='adicionar-servidores-vinculados'),
    path('vinculo/<int:pk>/editar/', principal.EditarVinculoServidorView.as_view(), name="vinculo-editar"),
    path('vinculo/inativar/', principal.inativar_vínculo, name="vinculo-inativar"),

    path('ajax/vinculo/<int:pk>/detalhe/', principal.detalha_vinculo, name='ajax-vinculo-detail'),
    path('ajax/servidor/<int:pk>/detalhe/', principal.detalha_servidor, name='ajax-servidor-detail'),
    path('ajax/responsabilidade/<int:pk>/detalhe/', principal.detalha_responsabilidade, name='ajax-responsabilidade-detail'),

    path('', include('manhana.core.urls.processo')),
]