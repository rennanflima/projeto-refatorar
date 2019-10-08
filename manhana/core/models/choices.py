STATUS_CHOICE = (
    (True, 'Ativo'),
    (False, 'Inativo')
)

TIPO_DADO = (
    ('TEXTO', 'Texto'),
    ('INTEIRO', 'Inteiro'),
    ('DECIMAL', 'Decimal'),
    ('BOOLEAN', 'Boolean'),
    ('DATA', 'Data'),
    ('HORA', 'Hora'),
    ('DATA_HORA', 'Data/Hora'),
    ('ARQUIVO', 'Arquivo'),
)

TIPO_ESTRUTURA = (
    (1, 'Raiz'),
    (2, 'Campus'),
    (3, 'Comissão'),
    (4, 'Setor'),
    (5, 'Polo'),
    (6, 'Pró-Reitoria'),
)

VALIDACAO_POR_CHOICES = (
    ('RESOLUCAO', 'Conforme resolução'),
    ('CURSO', 'Por Curso'),
    ('TURMA', 'Por turma'),
    ('DISCIPLINA', 'Por disciplina'),
    ('PROJETO', 'Por Projeto'),
    ('QUANTIDADE', 'Por quantidade informada no formulário'),
)

TIPO_NIVEL_RESPONSABILIDADE = (
    ('C', 'Chefia/Diretoria'),
    ('V', 'Vice-Chefia/Vice-Diretoria'),
    ('S', 'Secretaria'),
    ('A', 'Supervisor/Diretor Acadêmico'),
)

TIPO_VINCULO = (
    ('P', 'Presidente'),
    ('V', 'Vice-Presidente'),
    ('S', 'Secretario'),
    ('M', 'Membro'),
)

TIPO_FLUXO_PROCESSO = (
    ('P', 'Principal'),
    ('R', 'Recurso'),
    ('C', 'Consulta'),
)

TIPO_STATUS_REGISTRO = (
    ('AGUARDANDO_VALIDACAO', 'Aguardando validação'),
    ('VALIDA','Válida'),
    ('INVALIDA','Inválida'),
    ('EDITADA','Editada'),
)

TIPO_DESPACHO = (
    ('SOLICITACAO', 'Solicitação'),
    ('PARECER', 'Parecer'),
    ('DESPACHO', 'Despacho'),
)

TIPO_DOCUMENTO = (
    ('SOLICITACAO', 'Solicitação'),
    ('PARECER', 'Parecer'),
    ('DESPACHO', 'Despacho'),
)