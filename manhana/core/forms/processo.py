from django import forms
from django.utils.translation import gettext_lazy as _
from manhana.core.models.processo import *
from django.core.exceptions import NON_FIELD_ERRORS
from django.forms import formset_factory
from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget



class ProcessoForm(forms.ModelForm):
    class Meta:
        model = Processo
        fields = ['ano', 'semestre', 'tipo_processo',]
        error_messages  =  { 
            'unique_together' :  " %(model_name)s %(field_labels)s não são exclusivos." , 
        }

    def __init__(self, *args, **kwargs):
        super(ProcessoForm, self).__init__(*args, **kwargs)


class RegistroAtividadeForm(forms.ModelForm):
    processo = forms.ModelChoiceField(queryset=Processo.objects.all(), widget=forms.HiddenInput())
    ch_semanal = forms.DecimalField(label='Carga horária semanal', max_digits=10, decimal_places=2, localize=True, required=True)

    class Meta:
        model = RegistroAtividade
        exclude = ['situacao', 'justificativa', 'avaliador', 'data_avaliacao',]
    
    def __init__(self, *args, **kwargs):
        if 'atividade' in kwargs:
            self.base_fields['atividade'].queryset = kwargs.pop('atividade')
        
        super(RegistroAtividadeForm, self).__init__(*args, **kwargs)
        
        self.fields['is_editavel'].widget = forms.HiddenInput()
        self.fields['is_obrigatorio'].widget = forms.HiddenInput()
        self.fields['atividade'].widget.attrs['class'] = 'js-atividade'
        
        self.fields['ch_semanal'].localize = True
        self.fields['ch_semanal'].widget.is_localized = True
        self.fields['ch_semanal'].widget.attrs['class'] = 'js-money2'

        if self.instance.pk:
            self.fields['atividade'].widget.attrs['readonly'] = True

        if 'initial' in kwargs:
            if 'atividade' in kwargs['initial']:
                if kwargs['initial']['atividade'].descricao == 'Preparação didática':
                    self.fields['ch_semanal'].widget.attrs['readonly'] = True
                    self.fields['descricao'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super().clean()
        ch_semanal = cleaned_data.get("ch_semanal")
        atividade = cleaned_data.get("atividade")
        
        if ch_semanal and ch_semanal <= 0: 
            self.add_error('ch_semanal', 'A carga horária semanal da atividade não pode ser menor ou igual a ZERO.')

        if atividade and atividade.validacao_ch_por == atividade.RESOLUCAO:
            if ch_semanal < atividade.ch_minima or ch_semanal > atividade.ch_maxima:
                self.add_error('ch_semanal', f"Carga horária semanal não deve estar entre {atividade.ch_minima} e {atividade.ch_maxima}.")


    def clean_atividade(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            return instance.atividade
        else:
            return self.cleaned_data['atividade']

RegistroAtividadeFormSet = formset_factory(RegistroAtividadeForm, extra=0)


class InformacoesRegistroForm(forms.Form):
    pass


class ProjetoForm(forms.ModelForm):
    processo = forms.ModelChoiceField(queryset=Processo.objects.all(), widget=forms.HiddenInput())
    ch_semanal = forms.DecimalField(label='Carga horária semanal', max_digits=10, decimal_places=2, localize=True)
    titulo = forms.CharField()
    numero_participantes = forms.IntegerField()
    data_inicio = forms.DateField(help_text='Ex: 15/11/2002', input_formats=["%d/%m/%Y",], widget=forms.DateInput(format='%d/%m/%Y'))
    data_termino = forms.DateField(help_text='Ex: 15/11/2002', input_formats=["%d/%m/%Y",], widget=forms.DateInput(format='%d/%m/%Y'))
    resultados = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = RegistroAtividade
        exclude = ['descricao', 'situacao', 'justificativa', 'avaliador', 'data_avaliacao',]
    
    def __init__(self, *args, **kwargs):
        if 'atividade' in kwargs:
            self.base_fields['atividade'].queryset = kwargs.pop('atividade')
        
        super(ProjetoForm, self).__init__(*args, **kwargs)

        self.fields['data_inicio'].widget.attrs['class'] = 'js-date'
        self.fields['data_termino'].widget.attrs['class'] = 'js-date'

        
        self.fields['ch_semanal'].localize = True
        self.fields['ch_semanal'].widget.is_localized = True
        self.fields['ch_semanal'].widget.attrs['class'] = 'js-money2'
        
        self.fields['is_editavel'].widget = forms.HiddenInput()
        self.fields['is_obrigatorio'].widget = forms.HiddenInput()

        if self.instance and self.instance.pk:
            self.fields['atividade'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get("data_inicio")
        data_termino = cleaned_data.get("data_termino")
        ch_semanal = cleaned_data.get("ch_semanal")
        atividade = cleaned_data.get("atividade")

        if ch_semanal <= 0: 
            self.add_error('ch_semanal', 'A carga horária semanal do projeto não pode ser menor ou igual a ZERO.')

        if data_inicio > data_termino:
            self.add_error('data_inicio', 'A data de início do projeto não pode ser maior que a data de termíno')
            self.add_error('data_termino', 'A data de termíno do projeto deve ser maior que a data de início')
        
        elif data_inicio == data_termino:
            self.add_error('data_inicio', 'A data de início do projeto não pode ser igual que a data de termíno')
            self.add_error('data_termino', 'A data de termíno do projeto deve ser maior que a data de início')

        if atividade and atividade.validacao_ch_por == atividade.RESOLUCAO:
            if ch_semanal < atividade.ch_minima or ch_semanal > atividade.ch_maxima:
                self.add_error('ch_semanal', f"Carga horária semanal não deve estar entre {atividade.ch_minima} e {atividade.ch_maxima}.")

    def clean_atividade(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            return instance.atividade
        else:
            return self.cleaned_data['atividade']



class DocumentoForm(forms.ModelForm):

    class Meta:
       model = DocumentoProcesso
       fields = ['tipo_documento', 'titulo', 'texto', 'arquivo',]
       widgets = {
            'texto': CKEditorWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(DocumentoForm, self).__init__(*args, **kwargs)

        # self.fields['tipo_documento'].widget = forms.HiddenInput()
        # self.fields['tipo_documento'].initial = DocumentoProcesso.DESPACHO

class AvaliacaoAtividadeForm(forms.ModelForm):
    is_valida = forms.BooleanField(label='Atividade válida?', required=False)
    
    class Meta:
        model = RegistroAtividade
        fields = ['justificativa',]
        widgets = {
            'justificativa': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_valida'].widget.attrs['class'] = 'custom-control-input'

        if self.instance and self.instance.situacao == RegistroAtividade.VALIDA:
            self.fields['is_valida'].initial = True
        else:
            self.fields['is_valida'].initial = False

    def clean(self):
        cleaned_data = super().clean()
        is_valida = cleaned_data.get("is_valida")
        justificativa = cleaned_data.get("justificativa")

        if not is_valida:
            if not justificativa:
                self.add_error('justificativa', 'O campo é obrigatório.')
            if not justificativa.strip():
                self.add_error('justificativa', 'O campo contem somente espaços.')
            
            