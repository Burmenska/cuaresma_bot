import os
from datetime import date, datetime, time

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import json
from pathlib import Path

# Load environment variables from .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set in .env")

# Cargar la Biblia RV1909 en español
BIBLE = json.loads(Path("data/rv_1909.json").read_text(encoding="utf-8"))
VERSES = BIBLE["verses"]

# Plan de lecturas de 40 días
READINGS_PLAN = json.loads(
    Path("data/cuaresma_readings.json").read_text(encoding="utf-8")
)

# Lent 2026 dates (Ash Wednesday to Holy Saturday)
LENT_START = date(2026, 2, 18)
LENT_END = date(2026, 4, 4)

SUBSCRIBERS: set[int] = set()

PRAYERS_DATA = json.loads(
    Path("data/prayers.json").read_text(encoding="utf-8")
)

PRAYERS: list[str] = [
    PRAYERS_DATA["padre_nuestro"],
    PRAYERS_DATA["ave_maria"],
]



BOOK_NORMALIZATION = {
    "Génesis": "Génesis",
    "Éxodo": "Éxodo",
    "Levítico": "Levítico",
    "Números": "Números",
    "Deuteronomio": "Deuteronomio",
    "Salmos": "Salmos",
    "1 Samuel": "1 Samuel",
    "2 Samuel": "2 Samuel",
    "1 Reyes": "1 Reyes",
    "Oseas": "Oseas",
    "Isaías": "Isaías",
    "Ezequiel": "Ezequiel",
    "Mateo": "Mateo",
    "Marcos": "Marcos",
    "Lucas": "Lucas",
    "Juan": "Juan",
    "Hechos": "Hechos",
    "Gálatas": "Gálatas",
    "Hebreos": "Hebreos",
    "Apocalipsis": "Apocalipsis",
}


def split_message(text: str, limit: int = 4000) -> list[str]:
    """Split a long text into pieces under Telegram's limit."""
    parts: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        parts.append(text)
    return parts


def get_verses(
    book_name: str,
    chapter: int,
    start_verse: int | None,
    end_verse: int | None,
) -> list[str]:
    norm_book = BOOK_NORMALIZATION.get(book_name, book_name)
    out: list[str] = []
    for v in VERSES:
        if v["book_name"] != norm_book:
            continue
        if v["chapter"] != chapter:
            continue
        verse_no = v["verse"]
        if start_verse is not None and verse_no < start_verse:
            continue
        if end_verse is not None and verse_no > end_verse:
            continue
        out.append(f'{verse_no}. {v["text"]}')
    return out


def parse_single_reference(ref: str) -> list[tuple[str, int, int | None, int | None]]:
    ref = ref.strip()
    if not ref:
        return []

    parts = ref.split()
    if parts[0] in ("1", "2", "3"):
        book_name = " ".join(parts[:2])
        rest = " ".join(parts[2:])
    else:
        book_name = parts[0]
        rest = " ".join(parts[1:])

    book_name = book_name.strip()
    if not rest:
        return []

    if ":" in rest:
        chap_str, verse_part = rest.split(":", 1)
        chapter = int(chap_str)
        verse_part = verse_part.strip()
        if "-" in verse_part:
            start_v, end_v = verse_part.split("-", 1)
            return [(book_name, chapter, int(start_v), int(end_v))]
        else:
            v = int(verse_part)
            return [(book_name, chapter, v, v)]
    else:
        if "-" in rest:
            start_ch, end_ch = rest.split("-", 1)
            start_ch = int(start_ch)
            end_ch = int(end_ch)
            return [
                (book_name, ch, None, None) for ch in range(start_ch, end_ch + 1)
            ]
        else:
            chapter = int(rest)
            return [(book_name, chapter, None, None)]


def get_passage_text(full_ref: str) -> str:
    if not full_ref:
        return ""

    segments = [s.strip() for s in full_ref.split(";") if s.strip()]
    all_lines: list[str] = []
    current_book: str | None = None

    for seg in segments:
        is_new_book = seg.startswith(
            (
                "Génesis",
                "Éxodo",
                "Levítico",
                "Números",
                "Deuteronomio",
                "Salmos",
                "1 Samuel",
                "2 Samuel",
                "1 Reyes",
                "Oseas",
                "Isaías",
                "Ezequiel",
                "Mateo",
                "Marcos",
                "Lucas",
                "Juan",
                "Hechos",
                "Gálatas",
                "Hebreos",
                "Apocalipsis",
            )
        )

        if is_new_book:
            current_book = None
            parsed_ranges = parse_single_reference(seg)
        else:
            if current_book is None:
                continue
            seg_with_book = f"{current_book} {seg}"
            parsed_ranges = parse_single_reference(seg_with_book)

        if parsed_ranges:
            current_book = parsed_ranges[-1][0]

        for book_name, chapter, start_v, end_v in parsed_ranges:
            lines = get_verses(book_name, chapter, start_v, end_v)
            if lines:
                header = f"{book_name} {chapter}"
                if start_v is not None and end_v is not None:
                    header += f":{start_v}-{end_v}"
                all_lines.append(header)
                all_lines.extend(lines)
                all_lines.append("")

    return "\n".join(all_lines).strip()


def lent_day_number(today: date) -> int | None:
    if not (LENT_START <= today <= LENT_END):
        return None
    return (today - LENT_START).days + 1


def get_prayer_for_day(day_n: int) -> str:
    index = (day_n - 1) % len(PRAYERS)
    return PRAYERS[index]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    SUBSCRIBERS.add(chat_id)

    today = datetime.utcnow().date()
    day_n = lent_day_number(today)

    if day_n is None:
        msg = (
            "Has iniciado el bot de Cuaresma.\n\n"
            "Actualmente no estamos en tiempo de Cuaresma, pero en cuanto "
            "empiece, recibirás una oración diaria."
        )
        await update.message.reply_text(msg)
        return

    header = (
        f"Hoy es el día {day_n} de la Cuaresma. "
        "Aquí tienes la oración y lectura bíblica de hoy:"
    )
    prayer = get_prayer_for_day(day_n)
    ref = READINGS_PLAN.get(str(day_n), "")
    bible_text = get_passage_text(ref)

    text = f"{header}\n\n{prayer}\n\nLectura de hoy ({ref}):\n\n{bible_text}"

    for chunk in split_message(text):
        await update.message.reply_text(chunk)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id in SUBSCRIBERS:
        SUBSCRIBERS.remove(chat_id)
        await update.message.reply_text(
            "Has dejado de recibir las oraciones diarias de Cuaresma."
        )
    else:
        await update.message.reply_text(
            "No estabas suscrito a las oraciones diarias."
        )


async def send_daily_prayers(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.utcnow().date()
    day_n = lent_day_number(today)
    if day_n is None:
        return

    header = (
        f"Hoy es el día {day_n} de la Cuaresma. "
        "Aquí tienes la oración y lectura bíblica de hoy:"
    )
    prayer = get_prayer_for_day(day_n)
    ref = READINGS_PLAN.get(str(day_n), "")
    bible_text = get_passage_text(ref)

    text = f"{header}\n\n{prayer}\n\nLectura de hoy ({ref}):\n\n{bible_text}"

    for chat_id in list(SUBSCRIBERS):
        try:
            for chunk in split_message(text):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        except Exception:
            continue


def main() -> None:
    print("Starting Cuaresma bot")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))

    job_queue = application.job_queue
    job_queue.run_daily(
        send_daily_prayers,
        time=time(hour=7, minute=0),
        name="cuaresma_daily_prayers",
    )

    application.run_polling()


if __name__ == "__main__":
    main()
