# Entrega — licença Pro com ativação por PC

forge-key: `sratlas:dispatch:4`  
agente: Cursor  
ramo: `claude/sratlas-license-activation`  
hora UTC do registo: 2026-11-15T16:20:46Z

## VERIFIED

Ficheiros alterados, e só estes:

- `backend/license.py` — `POST /v1/licenses/activate` com `instance_name` (`atlas-` + 32 hex de SHA-256); `validate` envia `license_key` e `instance_id`; coluna `instance_id` com `ALTER TABLE ... ADD COLUMN` só se faltar; loja e produto; `deactivate()`
- `backend/server.py` — `POST /api/license/deactivate`, com `_license_response_is_safe`, 503 em falha de rede e 422 em chave vazia na ativação, como a rota que já existia
- `backend/tests/test_license.py`
- `frontend/src/lib/api.js` — `deactivateLicense`
- `frontend/src/pages/Settings.jsx` — botão «Deactivate on this PC» (`data-testid="license-deactivate"`), visível quando há chave guardada
- `frontend/src/lib/api.test.js`
- `frontend/src/components/remainingVisual.test.js`
- `docs/entregas/licenca-ativacao/RECECAO.md`
- `docs/entregas/licenca-ativacao/ENTREGA.md`

Comportamento observado nos testes que correram:

- Ativar chama `https://api.lemonsqueezy.com/v1/licenses/activate` com `license_key` e `instance_name` a começar por `atlas-`. O nome não contém o material cru. O `instance.id` fica na tabela.
- A mesma chave com o mesmo `instance_id` não volta a chamar activate. A segunda chamada é validate com esse `instance_id`.
- A revalidação, passadas mais de 24 h, envia `license_key` e `instance_id`. No mesmo dia continua a haver uma só chamada.
- Limite de ativações: Free, sem Pro, com a frase «This key is already active on another PC. Deactivate it there or contact support.» A linha de `mt5_overrides` que existia no mesmo ficheiro mantém-se. A chave não aparece na resposta, no log nem em `last_error`. No dia seguinte essa recusa não é tratada como validate sem instância.
- Com `LEMON_STORE_ID=10` e `LEMON_PRODUCT_ID=20`, loja 99 ou produto 77 não dá Pro. A loja errada, depois de a Lemon aceitar a ativação, é seguida de `POST /v1/licenses/deactivate` dessa instância, e o `instance_id` local fica vazio. Loja 10 e produto 20 dão Pro.
- Com as duas variáveis ausentes (0), uma resposta válida de outra loja e outro produto continua Pro. O aviso de configuração aparece uma vez. O texto atual é `LEMON_STORE_ID and LEMON_PRODUCT_ID are 0; store and product check is skipped.`
- Falha de rede ou HTTP 503, dois dias depois de um Pro válido, mantém Pro (`cached`). Oito dias depois, volta a Free. Uma resposta `disabled` ao fim de dois dias tira o Pro na hora, sem margem, e o limite de 1 conta volta a ser aplicado.
- Instância desconhecida na revalidação: Free, sem nova ativação automática. O `instance_id` local é esquecido. Um `activate` seguinte volta a registar o PC.
- Uma linha antiga com chave Pro e sem `instance_id` é registada na revalidação (`/licenses/activate`) e a chave gravada não muda.
- `ALTER TABLE` acrescenta `instance_id` a uma `atlas_license` antiga e não apaga a linha nem a tabela `mt5_overrides`. A segunda chamada não duplica a coluna.
- `deactivate()` chama `/licenses/deactivate` com `license_key` e `instance_id`, apaga a chave e a instância locais e volta a Free. A linha de conta no mesmo SQLite mantém-se. Falha de rede não tira o Pro.
- `POST /api/license/deactivate` sem chave: 200, Free. Com Pro e rede em baixo: 503, Pro mantém-se, e a chave não vai na resposta. Com sucesso: 200, Free, e `GET /api/license` continua Free sem a chave.
- O identificador do PC, com o material substituído por `SECRET-GUID`, é `atlas-` mais os primeiros 32 hex de SHA-256 desse texto, estável entre duas leituras.

Comandos e códigos de saída:

```text
cd backend && python3 -m pytest tests/test_license.py -q --tb=line
```

exit code 0 — 40 passed, 12 warnings, 0.79s. Os 12 warnings são `DeprecationWarning` / `PendingDeprecationWarning` de `on_event` no arranque do FastAPI e do parser de formulários do Starlette. Nenhum teste falhou. Esta alteração não editou esses `on_event`.

