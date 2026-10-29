# SPDX-License-Identifier: AGPL-3.0-only
"""Sending email through the operator's SMTP server, and the daily digest of due marks."""

from __future__ import annotations

import smtplib
import ssl
import uuid
from datetime import datetime
from email.message import EmailMessage
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from nevus import settings_store
from nevus.db.models import NotificationDelivery, User
from nevus.domain.due import due_for_user
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register
from nevus.logging import get_logger
from nevus.reports.i18n import Words

log = get_logger(__name__)
DIGEST_KIND = "notify.email.digest"

TEXT = {
    "en": {
        "subject_one": "neVus: one mark is due for a photo",
        "subject_other": "neVus: {n} marks are due for a photo",
        "intro": "These marks are due for a new photo:",
        "due_since": "due since {date}",
        "open": "Open neVus: {url}",
        "footer": "You receive this because email reminders are on in your neVus settings. "
        "neVus is a personal documentation aid; it does not diagnose or assess any disease.",
        "test_subject": "neVus: test message",
        "test_body": "This is a test message from neVus. Email reminders will reach this address.",
    },
    "es": {
        "subject_one": "neVus: toca fotografiar una marca",
        "subject_other": "neVus: toca fotografiar {n} marcas",
        "intro": "Toca hacer una foto nueva de estas marcas:",
        "due_since": "pendiente desde el {date}",
        "open": "Abrir neVus: {url}",
        "footer": "Recibes esto porque tienes activados los recordatorios por correo en los ajustes de neVus. "
        "neVus es una ayuda personal de documentación; no diagnostica ni evalúa ninguna enfermedad.",
        "test_subject": "neVus: mensaje de prueba",
        "test_body": "Este es un mensaje de prueba de neVus. Los recordatorios por correo llegarán a esta dirección.",
    },
    "pt": {
        "subject_one": "neVus: uma marca tem foto pendente",
        "subject_other": "neVus: {n} marcas têm foto pendente",
        "intro": "Estas marcas têm uma foto nova pendente:",
        "due_since": "pendente desde {date}",
        "open": "Abrir o neVus: {url}",
        "footer": "Recebe esta mensagem porque os lembretes por e-mail estão ligados nas suas definições "
        "do neVus. O neVus é um auxiliar pessoal de documentação; não diagnostica nem avalia "
        "nenhuma doença.",
        "test_subject": "neVus: mensagem de teste",
        "test_body": "Esta é uma mensagem de teste do neVus. Os lembretes por e-mail chegarão a este endereço.",
    },
    "ca": {
        "subject_one": "neVus: toca fotografiar una marca",
        "subject_other": "neVus: toca fotografiar {n} marques",
        "intro": "Toca fer una foto nova d'aquestes marques:",
        "due_since": "pendent des del {date}",
        "open": "Obre el neVus: {url}",
        "footer": "Rebes això perquè tens activats els recordatoris per correu als ajustos del neVus. neVus és una "
        "ajuda personal de documentació; no diagnostica ni avalua cap malaltia.",
        "test_subject": "neVus: missatge de prova",
        "test_body": "Aquest és un missatge de prova del neVus. Els recordatoris per correu arribaran a aquesta "
        "adreça.",
    },
    "gl": {
        "subject_one": "neVus: toca fotografar unha marca",
        "subject_other": "neVus: toca fotografar {n} marcas",
        "intro": "Toca facer unha foto nova destas marcas:",
        "due_since": "pendente desde o {date}",
        "open": "Abrir neVus: {url}",
        "footer": "Recibes isto porque tes activados os recordatorios por correo nos axustes de neVus. neVus é unha "
        "axuda persoal de documentación; non diagnostica nin avalía ningunha enfermidade.",
        "test_subject": "neVus: mensaxe de proba",
        "test_body": "Esta é unha mensaxe de proba de neVus. Os recordatorios por correo chegarán a este enderezo.",
    },
    "eu": {
        "subject_one": "neVus: marka bati argazkia atera behar zaio",
        "subject_other": "neVus: {n} markari argazkia atera behar zaie",
        "intro": "Marka hauei argazki berri bat atera behar zaie:",
        "due_since": "{date} geroztik zain",
        "open": "Ireki neVus: {url}",
        "footer": "Mezu hau jasotzen duzu neVus-eko ezarpenetan posta bidezko gogorarazpenak aktibatuta dituzulako. "
        "neVus dokumentaziorako laguntza pertsonala da; ez du inolako gaixotasunik diagnostikatzen ez ebaluatzen.",
        "test_subject": "neVus: probako mezua",
        "test_body": "Hau neVus-en probako mezu bat da. Posta bidezko gogorarazpenak helbide honetara iritsiko dira.",
    },
    "fr": {
        "subject_one": "neVus : une marque est à photographier",
        "subject_other": "neVus : {n} marques sont à photographier",
        "intro": "Ces marques sont à photographier de nouveau :",
        "due_since": "à faire depuis le {date}",
        "open": "Ouvrir neVus : {url}",
        "footer": "Vous recevez ce message parce que les rappels par e-mail sont activés dans vos réglages neVus. "
        "neVus est une aide personnelle de documentation ; il ne diagnostique ni n'évalue aucune maladie.",
        "test_subject": "neVus : message de test",
        "test_body": "Ceci est un message de test de neVus. Les rappels par e-mail arriveront à cette adresse.",
    },
    "it": {
        "subject_one": "neVus: c'è un segno da fotografare",
        "subject_other": "neVus: ci sono {n} segni da fotografare",
        "intro": "Questi segni sono da fotografare di nuovo:",
        "due_since": "in attesa dal {date}",
        "open": "Apri neVus: {url}",
        "footer": "Ricevi questo messaggio perché i promemoria via e-mail sono attivi nelle impostazioni di neVus. "
        "neVus è un aiuto personale di documentazione; non diagnostica né valuta alcuna malattia.",
        "test_subject": "neVus: messaggio di prova",
        "test_body": "Questo è un messaggio di prova di neVus. I promemoria via e-mail arriveranno a questo indirizzo.",
    },
    "de": {
        "subject_one": "neVus: Eine Stelle ist für ein Foto fällig",
        "subject_other": "neVus: {n} Stellen sind für ein Foto fällig",
        "intro": "Diese Stellen sind für ein neues Foto fällig:",
        "due_since": "fällig seit {date}",
        "open": "neVus öffnen: {url}",
        "footer": "Du erhältst diese Nachricht, weil E-Mail-Erinnerungen in deinen neVus-Einstellungen aktiviert "
        "sind. neVus ist eine persönliche Dokumentationshilfe; es diagnostiziert oder beurteilt keine Krankheit.",
        "test_subject": "neVus: Testnachricht",
        "test_body": "Dies ist eine Testnachricht von neVus. E-Mail-Erinnerungen werden an diese Adresse zugestellt.",
    },
    "nl": {
        "subject_one": "neVus: één plek is aan een foto toe",
        "subject_other": "neVus: {n} plekken zijn aan een foto toe",
        "intro": "Deze plekken zijn aan een nieuwe foto toe:",
        "due_since": "openstaand sinds {date}",
        "open": "Open neVus: {url}",
        "footer": "Je ontvangt dit omdat e-mailherinneringen aan staan in je neVus-instellingen. neVus is een "
        "persoonlijk hulpmiddel voor documentatie; het stelt geen diagnose en beoordeelt geen enkele ziekte.",
        "test_subject": "neVus: testbericht",
        "test_body": "Dit is een testbericht van neVus. E-mailherinneringen komen op dit adres aan.",
    },
    "pl": {
        "subject_one": "neVus: jedno oznaczenie do sfotografowania",
        "subject_other": "neVus: oznaczenia do sfotografowania: {n}",
        "intro": "Te oznaczenia czekają na nowe zdjęcie:",
        "due_since": "do zrobienia od {date}",
        "open": "Otwórz neVus: {url}",
        "footer": "Dostajesz tę wiadomość, bo w ustawieniach neVus włączone są przypomnienia e-mail. neVus to "
        "osobista pomoc w dokumentowaniu; nie diagnozuje ani nie ocenia żadnej choroby.",
        "test_subject": "neVus: wiadomość testowa",
        "test_body": "To jest wiadomość testowa z neVus. Przypomnienia e-mail będą przychodzić na ten adres.",
    },
    "ru": {
        "subject_one": "neVus: пора сфотографировать одну метку",
        "subject_other": "neVus: меток, которые пора сфотографировать: {n}",
        "intro": "Для этих меток пора сделать новое фото:",
        "due_since": "ожидает с {date}",
        "open": "Открыть neVus: {url}",
        "footer": "Вы получаете это письмо, потому что в настройках neVus включены напоминания по электронной почте. "
        "neVus — личный помощник для ведения записей; он не диагностирует и не оценивает никакие заболевания.",
        "test_subject": "neVus: тестовое сообщение",
        "test_body": "Это тестовое сообщение от neVus. Напоминания по электронной почте будут приходить на этот адрес.",
    },
    "tr": {
        "subject_one": "neVus: bir işaretin fotoğraf zamanı geldi",
        "subject_other": "neVus: {n} işaretin fotoğraf zamanı geldi",
        "intro": "Bu işaretlerin yeni fotoğraf zamanı geldi:",
        "due_since": "{date} tarihinden beri bekliyor",
        "open": "neVus'u aç: {url}",
        "footer": "Bunu, neVus ayarlarınızda e-posta hatırlatıcıları açık olduğu için alıyorsunuz. neVus kişisel bir "
        "belgeleme yardımcısıdır; hiçbir hastalığı teşhis etmez veya değerlendirmez.",
        "test_subject": "neVus: test iletisi",
        "test_body": "Bu, neVus'tan bir test iletisidir. E-posta hatırlatıcıları bu adrese ulaşacak.",
    },
    "id": {
        "subject_one": "neVus: satu tanda perlu difoto",
        "subject_other": "neVus: {n} tanda perlu difoto",
        "intro": "Tanda-tanda ini perlu difoto ulang:",
        "due_since": "tertunda sejak {date}",
        "open": "Buka neVus: {url}",
        "footer": "Anda menerima ini karena pengingat email diaktifkan di pengaturan neVus Anda. neVus adalah alat "
        "bantu dokumentasi pribadi; neVus tidak mendiagnosis atau menilai penyakit apa pun.",
        "test_subject": "neVus: pesan uji coba",
        "test_body": "Ini adalah pesan uji coba dari neVus. Pengingat email akan sampai ke alamat ini.",
    },
    "zh": {
        "subject_one": "neVus：有 1 处标记该拍照了",
        "subject_other": "neVus：有 {n} 处标记该拍照了",
        "intro": "以下标记该拍新照片了：",
        "due_since": "自 {date} 起待拍",
        "open": "打开 neVus：{url}",
        "footer": "你收到这封邮件，是因为在 neVus 设置中开启了邮件提醒。neVus "
        "是个人记录辅助工具，不诊断也不评估任何疾病。",
        "test_subject": "neVus：测试消息",
        "test_body": "这是来自 neVus 的测试消息。邮件提醒将发送到此地址。",
    },
    "ja": {
        "subject_one": "neVus：写真を撮る時期のマークが1件あります",
        "subject_other": "neVus：写真を撮る時期のマークが{n}件あります",
        "intro": "次のマークは新しい写真を撮る時期です：",
        "due_since": "{date}から撮影待ち",
        "open": "neVusを開く：{url}",
        "footer": "neVusの設定でメール通知がオンになっているため、このメールが届いています。neVus"
        "は個人用の記録補助ツールであり、いかなる病気も診断・評価しません。",
        "test_subject": "neVus：テストメッセージ",
        "test_body": "neVusからのテストメッセージです。メール通知はこのアドレスに届きます。",
    },
    "ko": {
        "subject_one": "neVus: 사진을 찍을 표시가 1개 있어요",
        "subject_other": "neVus: 사진을 찍을 표시가 {n}개 있어요",
        "intro": "다음 표시는 새 사진을 찍을 때가 되었어요:",
        "due_since": "{date}부터 대기 중",
        "open": "neVus 열기: {url}",
        "footer": "neVus 설정에서 이메일 알림이 켜져 있어 이 메일을 받으셨어요. neVus는 개인 기록 보조 도구예요. 어떤 "
        "질환도 진단하거나 평가하지 않아요.",
        "test_subject": "neVus: 테스트 메시지",
        "test_body": "neVus에서 보낸 테스트 메시지예요. 이메일 알림이 이 주소로 도착해요.",
    },
    "hi": {
        "subject_one": "neVus: एक निशान की फ़ोटो लेने का समय है",
        "subject_other": "neVus: {n} निशानों की फ़ोटो लेने का समय है",
        "intro": "इन निशानों की नई फ़ोटो लेने का समय है:",
        "due_since": "{date} से बाकी",
        "open": "neVus खोलें: {url}",
        "footer": "आपको यह संदेश इसलिए मिला है क्योंकि आपकी neVus सेटिंग में ईमेल रिमाइंडर चालू हैं। neVus "
        "दस्तावेज़ीकरण का एक निजी सहायक है; यह किसी भी बीमारी का निदान या मूल्यांकन नहीं करता।",
        "test_subject": "neVus: परीक्षण संदेश",
        "test_body": "यह neVus की ओर से एक परीक्षण संदेश है। ईमेल रिमाइंडर इसी पते पर पहुँचेंगे।",
    },
    "ar": {
        "subject_one": "neVus: علامة واحدة بانتظار صورة جديدة",
        "subject_other": "neVus: علامات بانتظار صورة جديدة: {n}",
        "intro": "هذه العلامات بانتظار صورة جديدة:",
        "due_since": "بانتظار الصورة منذ {date}",
        "open": "افتح neVus: {url}",
        "footer": "تصلك هذه الرسالة لأن تذكيرات البريد الإلكتروني مفعّلة في إعدادات neVus. neVus أداة شخصية للتوثيق؛ "
        "ولا يشخّص أي مرض ولا يقيّمه.",
        "test_subject": "neVus: رسالة تجريبية",
        "test_body": "هذه رسالة تجريبية من neVus. ستصل تذكيرات البريد الإلكتروني إلى هذا العنوان.",
    },
}


