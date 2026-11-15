# Pedido: IDs reais da loja e do produto na licença do Sr Atlas

forge-key: sratlas:dispatch:5. Seguimento do PR #67 (licença por PC), autorizado pelo Fundador a 2026-11-15. Construção: Cursor (neste ramo). Revisão: Claude + Codex. Merge só com o «sim» do Fundador.

## Âmbito, e só este
Em `backend/license.py`:
- `LEMON_STORE_ID = 524518` (loja «Forge Factory Lab», forgefactorylab.lemonsqueezy.com);
- `LEMON_PRODUCT_ID = 1529348` (produto «Sr. Atlas Pro»).

A substituição por ambiente fica só para os testes e para o desenvolvimento, como já está. Os testes que dependem dos valores 0 por omissão passam a fixar os valores explicitamente (monkeypatch ou ambiente de teste), sem mudar o comportamento testado. Junta um teste que confirme os valores de produção.

## Entrega
`pytest tests/test_license.py` a passar; `docs/entregas/licenca-ids/ENTREGA.md`.
