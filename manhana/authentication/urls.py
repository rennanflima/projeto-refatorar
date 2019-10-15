
from django.urls import path, re_path, include
from manhana.authentication.views import *

app_name = 'authentication'
urlpatterns = [
    path('', VerificaUsuarioView.as_view(), name="verifica_user"),
    path('usuario/informacao_adicional/form/', InfoAdicionaisUserView.as_view(), name="info_adicional_user"),
    path('usuario/informacao_adicional/detalhe/', SelecionarVinculoView.as_view(), name="selecao_vinculo"),
    path('usuario/selecao/perfil/', SelecionarPerfilView.as_view(), name="selecao_perfil"),

    path('usuario/buscar/', BuscaPessoaView.as_view(), name='buscar_pessoa'),
    path('usuario/buscar/pessoa/detalhe/<int:id>/', DetalhaPessoaView.as_view(), name='detalha_pessoa'),
    path('usuario/buscar/pessoa/detalhe/<int:id>/confirma/username/', ConfirmaUsernameView.as_view(), name='confirma_username'),
    path('usuario/pessoa/<int:id_pessoa_sig>/existe/', UserExisteView.as_view(), name='conta_existe'),
    path('usuario/novo/confirmacao/', ConfirmacaoNovoUserView.as_view(), name='confirmacao_novo_user'),
    path('usuario/novo/pessoa/<int:id_pessoa_sig>/', UsuarioNovoView.as_view(), name="user_novo"),
]