```text
cd frontend && CI=true yarn test --watchAll=false --watchman=false --testPathPattern='api.test|remainingVisual'
```

exit code 0 — 2 suites, 13 passed, 0.49s. O Jest lê o fonte; não monta Settings.

```text
python3 -m pytest installer/tests/test_payload_hygiene.py -q --tb=line
```

exit code 0 — 4 passed, 0.04s. O ficheiro de teste não foi alterado. Confirma que o painel de licença continua no fonte que o instalador copia, e que não entrou nenhum dos segredos que esse teste procura.

`AGENTS.md` e `.cursor/rules/` não foram alterados. A Fase 3 não foi ligada. Não houve merge. `httpx` já estava no módulo; não entrou dependência nova.

O texto do botão no fonte é «Deactivate on this PC». Em `frontend/src/index.css`, `.btn` tem `text-transform: uppercase`, a mesma regra do botão ACTIVATE. O CSS não foi alterado.

## INFERENCE

- A verificação da loja e do produto compara os dois ids só quando ambos são maiores que 0. Se só um está definido, a resposta não dá Pro. Isso ficou verificado na correção abaixo.
- Uma instalação que já tinha a chave Pro gravada, sem `instance_id`, regista este PC na próxima revalidação (mais de um dia desde `last_verified_at`). Sem isso o limite de ativações não passava a valer para essa chave. Uma recusa já gravada, sem instância, não é repetida sozinha.
- Se a Lemon aceita a ativação e a loja ou o produto não são os nossos, o Atlas tenta libertar essa instância. Se essa libertação falhar por rede, o Pro fica negado na mesma e o lugar remoto pode continuar ocupado.
- A margem de 7 dias fica só quando a última resposta bem sucedida continua `valid` e a chamada nova é rede, timeout ou HTTP ≥ 500. Qualquer resposta confirmada com `valid` falso ignora a margem.
- `deactivate()` com sucesso, ou com instância que a Lemon já não conhece, apaga a chave local para a revalidação não a voltar a ativar. Não mexe nas tabelas de conta.

## NOT VERIFIED

- Ativação, validação e desativação reais na Lemon Squeezy. Não há produto nem chave de teste.
- `MachineGuid` num Windows real. Aqui o material foi o de teste, ou `uuid.getnode()` no Linux.
- O botão no browser. Carregar em desativar chamaria a Lemon ao vivo.
- Suite pytest completa e suite Jest completa.
- Instalador Windows e bridge.
- Revisão Codex do novo HEAD e o «sim» do Fundador. Não fazer merge sem isso.

## Correção Codex em `83e6bb7` — 2026-11-15T16:33:09Z

Os quatro achados eram válidos. O desenho com `prev_license_key` / `prev_instance_id` desta secção foi retirado na simplificação de `c5ecf02`, mais abaixo. As colunas ficam na tabela, sem uso.

Esta correção mexeu só em `backend/license.py`, `backend/tests/test_license.py` e neste ficheiro.

### VERIFIED

- **P1.** A comparação loja/produto é saltada só quando `LEMON_STORE_ID` e `LEMON_PRODUCT_ID` são os dois 0. Com `LEMON_STORE_ID=10` e `LEMON_PRODUCT_ID` ausente, uma chave da loja 99 não fica Pro. O aviso `partial license configuration is a mismatch and Pro is not granted` sai uma vez. A segunda ativação não repete o aviso.
- **P2, instância desconhecida.** A recusa é gravada antes da nova ativação: `valid=0`, `lemon_status=unknown_instance`, `last_success_at` vazio. Se a nova ativação falha por rede, `LicenseNetworkError` sai e o registo continua inválido. Dois dias depois, mesmo com o `httpx` a responder como Pro, `is_pro_active()` fica falso e `cached` fica falso.
- **P2, trocar a chave A por uma chave B inválida.** Antes de gravar B, o Atlas chama `/licenses/deactivate` com a chave e o `instance_id` de A. Se essa chamada confirma a libertação, B fica Free e `prev_license_key` fica vazio. Se falha por rede, A fica em `prev_license_key` e `prev_instance_id` (colunas novas, `ALTER TABLE ... ADD COLUMN` só se faltarem). B não fica Pro e `last_success_at` fica vazio. Colar A outra vez chama validate com o `instance_id` guardado, não activate. «Deactivate on this PC» (`deactivate()`) liberta essa instância e apaga `prev_*`.
- **P2, desativação recusada.** Resposta `disabled` ou `expired` grava a recusa, põe `valid=0`, limpa `last_success_at` e mantém o `instance_id`. `pro` fica falso no mesmo dia. Dois dias depois, uma falha de rede no validate não repõe o Pro.

