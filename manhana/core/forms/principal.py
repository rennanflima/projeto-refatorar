from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from manhana.authentication.models import *
from manhana.authentication.services import Cadu
from manhana.core.models.parametro import VinculoServidorUnidade, EstruturaOrganizacional
from django.db.models import Q

class DocenteForm(forms.ModelForm):
    area_contratacao = forms.ModelChoiceField(queryset=AreaContratacao.objects.filter(is_ativo=True))
    class Meta:
        model = DocenteProfile
        fields = ('grupo', 'lattes', 'area_contratacao',)

    def __init__(self, *args, **kwargs):
        if 'grupo' in kwargs:
            self.base_fields['grupo'].queryset = kwargs.pop('grupo')

        super(DocenteForm, self).__init__(*args, **kwargs)
        

class ConfirmPasswordForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label="Confirmação de senha")

    class Meta:
        model = User
        fields = ('confirm_password', )

    def clean(self):
        cleaned_data = super(ConfirmPasswordForm, self).clean()
        confirm_password = cleaned_data.get('confirm_password')
        if self.instance.password:
            if not check_password(confirm_password, self.instance.password):
                self.add_error('confirm_password', 'A senha informada não corresponde.')            
        else:
            cadu = Cadu()
            user_cadu = cadu.buscar_por_username(self.instance.username)
            if not check_password(confirm_password, user_cadu['password']):
                self.add_error('confirm_password', 'A senha informada não corresponde.')


class VinculoServidorUnidadeForm(forms.ModelForm):
    unidade = forms.ModelChoiceField(queryset=EstruturaOrganizacional.objects.all(), widget=forms.HiddenInput())
    data_inicio = forms.DateField(help_text='Ex: 15/11/2002', input_formats=["%d/%m/%Y",], widget=forms.DateInput(format='%d/%m/%Y'))

    class Meta:
        model = VinculoServidorUnidade
        exclude = ('data_termino', 'is_ativo',)


    def __init__(self, *args, **kwargs):        
        super(VinculoServidorUnidadeForm, self).__init__(*args, **kwargs)

        self.fields['data_inicio'].widget.attrs['class'] = 'js-date'

        if self.instance and self.instance.pk:
            self.fields['servidor'].widget.attrs['readonly'] = True
            self.fields['data_inicio'].widget.attrs['readonly'] = True
            
