"""Parse one-way Telegram commands. Never AI-interpreted."""

from __future__ import annotations

from dataclasses import dataclass

INFORMATIONAL_REPLY = (
    "Este canal é exclusivamente informativo. O Sr. Atlas não aceita "
    "instruções, decisões de investimento ou ordens de negociação pelo "
    "Telegram. Utilize o dashboard para gerir as suas preferências."
)

HELP_TEXT = (
    "Comandos disponíveis:\n"
    "/start <código> — associar esta conversa à sua conta Atlas\n"
    "/help — mostrar estas instruções\n"
    "/stop — deixar de receber avisos neste chat\n\n"
    "Este canal é exclusivamente informativo. O Sr. Atlas não aceita "
    "instruções, decisões de investimento ou ordens de negociação pelo Telegram."
)

START_OK_REPLY = (
    "Conta associada. Este canal é exclusivamente informativo."
)

INVALID_CODE_REPLY = "Código inválido ou já utilizado."

STOP_OK_REPLY = "Avisos deste chat desativados."

STOP_UNKNOWN_REPLY = "Não havia uma associação activa neste chat."

HANDLED_COMMANDS = frozenset({"start", "help", "stop"})


@dataclass(frozen=True)
class ParsedCommand:
    """A recognised command, or command=None for the fixed fallback."""

    command: str | None
    argument: str | None
    chat_id: str
    raw_text: str


def extract_chat_id(update: dict) -> str | None:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return None
    return str(chat_id)


def extract_text(update: dict) -> str:
    message = update.get("message") or update.get("edited_message") or {}
    text = message.get("text")
    return text if isinstance(text, str) else ""


def parse_command_text(text: str) -> tuple[str | None, str | None]:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None, None
    parts = raw.split()
    token = parts[0][1:]
    if "@" in token:
        token = token.split("@", 1)[0]
    token = token.lower()
    argument = parts[1] if len(parts) > 1 else None
    if token in HANDLED_COMMANDS:
        return token, argument
    return None, None


def parse_update(update: dict) -> ParsedCommand | None:
    chat_id = extract_chat_id(update)
    if chat_id is None:
        return None
    raw_text = extract_text(update)
    command, argument = parse_command_text(raw_text)
    return ParsedCommand(
        command=command,
        argument=argument,
        chat_id=chat_id,
        raw_text=raw_text,
    )
