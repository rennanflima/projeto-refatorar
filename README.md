# projeto-refatorar

---

## Instalação

Para executar este projeto em sua máquina local você deve:

### Clonar

- Clone este repositório para a sua máquina local usando `https://github.com/rennanflima/projeto-refatorar.git`

### Setup

É preciso instalar as dependecias do pygraphviz primeiro:

> Atualize e depois instale os pacotes

```sh
$ sudo apt-get update
$ sudo apt-get install python-dev graphviz libgraphviz-dev pkg-config
```

ou 

```sh
brew install graphviz
```

Crie o ambiente virtual e instale as dependências:

```sh
$ cd manhanah
$ python3 -m venv env
$ source env/bin/activate
```

Instale as dependências

```sh
$ pip install -r requirements.txt
```

Criar banco de dados (Tenha certeza que esteja no mesmo diretório que manage.py)

```
$ python manage.py makemigrations
$ python manage.py migrate
```

Popular banco de dados com informações iniciais
```
$ python manage.py loaddata authentication
$ python manage.py loaddata core
```

Execute o servidor localmente:
```
$ python manage.py runserver
Performing system checks...

System check identified no issues (0 silenced).
June 25, 2019 - 17:46:14
Django version 2.1.7, using settings 'manhanah.settings.development'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```
---

## Usuários

* tae.teste
* docente.teste
* docente2.teste

_**Obs.:** Para estes usuários usar a senha "teste"._




