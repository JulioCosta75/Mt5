# Atlas beta — tester guide

One unsigned installer (`Atlas_Setup.exe`). Windows 10 or 11, 64-bit.
MetaTrader 5 is already installed and you are logged into a **demo**
account. Atlas does not promise profits and does not limit losses.

Free is one MT5 account. A Pro key is not part of this beta.

## Download and SmartScreen

You receive `Atlas_Setup.exe` from the person who invited you. It is not
signed (`NotSigned`). Windows shows “Windows protected your PC”.

1. Click **More info**.
2. Click **Run anyway**.

That warning is expected. Do not turn SmartScreen off.

## Install

No administrator password for the Atlas install. It goes to
`%LOCALAPPDATA%\Atlas`. When asked, enter the **demo** login, password,
and server. Leave the terminal path empty unless MT5 is not in the
usual place.

## First start

The Atlas icon sits in the system tray. The dashboard is
`http://127.0.0.1:8001/`.

In MetaTrader 5, turn **Algo Trading** on (toolbar button, green).
Without it the bridge cannot see the demo account. In Atlas, open
Settings and use **Save & Connect** if the header still says
Configuration Mode.

The header version should be **v0.3.1**.

## Logs

`%LOCALAPPDATA%\Atlas\logs`

`launcher.log`, `backend.out.log`, `backend.err.log`, `bridge.out.log`,
`bridge.err.log`.

Zip that folder and send it to the person who sent the installer.
Do not send `%LOCALAPPDATA%\Atlas\data`: it holds the demo password.

## Uninstall

Windows Settings → Apps → Atlas → Uninstall, or the Start menu shortcut.
Program files go away. **Data and logs stay** in `%LOCALAPPDATA%\Atlas`.
Delete that folder yourself only if you want them gone.

---

# Atlas beta — guia do tester

Um instalador sem assinatura (`Atlas_Setup.exe`). Windows 10 ou 11,
64 bits. O MetaTrader 5 já está instalado e a sessão é uma conta
**demo**. O Atlas não promete lucros e não limita perdas.

Free é uma conta MT5. Esta beta não inclui chave Pro.

## Descarga e SmartScreen

Recebe o `Atlas_Setup.exe` de quem o convidou. Não está assinado
(`NotSigned`). O Windows mostra “Windows protected your PC”.

1. Clique em **More info** (Mais informações).
2. Clique em **Run anyway** (Executar mesmo assim).

O aviso é esperado. Não desligue o SmartScreen.

## Instalar

A instalação do Atlas não pede senha de administrador. Fica em
`%LOCALAPPDATA%\Atlas`. Quando pedir, use o login, a senha e o servidor
da conta **demo**. Deixe o caminho do terminal vazio, salvo se o MT5
não estiver no sítio habitual.

## Primeiro arranque

O ícone do Atlas fica na área de notificação. O painel é
`http://127.0.0.1:8001/`.

No MetaTrader 5, ligue **Algo Trading** (botão da barra, verde). Sem
isso a ponte não vê a conta demo. No Atlas, abra Settings e use
**Save & Connect** se o cabeçalho ainda disser Configuration Mode.

A versão no cabeçalho deve ser **v0.3.1**.

## Registos

`%LOCALAPPDATA%\Atlas\logs`

`launcher.log`, `backend.out.log`, `backend.err.log`, `bridge.out.log`,
`bridge.err.log`.

Compacte essa pasta e envie-a a quem lhe mandou o instalador.
Não envie `%LOCALAPPDATA%\Atlas\data`: tem a senha da demo.

## Desinstalar

Definições do Windows → Aplicações → Atlas → Desinstalar, ou o atalho
do menu Iniciar. Os ficheiros do programa saem. **Os dados e os
registos ficam** em `%LOCALAPPDATA%\Atlas`. Apague essa pasta só se
os quiser mesmo eliminar.