def send(message: dict[str, Any]) -> None:
    """Deliver one message. Runs in a worker process; everything it needs travels in `message`."""
    email = EmailMessage()
    email["From"] = message["sender"]
    email["To"] = message["to"]
    email["Subject"] = message["subject"]
    email.set_content(message["body"])
    security = message["security"]
    if security == "ssl":
        client: smtplib.SMTP = smtplib.SMTP_SSL(
            message["host"], message["port"], timeout=20, context=ssl.create_default_context()
        )
    else:
        client = smtplib.SMTP(message["host"], message["port"], timeout=20)
    with client:
        if security == "starttls":
            client.starttls(context=ssl.create_default_context())
        if message.get("username"):
            client.login(message["username"], message.get("password") or "")
        client.send_message(email)


def envelope(config: settings_store.EmailConfig, to: str, subject: str, body: str) -> dict[str, Any]:
    return {
        "host": config.host,
        "port": config.port,
        "security": config.security,
        "username": config.username,
        "password": config.password,
        "sender": config.sender,
        "to": to,
        "subject": subject,
        "body": body,
    }


def digest_text(user: User, items: list[Any], public_url: str | None) -> tuple[str, str]:
    text = TEXT.get(user.language, TEXT["en"])
    subject = text["subject_one"] if len(items) == 1 else text["subject_other"].format(n=len(items))
    lines = [text["intro"], ""]
    words = Words(user.language)
    for item in items:
        label = item.lesion.label or words.zone(item.lesion.zone_code)
        lines.append(
            f"- {label} ({item.person.display_name}): {text['due_since'].format(date=item.next_due_on.isoformat())}"
        )
    if public_url:
        lines += ["", text["open"].format(url=public_url.rstrip("/"))]
    lines += ["", text["footer"]]
    return subject, "\n".join(lines)


