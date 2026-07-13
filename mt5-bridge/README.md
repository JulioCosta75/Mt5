# MT5 Bridge

Serviço Python que corre numa máquina **Windows** com o terminal MetaTrader 5 instalado e logado, e expõe os dados da conta numa API HTTP simples para ser consumida pelo backend Linux do projeto **QUANT.SUPERVISE**.

---

## Porquê um bridge separado?

A biblioteca oficial `MetaTrader5` (PyPI) **só funciona em Windows** porque comunica via IPC com o terminal MT5 (que também é Windows-only). O nosso backend principal corre num pod Linux na Emergent — daí a necessidade de um processo separado em Windows que faça a ponte.

---

## Limitações conhecidas

| # | Limitação | Consequência |
|---|-----------|--------------|
| 1 | Apenas Windows | Tem de correr numa máquina Windows |
| 2 | Terminal MT5 tem de estar aberto | Se fechar, o bridge fica offline (`/health` reporta) |
| 3 | Algo Trading tem de estar ON | Tools → Options → Expert Advisors → "Allow algorithmic trading" |
| 4 | Uma conta por processo | Para N contas, corra N bridges em portas diferentes (BRIDGE_PORT distinto, BRIDGE_TOKEN distinto) |
| 5 | API síncrona | Wrap em `asyncio.to_thread` (já feito) |
| 6 | Sem histórico de equity nativo | Reconstruímos via `history_deals_get` + gravamos snapshots ao vivo |
| 7 | Reconexão automática frágil | Healthcheck reporta; reinicie o bridge se preciso |

---

## Requisitos

- Windows 10/11 ou Windows Server 2019+
- **Python 3.10–3.12** (a `MetaTrader5` ainda não é estável em 3.13)
- Terminal MetaTrader 5 do seu broker, com a conta a usar **já logada**
- "Allow algorithmic trading" **ativado** em Tools → Options → Expert Advisors

---

## Instalação

1. **Copie esta pasta `mt5-bridge/`** para a sua máquina Windows (ex.: `C:\quant\mt5-bridge\`).

2. Abra **PowerShell** ou **cmd** dentro dessa pasta.

3. Crie e ative um virtualenv (o `run.bat` faz isto automaticamente também):

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Copie `.env.example` para `.env` e edite:

   ```ini
   MT5_LOGIN=5609382
   MT5_PASSWORD=********
   MT5_SERVER=Darwinex-Live
   # MT5_TERMINAL_PATH=C:\Program Files\Darwinex MT5\terminal64.exe

   BRIDGE_TOKEN=<gerar com: python -c "import secrets;print(secrets.token_urlsafe(32))">
   BRIDGE_HOST=0.0.0.0
   BRIDGE_PORT=8002

   SNAPSHOT_INTERVAL_SECONDS=10
   ```

5. Arranque:

   ```bat
   run.bat
   ```

   Ou diretamente:

   ```bat
   python bridge_server.py
   ```

---

## Testar a ligação (no Windows, isoladamente)

```powershell
# 1. Health (sem autenticação)
curl http://localhost:8002/health

# Deve devolver algo como:
# {"status":"ok","terminal_connected":true,"account_logged_in":true,
#  "trade_allowed":true,"login":5609382,"server":"Darwinex-Live",
#  "last_error":null,"server_time":"2026-01-15T18:42:01+00:00"}

# 2. Account info (com token)
$T = "<o-seu-BRIDGE_TOKEN>"
curl -H "Authorization: Bearer $T" http://localhost:8002/account

# 3. Posições abertas
curl -H "Authorization: Bearer $T" http://localhost:8002/positions

# 4. Ordens pendentes
curl -H "Authorization: Bearer $T" http://localhost:8002/orders

# 5. Histórico de deals dos últimos 30 dias
curl -H "Authorization: Bearer $T" "http://localhost:8002/deals?days=30"

# 6. Curva de equity reconstruída + snapshots
curl -H "Authorization: Bearer $T" "http://localhost:8002/equity-history?days=90"
```

---

## Endpoints expostos

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| GET | `/health` | — | Estado da ligação ao terminal + conta |
| GET | `/account` | Bearer | Info da conta MT5 (balance, equity, margin, etc.) |
| GET | `/positions` | Bearer | Lista de posições abertas |
| GET | `/orders` | Bearer | Lista de ordens pendentes |
| GET | `/deals?days=N` | Bearer | Histórico de deals fechados (até 365 dias) |
| GET | `/equity-history?days=N` | Bearer | Série de equity (reconstrução + snapshots) |

Toda a documentação interativa Swagger em `http://localhost:8002/docs`.

---

## Expor o bridge ao backend Linux

Em desenvolvimento, pode usar uma das seguintes opções:

### Opção A — Cloudflare Quick Tunnel (zero-config)
```powershell
# Instalar uma vez
winget install --id Cloudflare.cloudflared

# Arrancar tunnel temporário
cloudflared tunnel --url http://localhost:8002
# → devolve uma URL tipo https://random-xxxx.trycloudflare.com
```
No backend Linux, defina `MT5_BRIDGE_URL=https://random-xxxx.trycloudflare.com`.

### Opção B — Tailscale (privado, persistente)
Instale Tailscale em ambos os lados e use o hostname `.ts.net`.

### Opção C — ngrok
```powershell
ngrok http 8002
```

### Opção D — apenas local
Se executar também o backend Linux através de WSL2 no mesmo Windows, pode usar `http://host.docker.internal:8002` ou o IP da máquina.

---

## Arquivo de dados

O bridge cria um SQLite local (`bridge_data.db`) com:
- `equity_snapshots` — uma linha a cada `SNAPSHOT_INTERVAL_SECONDS`
- `reconstructed_equity` — cache da curva reconstruída

Pode apagar este ficheiro a qualquer momento — será recriado.

---

## Multi-conta (futuro)

Para supervisionar N contas, arranque N bridges:

```bat
REM Conta 1
set BRIDGE_PORT=8002 && set MT5_LOGIN=5609382 && python bridge_server.py

REM Conta 2 (novo cmd)
set BRIDGE_PORT=8003 && set MT5_LOGIN=5155368 && python bridge_server.py
```

E no backend Linux:
```env
MT5_BRIDGE_URLS=https://tunnel-1.example.com,https://tunnel-2.example.com
MT5_BRIDGE_TOKENS=token1,token2
```

---

## Resolução de problemas

| Sintoma | Causa provável | Solução |
|---------|---------------|---------|
| `MT5 error [-10005]` no startup | Terminal MT5 não está aberto | Abra o terminal MT5 |
| `MT5 error [-10004]` | Login/password/server errados | Reveja `.env` |
| `MT5 error [-10027]` | Algo trading desativado | Ative em Tools → Options → Expert Advisors |
| `MT5 error [-10003]` | `terminal64.exe` não encontrado / path em falta | Deixe o MT5 **a correr** antes de iniciar o Atlas (auto-detecção) ou defina `MT5_TERMINAL_PATH` com barras `/` (ex.: `C:/Program Files/Darwinex MT5/terminal64.exe`) |
| `/health` mostra `last_error="initialize failed"` | DLL do MT5 não acessível | Defina `MT5_TERMINAL_PATH` para o `terminal64.exe` correto |
| Equity history vazia | Sem deals nos últimos 90 dias | Diminua `days` ou aguarde snapshots ao vivo |
