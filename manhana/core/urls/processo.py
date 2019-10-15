from django.urls import include, path, re_path

from manhana.core.views import consulta, processo

urlpatterns = [
    path('processo/', processo.CaixaEntradaView.as_view(), name="caixa-entrada"),
    path('processo/novo/', processo.ProcessoNovoView.as_view(), name="processo-novo"),
    path('processo/<int:pk>/detalhe/', processo.ProcessoDetalheView.as_view(), name="processo-detalhe"),
    path('processo/<int:pk>/movimentar/', processo.MovimentaProcessoView.as_view(), name="processo-movimentar"),
    path('processo/<int:pk>/editar/', processo.EditarProcessoView.as_view(), name="processo-editar"),
    path('processo/excluir/', processo.excluir_processo, name="processo-deletar"),
    path('processo/<int:pk>/verifica/<slug:slug>/importacao/', processo.VerificarCategoriaAtividadeImportacaoView.as_view(), name="verificar_tipo_atividade_importar"),
    path('processo/<int:pk>/verifica/<slug:slug>/novo/', processo.VerificarCategoriaAtividadeNovoView.as_view(), name="verificar_tipo_atividade_novo"),
    path('processo/<int:pk>/importar/atividades/ensino/', processo.importar_atividade_ensino, name="importar_atividade_ensino"),
    path('processo/<int:pk>/importar/atividades/gestao/', processo.importar_atividade_gestao, name="importar_atividade_gestao"),
    path('processo/<int:pk>/importar/disciplinas/', processo.importar_disciplinas, name='importar_disciplinas'),
    path('processo/<int:pk>/<slug:slug>/atividade/novo/', processo.RegistroAtividadeNovoView.as_view(), name="atividade-novo"),
    path('processo/atividade/<int:pk>/editar/', processo.EditarRegistroAtividadeView.as_view(), name="atividade-editar"),
    path('processo/atividade/excluir/', processo.excluir_atividade, name="atividade-excluir"),

    # path('processo/<int:pk>/<slug:slug>/verficar/obrigatorias', processo.VerificarAtividadeObrigatoriasView.as_view(), name="verificar-atividades-obrigatorias"),
    path('processo/<int:pk>/<slug:slug>/verficar/obrigatorias', processo.verifica_atividades_obrigatorias_view, name="verificar-atividades-obrigatorias"),
    
    path('processo/<int:pk>/<slug:slug>/projeto/novo/', processo.ProjetoNovoView.as_view(), name="projeto-novo"),
    path('processo/projeto/<int:pk>/editar/', processo.EditarProjetoView.as_view(), name="projeto-editar"),

    path('processo/atividade/busca-observacao/<int:idatividade>/', processo.busca_observacao, name="busca-observacao"),

    path('processo/<int:pk>/assinar/', processo.assinar_envio_processo, name='assinar-envio-processo'),

    path('processo/comissao/receber/', processo.receber_processo, name='receber-processo'), 

    path('busca/avancada/processo/', processo.busca_avancada_processo, name="buscar-avancada-processo"),

    path('processo/<int:id_processo>/atividade/<int:pk>/avaliar/', processo.avaliar_atividade, name="avaliar-atividade"),


    # path('processo/<int:pk>/movimentar/despacho/', processo.criar_despacho, name="processo-despacho"),



    # Documento

    path('processo/<int:pk>/documento/novo/', processo.criar_documento, name="documento-novo"),
    path('processo/<int:id_processo>/documento/<int:pk>/editar/', processo.editar_documento, name="documento-editar"),
    path('processo/documento/excluir/', processo.excluir_documento, name="documento-excluir"),
    path('processo/documento/<int:pk>/assinar/', processo.assinar_documento, name='documento-assinar'),


    # Movimentar
    path('processo/<int:pk>/encaminhar/', processo.encaminhar_processo, name="processo-encaminhar"),


    # Consulta
    path('processo/<int:pk>/realizar/consulta/novo/', consulta.realizar_consulta_novo, name="consulta-novo"),
    path('processo/consulta/<int:pk>/movimentar/', consulta.consulta_detalhe, name="consulta-movimentar"),


    path('ajax/processo/<int:pk>/resumo/<editando>/', processo.resumo_processo, name='ajax-summary-process'),
    path('ajax/processo/<int:pk>/assinatura/form/', processo.form_assinatura, name='ajax-form-assinatura'),
    path('ajax/atividade/<int:pk>/detalhe/', processo.detalha_atividade, name='ajax-atividade-detail'),
    path('ajax/processo/<int:pk>/editar/tipo_atividade/<int:id_tipo_atividade>/carregar/lista/', processo.carregar_lista_atividades_editando, name='ajax-atividade-list-editar'),
    path('ajax/processo/<int:pk>/detalhe/tipo_atividade/<int:id_tipo_atividade>/carregar/lista/', processo.carregar_lista_atividades_detalhe, name='ajax-atividade-list-detalhe'),

    path('ajax/processo/<int:pk>/movimentacao/tipo_atividade/<int:id_tipo_atividade>/carregar/lista/', processo.carregar_lista_atividades_movimentacao, name='ajax-atividade-list-mov'),

    path('ajax/processo/<int:pk>/movimentacao/lista/', processo.carregar_lista_movimentacao, name='ajax-movimentacao-list'),
    path('ajax/processo/<int:pk>/documento/lista/', processo.carregar_lista_documentos, name='ajax-documento-list'),
    path('ajax/processo/<int:pk>/movimentacao/documento/lista/', processo.carregar_lista_documentos_movimentacao, name='ajax-documento-list-mov'),
    path('ajax/documento/<int:pk>/detalhe/', processo.detalha_documento, name='ajax-documento-detail'),

    path('ajax/tramite/<int:pk>/detalhe/', processo.detalha_tramite, name='ajax-tramite-detail'),
    path('ajax/tramite/<int:pk>/detalhe/movimentacao/', processo.detalha_tramite_movimentacao, name='ajax-tramite-detail-mov'),
    path('ajax/atividade/<int:pk>/detalhe/movimentacao/', processo.detalha_atividade_movimentacao, name='ajax-atividade-detail-mov'),

    path('ajax/processo/<int:pk>/parecer/novo/texto', processo.carrega_texto_parecer_novo, name='ajax-texto-parecer-novo'),

    path('ajax/processo/<int:pk>/processos/anexos/lista/', processo.carregar_lista_processos_anexos, name='ajax-processos-anexos-list'),
    path('ajax/processo/<int:pk>/movimentacao/processos/anexos/lista/', processo.carregar_lista_processos_anexos_movimentacao, name='ajax-processos-anexos-list-mov'),
]
