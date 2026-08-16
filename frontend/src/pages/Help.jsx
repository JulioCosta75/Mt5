import React from "react";
import PageShell from "@/pages/PageShell";
import { forgeFactoryLogo } from "@/assets/branding";

function Doc({ title, children, testId }) {
  return (
    <div className="panel doc-block" data-testid={testId}>
      <div className="panel-header">
        <span className="panel-title">{title}</span>
      </div>
      <div className="doc-body">{children}</div>
    </div>
  );
}

/** End-user Help — Portuguese guide. Technical architecture lives in docs/ + README. */
export default function Help() {
  return (
    <PageShell active="help" testId="help-page">
      <section className="doc-hero">
        <img
          src={forgeFactoryLogo}
          alt="Forge Factory Lab"
          className="doc-hero-logo"
          data-testid="help-forge-logo"
        />
        <div>
          <h1>Help</h1>
          <p className="mono">Sr. Atlas — Guia do Utilizador</p>
        </div>
      </section>

      <Doc title="Porque existe o Sr. Atlas" testId="help-why">
        <p>
          O trading é muitas vezes vendido como uma promessa de enriquecer depressa.
          Na realidade, a maioria de quem tenta acaba a agir por impulso — o que, sem
          perceber, se parece muito com jogar à sorte. Estudar a sério é difícil,
          quase como perceber como um avião voa.
        </p>
        <p>
          O Sr. Atlas nasceu de uma necessidade real, não de uma oportunidade de
          negócio vista de fora: a de ter algo que ajudasse <b>a cada decisão</b>, e
          que ajudasse a <b>aprender com cada decisão</b> — não uma ferramenta que
          decide ou negoceia por ti.
        </p>
        <p><b>O que o Sr. Atlas NÃO faz:</b></p>
        <ul>
          <li>Não decide por ti.</li>
          <li>Não compra nem vende nada sozinho.</li>
          <li>Não toca no teu dinheiro nem nas tuas ordens.</li>
        </ul>
        <p>
          <b>O que o Sr. Atlas faz:</b> mostra-te a verdade sobre o estado real da
          tua conta, sem filtros e sem enfeites — mesmo quando essa verdade é
          desconfortável (por exemplo, avisar que os dados estão desatualizados, em
          vez de fingir que está tudo bem). A decisão continua sempre a ser tua; o
          Atlas só te ajuda a decidir a ver com clareza.
        </p>
      </Doc>

      <Doc title="O painel, elemento a elemento" testId="help-panel">
        <p><b>Barra superior</b></p>
        <ul>
          <li>
            <b>Separadores</b> (Overview, Strategies, Risk, Reports, Audit, About,
            Help, Settings) — as diferentes vistas do Atlas.
          </li>
          <li>
            <b>REFRESH FEED</b> — força uma atualização imediata dos dados, em vez
            de esperar pelo próximo ciclo automático.
          </li>
          <li>
            <b>v0.3.0 · [versão do código] · session-XXXX</b> — a versão exata
            instalada e o identificador da sessão atual, úteis para reportar
            problemas.
          </li>
        </ul>

        <p><b>Barra de estatísticas globais</b></p>
        <ul>
          <li>
            <b>TOTAL EQUITY</b> — o valor real da tua conta neste momento (saldo
            mais/menos o resultado das posições abertas).
          </li>
          <li>
            <b>DAILY P&amp;L</b> — quanto ganhaste ou perdeste hoje, em valor e em
            percentagem.
          </li>
          <li>
            <b>AVG DD</b> — a média do &quot;drawdown&quot; (quanto a conta caiu
            desde o pico mais recente) nas contas monitorizadas.
          </li>
          <li>
            <b>OPEN POS</b> — número de posições abertas neste momento.
          </li>
          <li>
            <b>ACCOUNTS</b> — quantas contas estão &quot;ao vivo&quot; (ligadas e a
            receber dados reais) sobre o total configurado.
          </li>
          <li>
            <b>ALERTS</b> — número de alertas ativos a precisar da tua atenção.
          </li>
          <li>
            <b>UTC, data/hora</b> — o relógio de referência do sistema (hora
            universal, não a hora local).
          </li>
        </ul>

        <p><b>Tabela &quot;MT5 Accounts&quot;</b></p>
        <p>
          Uma linha por conta MT5 ligada. Colunas: <b>Status</b>, <b>Account</b>{" "}
          (número da conta), <b>Broker</b> (corretora), <b>Strategy</b> (nome da
          estratégia associada), <b>Balance</b> (saldo), <b>Equity</b> (valor real,
          incluindo posições abertas), <b>Daily P&amp;L</b>, <b>DD</b> (drawdown
          atual), <b>POS</b> (posições abertas), <b>LEV</b> (alavancagem, ex:{" "}
          <code>1:30</code>), <b>Margin %</b> (nível de margem — quanto mais alto,
          mais folga tens antes de um &quot;stop out&quot; do broker).
        </p>

        <p><b>Secção &quot;Risk&quot;</b></p>
        <p>
          Repete os números da conta selecionada (Equity, Balance, Margin Used,
          Margin Lvl, Daily P&amp;L, Cur DD, Max DD, Leverage), e acrescenta:
        </p>
        <ul>
          <li>
            <b>Risk Limits</b> — três campos que defines tu:{" "}
            <b>Max Daily Loss (%)</b>, <b>Max Position Size (lots)</b>,{" "}
            <b>Max Open Positions</b> — com botão <b>Save Limits</b> para gravar.
          </li>
        </ul>

        <p><b>Painel &quot;Sr. Atlas Supervision&quot; (lado direito)</b></p>
        <ul>
          <li>
            Selo de estado geral: <b>OK</b> ou <b>WARNING</b>, com uma frase a
            explicar porquê (ex: &quot;MT5 bridge is unavailable; displayed data
            comes from cache and may be outdated&quot;).
          </li>
          <li>Resumo: Total Equity, Daily P&amp;L, Accounts Live, Active Alerts.</li>
          <li>
            <b>Core Services</b> — o estado de cada peça interna do Atlas, uma a
            uma:
            <ul>
              <li>
                <b>Backend</b> — o &quot;cérebro&quot; que serve o painel.
              </li>
              <li>
                <b>Store</b> — onde os dados ficam guardados.
              </li>
              <li>
                <b>Bridge</b> — a ligação direta ao teu terminal MT5.
              </li>
              <li>
                <b>Dashboard</b> — o próprio painel que estás a ver.
              </li>
            </ul>
            Cada uma mostra <b>OK</b> (verde) ou <b>DOWN</b> (vermelho). Se o
            Bridge estiver &quot;DOWN&quot;, os números que vês vêm de uma cópia
            guardada (cache), não ao vivo — o Atlas avisa sempre quando isto
            acontece.
          </li>
          <li>
            <b>Generate Sr. Atlas Report</b> — botão para criar um relatório da
            conta.
          </li>
          <li>
            <b>Recent Reports</b> — lista dos relatórios já gerados.
          </li>
        </ul>

        <p><b>Gráficos, em baixo</b></p>
        <ul>
          <li>
            <b>Equity Curve · 90D</b> — a evolução do valor da tua conta nos
            últimos 90 dias.
          </li>
          <li>
            <b>Drawdown · 90D</b> — a evolução das quedas desde o pico, no mesmo
            período.
          </li>
        </ul>

        <p><b>Histórico de operações (fundo do Overview)</b></p>
        <ul>
          <li>
            <b>Trade History</b> — lista das tuas operações já fechadas: símbolo,
            lado (compra/venda), lotes, hora de abertura e fecho, duração em
            minutos, resultado (P&amp;L) e estratégia associada. Podes filtrar por
            símbolo e por lado. No topo da tabela: resultado líquido total (
            <b>NET</b>), percentagem de operações ganhas (<b>WIN%</b>), e número
            de operações (<b>N</b>).
          </li>
        </ul>

        <p><b>Painel de alertas (lado direito)</b></p>
        <ul>
          <li>
            <b>Alerts</b> — contagem de alertas por gravidade (vermelho =
            crítico, laranja = aviso, azul = informativo). Mostra &quot;No
            alerts&quot; quando não há nada a assinalar.
          </li>
          <li>
            <b>System</b> — o &quot;pulso&quot; técnico do sistema:{" "}
            <b>API Latency</b>, <b>MT5 Bridge</b>, <b>Risk Engine</b>,{" "}
            <b>Telegram Notif</b>, <b>Last Heartbeat</b>, <b>Strategies Loaded</b>.
          </li>
        </ul>
      </Doc>

      <Doc title="Os outros separadores" testId="help-tabs">
        <p><b>Strategies</b></p>
        <p>
          Agrupa as tuas contas por estratégia em vez de por conta individual —
          útil se um dia tiveres várias contas a seguir a mesma abordagem. Mostra,
          por estratégia: contas associadas, quantas estão ao vivo, equity total,
          P&amp;L diário, posições abertas, drawdown médio.
        </p>
        <p><b>Risk</b></p>
        <p>
          A mesma secção &quot;Risk&quot; já descrita acima (Risk Limits), mas
          como página própria.
        </p>
        <p><b>Reports</b></p>
        <p>
          Lista dos relatórios já gerados pelo botão &quot;Generate Sr. Atlas
          Report&quot;, com estado, mensagem e origem de cada um. Vazio até
          gerares o primeiro.
        </p>
        <p><b>Audit</b></p>
        <p>
          Um registo histórico de eventos do sistema (o &quot;diário de
          bordo&quot; do Atlas) — separado do histórico de operações. Vazio até
          haver eventos registados.
        </p>
        <p><b>About</b></p>
        <p>
          Página de apresentação da marca — o logótipo e princípios da Forge
          Factory Lab (&quot;Conhecimento, validação e verdade vêm antes da
          automação&quot;) e do Sr. Atlas. Não tem funcionalidade, é só
          identidade.
        </p>
        <p><b>Settings</b></p>
        <p>
          Onde ligas (ou alteras, a qualquer momento, sem reinstalar) a tua conta
          MT5:
        </p>
        <ul>
          <li>
            <b>MT5 Login</b> — o número da tua conta.
          </li>
          <li>
            <b>MT5 Password</b> — fica guardada; podes deixar em branco para
            manter a atual.
          </li>
          <li>
            <b>Server / Broker</b> — o nome do servidor da tua corretora (ex:{" "}
            <code>PepperstoneUK-Demo</code>).
          </li>
          <li>
            <b>Terminal path</b> (opcional) — onde o MT5 está instalado;
            normalmente não precisas de mexer, o Atlas encontra sozinho.
          </li>
          <li>
            <b>Bridge port</b> — a porta técnica usada para a ligação (não
            precisas de alterar isto, a não ser que saibas exatamente porquê).
          </li>
          <li>
            <b>Save &amp; Connect</b> — grava e liga.
          </li>
          <li>
            <b>Clear</b> — limpa os campos.
          </li>
        </ul>
        <p>
          Um indicador no topo mostra sempre se estás <b>Connected</b> (ligado)
          ou não, em tempo real.
        </p>
      </Doc>

      <Doc title="Antes de começares" testId="help-prereqs">
        <p>Precisas de:</p>
        <ol>
          <li>
            Uma conta MetaTrader 5 (demo ou real) já criada, com login, password e
            nome do servidor (ex: <code>PepperstoneUK-Demo</code>).
          </li>
          <li>O terminal MetaTrader 5 instalado neste computador.</li>
          <li>
            No terminal MT5: ir a <b>Ferramentas → Opções → Expert Advisors</b> e
            ativar <b>&quot;Allow algorithmic trading&quot;</b>. Sem isto, o Sr.
            Atlas liga-se à tua conta mas não consegue confirmar que está tudo
            pronto.
          </li>
        </ol>
      </Doc>

      <Doc title="Como ligar a tua conta" testId="help-connect">
        <ol>
          <li>Abre o Sr. Atlas.</li>
          <li>
            Vai a <b>Definições</b>.
          </li>
          <li>Introduz o login, password e servidor da tua conta MT5.</li>
          <li>
            Guarda. O painel deve mostrar os teus dados reais em poucos segundos.
          </li>
        </ol>
        <p>
          Não precisas de abrir o terminal MT5 manualmente primeiro — o Sr. Atlas
          trata disso sozinho.
        </p>
      </Doc>

      <Doc title="O que significam os estados do painel" testId="help-states">
        <div className="doc-table-wrap">
          <table className="doc-table">
            <thead>
              <tr>
                <th>Estado</th>
                <th>O que significa</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <b>OK / Saudável</b>
                </td>
                <td>Tudo ligado e a funcionar normalmente.</td>
              </tr>
              <tr>
                <td>
                  <b>WARNING (Aviso)</b>
                </td>
                <td>
                  Ligado, mas há algo a precisar da tua atenção — por exemplo,
                  &quot;Allow algorithmic trading&quot; desligado no terminal.
                </td>
              </tr>
              <tr>
                <td>
                  <b>PAUSED (Em pausa)</b>
                </td>
                <td>
                  A supervisão está temporariamente parada — normalmente porque a
                  ligação ao terminal MT5 foi interrompida.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          O Sr. Atlas nunca mostra &quot;tudo saudável&quot; se a ligação à tua
          conta estiver mesmo em baixo — preferimos avisar-te a mentir-te sobre o
          estado da tua conta.
        </p>
      </Doc>

      <Doc title="Problemas comuns" testId="help-troubleshoot">
        <p>
          <b>&quot;O painel não mostra os meus dados&quot;</b>
        </p>
        <ul>
          <li>Confirma que o terminal MT5 está instalado neste computador.</li>
          <li>
            Confirma que &quot;Allow algorithmic trading&quot; está ativado (ver
            acima).
          </li>
          <li>Confirma o login/password/servidor em Definições.</li>
        </ul>
        <p>
          <b>&quot;Aparece um aviso sobre trading automático desligado&quot;</b>
        </p>
        <ul>
          <li>
            Vai ao terminal MT5 → Ferramentas → Opções → Expert Advisors → ativa
            &quot;Allow algorithmic trading&quot;.
          </li>
        </ul>
        <p>
          <b>&quot;Instalei mas não abre nada no browser&quot;</b>
        </p>
        <ul>
          <li>
            Espera um minuto — os serviços podem demorar uns segundos a arrancar
            após a instalação.
          </li>
          <li>
            Se continuar sem abrir, tenta o atalho &quot;Start Atlas&quot; no menu
            Iniciar.
          </li>
        </ul>
      </Doc>

      <Doc title="Onde pedir ajuda" testId="help-report">
        <p>
          Se as secções acima não resolverem, usa o botão{" "}
          <b>&quot;Reportar problema&quot;</b> no painel. Ele junta
          automaticamente o estado de saúde do sistema e os registos relevantes —
          nunca as tuas credenciais — e envia diretamente para a Forge Factory
          Lab, com um clique.
        </p>
        <p className="doc-footnote">
          Este documento explica o que o Sr. Atlas faz e não faz. Se algo aqui não
          corresponder ao que vês no ecrã, é mais importante confiares no que vês
          do que neste texto — e por favor avisa-nos.
        </p>
      </Doc>
    </PageShell>
  );
}