```text
cd backend && python3 -m pytest tests/test_license.py -q --tb=short
```

exit code 0 — 47 passed, 12 warnings, 0.88s. Os warnings são os mesmos de `on_event` e do parser de formulários. Nenhum teste falhou.

### INFERENCE

- Se a libertação de A confirma e a chamada seguinte, para B, falha por rede, o registo local de A já foi marcado inválido e sem instância. A margem antiga não regressa.

### NOT VERIFIED

- Codex outra vez, neste HEAD.
- Chamada real à Lemon Squeezy.

## Simplificação em `c5ecf02` — 2026-11-15T16:39:55Z

Os três P2 novos vinham da recuperação com `prev_*`. Em vez de fechar cada ramo, esse caminho deixou de existir. Ficheiros: `backend/license.py`, `backend/tests/test_license.py` e este.

### VERIFIED

- `prev_license_key` e `prev_instance_id` já não entram em ler, gravar, ativar, desativar nem na resposta pública. O `CREATE TABLE` e o `ALTER TABLE ... ADD COLUMN` mantêm as colunas. Não há `DROP COLUMN`.
- Com `instance_id` guardado, uma chave diferente é recusada com «Deactivate the current license on this PC first (Settings → License → Deactivate on this PC).» O registo não muda e não há chamada remota. O Pro da chave atual mantém-se.
- Sem `instance_id`, uma chave diferente segue a ativação normal.
- `deactivate()` com sucesso apaga a chave, o `instance_id` e o Pro.
- Falha de rede em `deactivate()` não altera o registo, levanta `LicenseNetworkError`, e `key_present` continua verdadeiro.
- Recusa explícita `disabled`, `expired` ou instância desconhecida apaga a chave, o `instance_id` e `last_success_at`. `pro` fica falso. Dois dias depois, uma resposta que seria Pro não repõe o Pro.
- `LEMON_STORE_ID` e `LEMON_PRODUCT_ID` são constantes do módulo, ambas `0`. Sem `PYTEST_CURRENT_TEST` e sem `ATLAS_ENV` de desenvolvimento, as variáveis de ambiente não mudam os ids: uma chave da loja 99 continua Pro. Com `ATLAS_ENV=development`, o override de teste volta a valer. A regra «os dois a 0 saltam o teste; um só definido não dá Pro» mantém-se nos testes.
- A recusa de instância desconhecida continua a ser gravada, com a margem limpa, antes de uma nova ativação.

```text
cd backend && python3 -m pytest tests/test_license.py -q --tb=short
```

exit code 0 — 50 passed, 12 warnings, 0.76s. Os warnings são os mesmos de `on_event` e do parser de formulários. Nenhum teste falhou.

### NOT VERIFIED

- Codex neste HEAD.
- Chamada real à Lemon Squeezy.
- O botão no browser.

## Recusa local sem revalidar — 2026-11-15T16:44:08Z

P2 em `f346289`: a recusa de uma chave diferente chamava `public_state()`, e um `last_verified_at` com mais de um dia disparava `_refresh_if_due()`.

### VERIFIED

- A resposta dessa recusa sai de `_format_public_state` sobre o registo já lido. Não chama `_refresh_if_due` nem a Lemon, e não grava.
- `public_state(refresh=False)` existe para o mesmo formato sem revalidar. O caminho normal de `public_state()` continua a revalidar.
- Teste com `last_verified_at` e `last_success_at` dois dias no passado: nenhuma chamada HTTP, o registo depois é igual ao de antes, `activated` é falso, `pro` mantém-se, e a frase pedida está na resposta.
- `LEMON_STORE_ID` e `LEMON_PRODUCT_ID` continuam `0`. O id de produto não foi escrito.

```text
cd backend && python3 -m pytest tests/test_license.py -q --tb=short
```

exit code 0 — 51 passed, 12 warnings, 0.76s. Os warnings são os mesmos de `on_event` e do parser de formulários. Nenhum teste falhou.

### NOT VERIFIED

- Codex neste HEAD.
- Chamada real à Lemon Squeezy.
