# Sistema do Evento Acadêmico (Caso 2)

Sistema completo (banco de dados + interface web) para o trabalho de
Evento Acadêmico. Não depende de instalar nada além do Python — usa
apenas `sqlite3` e `http.server`, que já vêm com o Python.

## Como rodar

1. Precisa ter Python 3 instalado (`python3 --version`).
2. Abra um terminal na pasta do projeto e rode:
   ```
   python3 app.py
   ```
3. Abra o navegador em: **http://localhost:8000**

Na primeira execução ele cria sozinho o arquivo `evento.db` (SQLite) já
com as tabelas do `schema.sql`. Para zerar o banco, feche o servidor e
apague o arquivo `evento.db`; ele é recriado na próxima execução.

Para rodar num servidor (VPS, por exemplo), basta copiar a pasta inteira
e rodar o mesmo comando — se quiser deixá-lo rodando em segundo plano,
use algo como `nohup python3 app.py &` ou configure um serviço systemd.
Se for acessar de outro computador, troque `localhost` pelo IP/domínio
do servidor (o servidor já escuta em `0.0.0.0`, então isso funciona sem
mudar o código — só ajuste liberação de porta/firewall se necessário).

## Estrutura de arquivos

```
evento_academico/
├── app.py            → backend (servidor HTTP + regras de acesso ao banco)
├── schema.sql         → criação das tabelas (executado automaticamente)
├── evento.db           → banco SQLite (criado ao rodar, não precisa mexer)
└── static/
    ├── index.html      → página única (abas: Cadastro / Consulta / Relatórios)
    ├── style.css
    └── app.js          → toda a lógica de front-end (chama a API via fetch)
```

## Correção dos dois pontos problemáticos do enunciado

O modelo original tinha, dentro da entidade `atividades`, os atributos
`responsáveis pela organização` e `equipe de apoio` como listas dentro
da própria atividade. Isso é um atributo **multivalorado**, o que
viola a 1FN, além de representar na verdade um relacionamento **N:N**
(uma atividade pode ter várias pessoas organizando, e uma mesma pessoa
pode organizar várias atividades — o mesmo vale para o apoio).

A correção foi criar duas tabelas associativas:

- `atividade_organizadores (id_atividade, cpf)`
- `atividade_apoio (id_atividade, cpf)`

Cada uma com chave primária composta, referenciando `atividades` e
`equipe_organizadora`/`equipe_apoio`. Isso resolve a 1FN (nada de
listas dentro de uma célula) e mantém 2FN/3FN porque não sobra nenhum
atributo não-chave dependendo de apenas parte da chave.

Demais ajustes de normalização feitos ao longo do modelo:
- `instituicoes` e `tipos_vinculo` viraram tabelas próprias (o enunciado
  já sugeria isso com o `(Ɓ)` — chave estrangeira), evitando repetir o
  nome da instituição/vínculo por extenso em cada pessoa.
- `inscritos_alocados` referencia `quartos_hotel` pela chave composta
  (nome do hotel, quarto), exatamente como pedido no enunciado.

## O que a interface cobre

**Cadastro (inserção):** pessoa, inscrição, equipe organizadora, equipe
de apoio, atividade (com seleção múltipla de organizadores/apoio),
ministrante, presença em atividade, hotel, quarto e alocação.

**Consulta:** pessoas/inscritos (com busca por CPF/nome), atividades
(com busca por nome, mostrando vagas/organizadores/apoio/ministrantes),
alocação em hotéis.

**Relatórios:** atividades×inscritos×excedentes, atividades×ministrantes
×equipe de apoio, presentes confirmados, certificados por atividade/
inscrito, hotel×quartos×pessoas×instituição.

## Observações para o trabalho

- O arquivo `schema.sql` já é, em si, a entrega da modelagem lógica
  (script de criação com PKs, FKs e a correção da normalização). Vale
  a pena desenhar o Modelo Entidade-Relacionamento (MER/DER) à parte
  num editor de diagramas (draw.io, por exemplo) espelhando essas
  mesmas tabelas — o professor provavelmente quer ver o diagrama, não
  só o SQL.
- O backend é minimalista de propósito (sem framework) para não
  depender de `pip install` nem de internet no servidor onde você for
  rodar. Se seu professor não tiver problema com bibliotecas externas,
  dá para trocar por Flask depois sem mudar o banco.
- Os dados de teste que usei para validar o sistema (curl) não estão
  no banco entregue — ele começa vazio.
