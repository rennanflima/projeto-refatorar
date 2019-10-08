#MODELS REGISTRADOS NO AMBIENTE DE CONFIGURAÇÃO (ADMIN DO DJANGO)
from django.contrib import admin
from django.http import HttpResponseRedirect
from django import forms
from django.contrib import messages
from manhana.core.models.parametro import *
from manhana.core.models.processo import *

#ACTION PARA ATIVAR REGISTROS SELECIONADOS
def activate_register(modeladmin, request, queryset):
    queryset.update(is_ativo=True)
activate_register.short_description = 'Ativar registro(s)'

#ACTION PARA DESATIVAR REGISTROS SELECIONADOS
def deactivate_register(modeladmin, request, queryset):
    queryset.update(is_ativo=False)
deactivate_register.short_description = 'Desativar registro(s)'


#MODEL DE CONFIGURAÇÃO DA ÁREA DE CONTRATAÇÃO DO DOCENTE
@admin.register(AreaContratacao)
class AreaContratacaoAdmin(admin.ModelAdmin):
    search_fields = ['nome',]
    list_filter = ['is_ativo',]
    list_display = ['nome', 'is_ativo',]
    actions = [activate_register, deactivate_register]


@admin.register(CategoriaAtividade)
class CategoriaAtividadeAdmin(admin.ModelAdmin):
    search_fields = ['nome',]
    list_filter = ['is_ativo',]
    list_display = ['nome', 'label', 'categoria_pai', 'slug', 'is_ativo',]
    prepopulated_fields = {'slug': ('nome',)}
    actions = [activate_register, deactivate_register]


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    search_fields = ['descricao', 'categoria_atividade__nome']
    list_filter = ('is_ativo', 'categoria_atividade',)
    list_display = ['descricao', 'categoriaatividade', 'ch_minima', 'ch_maxima', 'validacao_ch_por', 'is_ativo']
    actions = [activate_register, deactivate_register]


@admin.register(CategoriaProcesso)
class CategoriaProcessoAdmin(admin.ModelAdmin):
    search_fields = ['nome', 'descricao',]
    list_filter = ['is_ativo',]
    list_display = ['nome', 'descricao', 'categoria_pai','is_ativo']
    actions = [activate_register, deactivate_register]


@admin.register(SituacaoProcesso)
class SituacaoProcessoAdmin(admin.ModelAdmin):
    search_fields = ['nome', 'descricao',]
    list_filter = ['is_ativo',]
    list_display = ['nome', 'descricao', 'is_ativo']
    prepopulated_fields = {'slug': ('nome',)}
    actions = [activate_register, deactivate_register]


@admin.register(ArgumentoCategoria)
class ArgumentoCategoriaAdmin(admin.ModelAdmin):
    search_fields = ['campo', 'categoria_atividade',]
    list_filter = ['is_ativo',]
    list_display = ['campo', 'tipo_dado', 'categorias', 'is_ativo']
    prepopulated_fields = {'slug': ('campo',)}
    actions = [activate_register, deactivate_register]


@admin.register(EstruturaOrganizacional)
class EstruturaOrganizacionalAdmin(admin.ModelAdmin):
    search_fields = ['nome', 'sigla']
    list_filter = ['tipo_estrutura', 'is_ativo']
    list_display = ['nome', 'sigla', 'tipo_estrutura', 'estrutura_pai', 'is_ativo']
    actions = [activate_register, deactivate_register]


@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    search_fields = ['nome',]
    list_filter = ['is_ativo',]
    list_display = ['nome', 'tipo_dado', 'valor', 'is_ativo']
    actions = [activate_register, deactivate_register]


@admin.register(CHSemanalCategoriaAtividade)
class CHSemanalCategoriaAtividadeAdmin(admin.ModelAdmin):
    search_fields = ['id',]
    list_display = ['id', 'categorias', 'ch_minima', 'ch_maxima', 'grupos']


class UnidadeFluxoProcessoTabularInline(admin.TabularInline):
    model = UnidadeFluxoProcesso
    extra = 1


@admin.register(FluxoProcesso)
class FluxoProcessoAdmin(admin.ModelAdmin):
    search_fields = ['nome', 'tipo_processo']
    list_filter = ['is_ativo', 'tipo_processo', 'tipo_fluxo',]
    list_display = ['nome', 'tipo_fluxo', 'unidade', 'tipo_processo', 'is_ativo']
    actions = [activate_register, deactivate_register]
    inlines = [UnidadeFluxoProcessoTabularInline]

    
@admin.register(VinculoServidorUnidade)
class VinculoServidorUnidadeAdmin(admin.ModelAdmin):
    search_fields = ['unidade','servidor',]
    list_filter = ['is_ativo', 'unidade',]
    list_display = ['unidade','servidor', 'is_ativo',]
    actions = [activate_register, deactivate_register]


@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    search_fields = ['numero_processo', 'tipo_processo']
    list_display = ['numero_processo', 'ano', 'semestre', 'tipo_processo', 'interessado', 'unidade_interessada', 'situacao', 'ultima_modificacao_em',]
    fieldsets = (
        (None, {
            'fields': ('numero_processo', 'ano', 'semestre', 'assunto', 'interessado', 'unidade_interessada', 'quantidade_leitura', 'tipo_processo', 'situacao', 'processo_pai')
        }),
        ('Histórico', {
            'fields': ('criado_em', 'criado_por', 'ultima_modificacao_em', 'modificado_por'),
        })
    )
    readonly_fields = ('criado_em', 'ultima_modificacao_em',)


@admin.register(Tramite)
class TramiteAdmin(admin.ModelAdmin):
    search_fields = ['processo', 'servidor_origem']
    list_display = ['processo', 'servidor_origem', 'unidade_origem', 'servidor_destino', 'unidade_destino']


@admin.register(DocumentoProcesso)
class DocumentoProcessoAdmin(admin.ModelAdmin):
    search_fields = ['processo', 'tipo_documento']
    list_display = ['processo', 'titulo', 'tipo_documento']
    fieldsets = (
        (None, {
            'fields': ('processo', 'tipo_documento', 'titulo', 'texto', 'arquivo')
        }),
        ('Histórico', {
            'fields': ('criado_em', 'criado_por', 'ultima_modificacao_em', 'modificado_por'),
        })
    )
    readonly_fields = ('criado_em', 'ultima_modificacao_em',)