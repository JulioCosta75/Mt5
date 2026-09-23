"""Budget-guarded Educador Q&A. No account or financial fields in the prompt."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ai_usage.application.services import UsageService, route_model
from education.ai.clients import LLMClient, LLMResponse
from education.ai.filter import filter_educador_output
from education.catalog import get_explanation

LIMIT_REACHED_TEXT = (
    "Limite de utilização atingido. Não foi feita nenhuma chamada ao modelo."
)

SYSTEM_INSTRUCTIONS = """És o Educador do Atlas Revolution.
Respondes em português de Portugal.
Explicas conceitos de trading e MetaTrader 5 de forma factual e geral.
Nunca dês conselhos financeiros nem recomendações de compra ou venda.
Nunca uses frases como "deverias", "recomendo" ou "compra agora".
Não tens acesso a contas, saldos, posições nem dados pessoais.
Se a pergunta pedir uma recomendação, recusa e explica o conceito em abstracto.
Isto é educação geral, idêntica para qualquer pessoa — não aconselhamento financeiro.
"""


@dataclass(frozen=True)
class Answer:
    text: str
    limit_reached: bool
    blocked: bool
    concept_id: str | None
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    usage_id: UUID | None = None


def build_educador_prompt(*, concept_id: str | None, question: str) -> str:
    """Assemble the LLM prompt from system text, catalog grounding, and the question.

    There is no parameter for account or user financial data. Catalog text is
    included only when ``get_explanation`` returns an entry; unknown ids are
    not invented.
    """
    parts = [SYSTEM_INSTRUCTIONS.strip(), ""]
    if concept_id:
        entry = get_explanation(concept_id)
        if entry is None:
            parts.append(
                f"Conceito pedido: {concept_id!r}. "
                "Não existe entrada de glossário para este id. "
                "Não inventes uma definição de catálogo."
            )
        else:
            parts.append("Texto de glossário (fonte estática, não inventar fora disto):")
            parts.append(f"id: {entry.id}")
            parts.append(f"título: {entry.title}")
            parts.append(f"definição: {entry.definition}")
            parts.append(f"exemplo: {entry.example}")
        parts.append("")
    parts.append("Pergunta do utilizador:")
    parts.append(question.strip())
    return "\n".join(parts)


def answer_educador_question(
    *,
    user_id: str,
    tier: str,
    question: str,
    client: LLMClient,
    usage: UsageService,
    concept_id: str | None = None,
    requested_model: str | None = None,
) -> Answer:
    """Answer a generic Educador question under the ai_usage budget guard.

    ``can_proceed`` runs first. On denial this returns a limit result and
    does not call ``client.generate``. Token counts recorded after a call
    are the client's own figures, never estimated here.
    """
    model = route_model(requested_model)
    if not usage.can_proceed(user_id, tier):
        return Answer(
            text=LIMIT_REACHED_TEXT,
            limit_reached=True,
            blocked=False,
            concept_id=concept_id,
            model=model,
        )

    prompt = build_educador_prompt(concept_id=concept_id, question=question)
    response: LLMResponse = client.generate(prompt)
    record = usage.record_usage(
        user_id=user_id,
        mode="educador",
        model=model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )
    filtered = filter_educador_output(response.text)
    return Answer(
        text=filtered.text,
        limit_reached=False,
        blocked=not filtered.allowed,
        concept_id=concept_id,
        model=model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        usage_id=record.id,
    )
