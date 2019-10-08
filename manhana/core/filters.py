import django_filters
from manhana.core.models.processo import Processo
from manhana.authentication.models import DocenteProfile

class ProcessoFilter(django_filters.FilterSet):
    interessado = django_filters.ModelChoiceFilter(label='Interessado', field_name='interessado', queryset=DocenteProfile.objects.all())
    class Meta:
        model = Processo
        fields = ['numero_processo', 'ano', 'semestre', 'tipo_processo', 'interessado', 'situacao']

    def __init__(self, *args, **kwargs):
        super(ProcessoFilter, self).__init__(*args, **kwargs)
        # at sturtup user doen't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()