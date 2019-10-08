from django import forms
from .models import *
from brazilnum.cpf import validate_cpf
from captcha.fields import ReCaptchaField
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User 

# Create your forms here.

class BuscaPessoaForm(forms.Form):
    cpf = forms.CharField(help_text='Ex: 81090784864', label='CPF', max_length=11)
    dataNasc = forms.DateField(help_text='Ex: 15/11/2002', label='Data de Nascimento', input_formats=["%d/%m/%Y",], widget=forms.DateInput(format='%d/%m/%Y'))
    # if not settings.DEBUG:
    #captcha = ReCaptchaField()
    
    def __init__(self, *args, **kwargs):
        super(BuscaPessoaForm, self).__init__(*args, **kwargs)
        self.fields['cpf'].widget.attrs.update({'class' : 'numero'})
        

    def clean(self):
        cleaned_data = super(BuscaPessoaForm, self).clean()
        cpf = self.cleaned_data.get('cpf')
        dataNasc = self.cleaned_data.get('dataNasc')
        if not validate_cpf(cpf):
            self.add_error('cpf', 'CPF inválido.')


class SignUpForm(UserCreationForm):
    # email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )
    
    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        if kwargs.get('initial', None):
            if kwargs['initial']['email']:
                self.fields['email'].widget.attrs['readonly'] = True



