# Pedido: licença do Sr Atlas Pro com ativação por PC e verificação da loja e do produto

forge-key: sratlas:dispatch:4. Alteração à Fase 2 autorizada pelo Fundador a 2026-11-15 («avança com a proteção de todos os nossos produtos»). Construção: Cursor (neste ramo). Revisão: Claude + Codex. Merge só com o «sim» do Fundador.

## Problema (verificado em `backend/license.py`, `main` b937542)
1. O Atlas só chama `POST /v1/licenses/validate`, sem `instance_id`. A ativação nunca é registada na Lemon Squeezy, por isso o «Activation limit» do produto não tem efeito: a mesma chave Pro funciona em qualquer número de PCs.
2. A resposta não é conferida contra a nossa loja e o nosso produto. Uma chave válida de **qualquer** loja Lemon Squeezy desbloqueia o Pro.

## Âmbito, e só este (`backend/license.py` e os seus testes)
1. **Ativação:** em `activate(key)`, `POST https://api.lemonsqueezy.com/v1/licenses/activate`, form com `license_key` e `instance_name` = um identificador estável do PC, sem dados pessoais (por exemplo um hash SHA-256 truncado do `MachineGuid` do Windows ou de `uuid.getnode()`, com o prefixo `atlas-`).
   - Guardar o `instance.id` devolvido na tabela `atlas_license`. A coluna nova entra com `ALTER TABLE ... ADD COLUMN`, só se não existir; nunca se apaga nem se recria a tabela.
   - Se a chave já estiver ativa **neste** PC (o mesmo `instance_id` guardado), não ativar outra vez.
2. **Validação:** `validate` passa a enviar `license_key` e `instance_id`. Uma resposta só conta como Pro com `valid=true`, `license_key.status == "active"`, e `meta.store_id` e `meta.product_id` iguais às constantes `LEMON_STORE_ID` e `LEMON_PRODUCT_ID`.
   - As constantes vêm de variáveis de ambiente com valor por omissão 0. Enquanto forem 0, a verificação da loja e do produto **não é feita**, e fica um aviso uma vez no log. Assim nada muda para quem já testa sem produto criado.
3. **Recusas explícitas** (limite de ativações atingido, chave desativada ou expirada, loja ou produto errados, instância desconhecida) → o Atlas volta ao Free sem perder dados, com mensagens claras em inglês. Exemplo: «This key is already active on another PC. Deactivate it there or contact support.»
4. **Desativação:** função `deactivate()` que chama `POST /v1/licenses/deactivate` (`license_key`, `instance_id`) e volta ao Free. Expor em `POST /api/license/deactivate`, com a mesma proteção das outras rotas de licença, e um botão «Deactivate on this PC» em Settings → License, para o cliente poder mudar de PC.
5. **Mantém-se igual:** a revalidação no máximo uma vez por dia; a margem de 7 dias sem rede (mas só para falhas de rede, nunca para recusas explícitas); a chave nunca aparece em respostas, logs nem relatórios.

## Fora do âmbito
Qualquer outra alteração à Fase 2, o instalador e as dependências novas (usar o `httpx` que já existe).

## Entrega
- Testes `pytest` para: ativar, revalidar com `instance_id`, recusa por limite, loja ou produto errados, margem offline só para rede, desativação, e migração da tabela sem perder o registo existente.
- `docs/entregas/licenca-ativacao/RECECAO.md` e `ENTREGA.md` (VERIFIED, INFERENCE e NOT VERIFIED separados). A ativação real fica NOT VERIFIED até haver produto e chave de teste.