def schedule_digests(ctx: JobContext, now: datetime | None = None) -> int:
    """Periodic: after the reminder hour, queue one digest per person who wants one and has something due."""
    zone = ZoneInfo(ctx.settings.effective_timezone)
    local = (now or datetime.now(tz=zone)).astimezone(zone)
    if local.hour < ctx.settings.reminder_hour:
        return 0
    today = local.date()
    queued = 0
    users = ctx.db.scalars(
        select(User).where(User.email_reminders.is_(True), User.email.is_not(None), User.disabled_at.is_(None))
    ).all()
    for user in users:
        key = f"due:{today.isoformat()}"
        sent = ctx.db.scalar(
            select(NotificationDelivery.id).where(
                NotificationDelivery.user_id == user.id,
                NotificationDelivery.channel == "email",
                NotificationDelivery.key == key,
            )
        )
        if sent is not None:
            continue
        if not due_for_user(ctx.db, user.id, today, roles=("owner", "manager")):
            continue
        if queue.enqueue(
            ctx.db,
            DIGEST_KIND,
            {"user_id": str(user.id), "date": today.isoformat()},
            dedupe_key=f"digest:{user.id}:{today}",
        ):
            queued += 1
    return queued


def _load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    from datetime import date

    user = ctx.db.get(User, uuid.UUID(payload["user_id"]))
    config = settings_store.email_config(ctx.db, ctx.settings)
    if user is None or not user.email or not user.email_reminders or not config.ready:
        return None
    items = due_for_user(ctx.db, user.id, date.fromisoformat(payload["date"]), roles=("owner", "manager"))
    if not items:
        return None
    subject, body = digest_text(user, items, config.public_url)
    return envelope(config, user.email, subject, body)


def _send(message: dict[str, Any]) -> dict[str, Any]:
    send(message)
    return {"ok": True}


def _store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    ctx.db.add(
        NotificationDelivery(
            user_id=uuid.UUID(payload["user_id"]), channel="email", key=f"due:{payload['date']}", status="sent"
        )
    )
    ctx.db.flush()
    log.info("email.digest.sent", user=payload["user_id"])


register(JobKind(DIGEST_KIND, _load, _send, _store, timeout=60.0, max_attempts=4))
