import asyncio
import io
import json
import os
import re
import shutil
import time
from pathlib import Path
from urllib import error, request

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    Image = None
    ImageFilter = None
    ImageOps = None


DATA_FILE = Path("lucky_spin_usage.json")
PENDING_ADMIN_CLAIMS_FILE = Path("pending_admin_claims.json")
ENV_FILE = Path(".env")
GUIDE_IMAGE_FILE = Path("images/panduan.jpg")
COOLDOWN_SECONDS = 24 * 60 * 60
STEP_USER_ID = "await_user_id"
STEP_ACCESS_CODE = "await_access_code"
STEP_PRIVATE_GET_CODE_USER_ID = "await_private_get_code_user_id"
BOT_GROUP_MENU_MESSAGES_KEY = "group_menu_message_ids"
PENDING_ADMIN_CLAIMS_KEY = "pending_admin_claims"
ADMIN_USERNAME = "horeg222"

CODES_TIER_5K = {
    "VSRYF2", "6F7QX6", "F3AXDW", "S8Q4L6", "M6E83K", "HCLENZ", "HY7CAC", "9DSLFY", "ZXYBTU", "GF9GHR",
    "KACT2M", "ES83VF", "NWERGS", "4YTXPS", "99H5XM", "HH7BU9", "AV2F8A", "6PWMRT", "VUDNQ3", "F35TZ5",
    "5H72ZU", "LRNFHX", "DPCBR2", "AL55GH", "3QCN54", "85F4Y3", "4KVT2X", "N6H8RY", "Q3MCW9", "W3RP4V",
    "VDJZK5", "QZ7ESF", "W5KGVC", "7M2NDY", "5JA3JR", "EYGC2K", "ML25PX", "GPPMCE", "8NRT3G", "T9GZ8K",
    "LC3H2N", "CATAVR", "4JY62W", "QP2WZY", "CNAUH4", "UKQ6TE", "CSLHKZ", "2PBF9Z", "KU3KJ8", "7L9AVA",
    "K6KREB", "8CK6X8", "R7RFK7", "TCZC8E", "4MSG4C", "S4ETWZ", "9RRQK7", "JYF9QV", "TX9BZX", "PUYE98",
    "JD3N4X", "8GQ7CW", "FSEFTR", "5GAUVD", "4XA6F3", "UGWG3Y", "FN979K", "MNZPFZ", "3FJN5M", "PG8D84",
    "D9T6ZE", "GSW472", "LNCGG8", "62GWCJ", "MUHFM7", "RV2JSL", "PNAZDM", "94LE2D", "WYR6AY", "NEMVYB",
    "GFE4HS", "RE2WPN", "UNADSD", "8KVZPN", "7L92HA", "MQHGRL", "EKZCDD", "W363LY", "A9SZ8U", "F23TN7",
    "NQG8NH", "8RM67S", "FD45T9", "9TGY56", "PF2VG6", "QWH74N", "UDFEXU", "8Z5E7N", "XVDR9L", "L7LT3C",
}

CODES_TIER_10K = {
    "32WECL", "A5VSPS", "Q4SRMV", "KAW3DM", "7MF444", "X9BUT7", "W2TKT6", "25F2GD", "BXEQZ4", "WWFB4B",
    "ZX5ZL2", "5WV7K8", "EB6JTS", "L9RPU3", "A4TE9B", "TDADVP", "G82ZMQ", "8KTSQU", "BCH46Z", "ZR2HMK",
    "CBTNLW", "77RRX8", "CWB84S", "RZ4CK5", "SVTK67", "7TJGMS", "XD6TY6", "KVMNA4", "X7NVRD", "D7W7RS",
    "5FBYQA", "GGMDFJ", "M2F7WN", "KQ7KSU", "WN7M4W", "4W8LNG", "NEZ9UJ", "H82EWF", "4237PF", "6HUXFZ",
    "BY86KR", "YR562D", "KN227Z", "JUBTZ5", "CG9E7E", "6QEVYV", "SKJM5E", "BDSKVJ", "4ZEAF3", "4GPXPN",
}

CODES_TIER_ZONK_FS = {
    "WG3JWZ", "T3R7P5", "8PMGZE", "KGA3NR", "3BMNB9", "UCL4DX", "6S76AD", "SRZPWC", "2MKYHF", "ZVJSRN",
    "9NVAH7", "J65XNT", "V8TNSW", "2574WW", "YPZU68", "RGCYWD", "CBNTNR", "YQ3AB4", "9Y7XJK", "MAP77J",
    "4B4SKU", "7MT6KC", "6V33GA", "M23BDJ", "N28L46", "9M64NZ", "B36SW9", "K935MP", "2686CM", "D7MK5Z",
    "MDYEQQ", "HK9ZGH", "5S4GMD", "T3JH47", "SPWFSH", "7VWHM9", "7XWS3T", "B4639C", "QGCVA2", "QKRZCK",
    "WDBE5D", "ZXVD68", "GUKA8E", "FVHT64", "R3BX7X", "SEHQR4", "HL26GP", "PJ6MTA", "CG8Q55", "ZAGLVV",
    "PLMAV8", "JSU9SH", "ENJX3K", "4HYMAA", "V4BV68", "ZDV6UN", "ULARR6", "6D8FSP", "JXLCWP", "JS3QTR",
    "G7CBJW", "DHZTL5", "DTAKXW", "6KRYLM", "J2N4ML", "TMRYHS", "ZZQ68U", "46UYDS", "Q6M4VB", "VNNP5G",
    "ELK3X2", "GET3AT", "FGBEUT", "HAWDLK", "AUE7MQ", "3WH67P", "DY4FB6", "Y5SP3F", "HME85N", "SE542H",
    "DQ4UPB", "DCE86M", "YT2UGF", "YMMLXK", "686GBK", "SETS6P", "CTKNVL", "FWLCNN", "G4QVYG", "NRG7NV",
    "4DN656", "SCC892", "MVVQVJ", "TNG9G3", "YV78DJ", "JMSMCV", "VASJUA", "P9TWP7", "YNUFE8", "U55BSQ",
    "YF5VYG", "YA4PDQ", "F6479R", "C3MRUM", "8JQSRE", "83D8YF", "CB4LDL", "A2T276", "593PW4", "S3EPV7",
    "SSTWKX", "CKGUF8", "6NYS9K", "TR5QXC", "NT4ZYA", "QC49AT", "6EMZAQ", "6H33YC", "X6VT8Q", "F57QRW",
    "H7JKXX", "S8FDF9", "VLXF5K", "DFV8BY", "5Q85PP", "5CGX2E", "8TPYBN", "SYTLQB", "PCDJW7", "NZLYTR",
    "AGFSL3", "EJFY7Z", "4G4H65", "826QSA", "6ETF3W", "Y3GJYT", "BUH9K4", "6HS4VB", "7KFHFN", "CMNCQT",
    "73K68M", "VZAUDS", "GNN45H", "D3AMM9", "544D72", "Z63B9E", "BCWZT3", "NVQATD", "JAWD75", "3RHC47",
    "B24HJL", "DJRG4R", "7UBD7N", "9T8N7N", "UUCENM", "C3RYKY", "R9GDFZ", "2AQTV5", "5YVUDS", "FX3EZR",
    "CLFA56", "YCUPUH", "R9VWD2", "ZZEXHY", "33LQ7B", "F55VAE", "F7HV7B", "59MJDX", "ZT4LPP", "Y5G6T3",
    "X68LGR", "5P282B", "WUDF22", "MP6RDJ", "NWGU88", "QLW5YM", "LR5EGG", "SCNQ5Y", "6UYMHJ", "GYGT3T",
    "PWGECX", "R55E9J", "7WGJMZ", "TPL8RZ", "Z3AXNZ", "Y9LWAZ", "KUBCJP", "RKB2YL", "473QBP", "3WGE9E",
    "YM8XNM", "J6MX7E", "HQMFQR", "KSYCUZ", "YRNG7P", "CQPT32", "VCKCZ3", "46GUJM", "B5GAWL", "4VFN8R",
    "A72GSG", "TD6JWZ", "3PWE3X", "3ZWKVB", "3GKDD5", "ANHMM8", "4XUXUG", "WF2A48", "9FG3VK", "DDR27X",
    "7RBFCD", "RS5HU2", "NVDSDS", "8TX39V", "4RKGQR", "W5HBAC", "DXBC7Q", "5TBQZS", "X5CGS4", "J6387M",
    "M9QSRD", "SBTABC", "5WFT9T", "PTATTD", "TSSE7C", "JE2BVX", "WSFKB4", "5FH74Y", "GM5VNE", "LL8FRA",
    "6LFLU7", "U338S8", "H9QE85", "AGE4QP", "8R3H99", "32764L", "NL382Y", "36VHQB", "2FSBM6", "TN2K2B",
    "V9BCA7", "66SUBT", "4GMCPF", "QZT78B", "LA4L2C", "2QJVTS", "BMBVF4", "3QAXCL", "BSS45V", "68Q56N",
}

VALID_CODES = CODES_TIER_5K | CODES_TIER_10K | CODES_TIER_ZONK_FS
TRIGGER_KEYWORDS = (
    "luckyspin",
    "lucky spin",
    "klaim spin",
    "klaim luckyspin",
    "kode akses",
)

APPS_SCRIPT_TIMEOUT_SECONDS = 10
SPIN_RESULT_UNKNOWN = "UNKNOWN"
SPIN_RESULT_5K = "RP5000"
SPIN_RESULT_10K = "RP10000"
SPIN_RESULT_FREE_SPIN = "FREESPIN"
SPIN_RESULT_ZONK = "ZONK"


def load_dotenv(env_path: Path = ENV_FILE) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def claim_code_from_apps_script(user_id: str, tele_id: str) -> dict:
    script_url = os.getenv("GOOGLE_SCRIPT_URL", "").strip()
    if not script_url:
        raise RuntimeError("GOOGLE_SCRIPT_URL belum diatur di file .env.")

    payload = json.dumps(
        {
            "action": "claim_code",
            "user_id": user_id,
            "tele_id": tele_id,
        }
    ).encode("utf-8")

    req = request.Request(
        script_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=APPS_SCRIPT_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gagal terhubung ke Apps Script: {exc.reason}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Respons Apps Script tidak valid: {body}") from exc

    if not isinstance(data, dict):
        raise RuntimeError("Respons Apps Script bukan objek JSON yang valid.")

    return data


def normalize_ocr_text(text: str) -> str:
    normalized = text.upper()
    normalized = normalized.replace("O", "0")
    normalized = normalized.replace(",", ".")
    normalized = re.sub(r"[^A-Z0-9.\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def classify_spin_result_from_text(text: str) -> str:
    normalized = normalize_ocr_text(text)

    if not normalized:
        return SPIN_RESULT_UNKNOWN

    if "FREE SPIN" in normalized or "FREESPIN" in normalized:
        return SPIN_RESULT_FREE_SPIN

    if "ZONK" in normalized:
        return SPIN_RESULT_ZONK

    patterns_10k = (
        "RP 10.000",
        "RP10.000",
        "RP 10000",
        "RP10000",
        "10.000",
        "10000",
    )
    if any(pattern in normalized for pattern in patterns_10k):
        return SPIN_RESULT_10K

    patterns_5k = (
        "RP 5.000",
        "RP5.000",
        "RP 5000",
        "RP5000",
        "5.000",
        "5000",
    )
    if any(pattern in normalized for pattern in patterns_5k):
        return SPIN_RESULT_5K

    return SPIN_RESULT_UNKNOWN


def detect_spin_result_from_image(image_bytes: bytes) -> str:
    if pytesseract is None or Image is None or ImageOps is None or ImageFilter is None:
        raise RuntimeError("Library OCR lokal belum terpasang.")

    tesseract_cmd = resolve_tesseract_cmd()
    if not tesseract_cmd:
        raise RuntimeError("Engine Tesseract belum ditemukan di server.")
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            grayscale = ImageOps.grayscale(image)
            resampling = getattr(Image, "Resampling", Image)
            enlarged = grayscale.resize(
                (grayscale.width * 2, grayscale.height * 2),
                resampling.LANCZOS,
            )
            sharpened = enlarged.filter(ImageFilter.SHARPEN)
            thresholded = sharpened.point(lambda value: 255 if value > 160 else 0)
            extracted_text = pytesseract.image_to_string(thresholded, config="--psm 6")
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Engine Tesseract belum terpasang di server.") from exc
    except Exception as exc:
        raise RuntimeError(f"Gagal memproses gambar OCR: {exc}") from exc

    return classify_spin_result_from_text(extracted_text)


def resolve_tesseract_cmd() -> str | None:
    configured = os.getenv("TESSERACT_CMD", "").strip()
    if configured and Path(configured).exists():
        return configured

    discovered = shutil.which("tesseract")
    if discovered:
        return discovered

    windows_candidates = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    )
    for candidate in windows_candidates:
        if Path(candidate).exists():
            return candidate

    return None


def get_spin_result_reply(result: str) -> str:
    if result == SPIN_RESULT_5K:
        return (
            "Selamat ya kamu mendapatkan Hadiah 5000 dari lucky spin\n"
            "Silakan tunggu proses pengecekan admin.\n\n"
            "Jika ada kendala, hubungi admin @horeg222"
        )
    if result == SPIN_RESULT_10K:
        return (
            "Selamat ya kamu mendapatkan Hadiah 10000 dari lucky spin\n"
            "Silakan tunggu proses pengecekan admin.\n\n"
            "Jika ada kendala, hubungi admin @horeg222"
        )
    if result == SPIN_RESULT_FREE_SPIN:
        return (
            "Free Spin\n\n"
            "Kamu mendapatkan kesempatan spin ulang.\n"
            "Silakan lanjutkan Lucky Spin kamu dan kirim lagi hasil terbarunya di chat ini."
        )
    if result == SPIN_RESULT_ZONK:
        return (
            "Zonk\n\n"
            "Maaf, hasil ini belum mendapatkan hadiah yang bisa diklaim.\n"
            "Silakan coba lagi di kesempatan berikutnya."
        )
    return (
        "Berikan Screenshot dari Hasil Lucky Spin yang kamu dapatkan.\n\n"
        "Pastikan gambar tidak blur, tidak terpotong, dan tulisan hadiah terlihat jelas.\n"
        "Lalu kirim ulang screenshot hasil Lucky Spin kamu di chat ini."
    )


def load_usage_data() -> dict:
    if not DATA_FILE.exists():
        return {}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_usage_data(data: dict) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_pending_admin_claims() -> dict:
    if not PENDING_ADMIN_CLAIMS_FILE.exists():
        return {}

    try:
        with PENDING_ADMIN_CLAIMS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_pending_admin_claims(data: dict) -> None:
    with PENDING_ADMIN_CLAIMS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def cleanup_expired_codes(data: dict) -> dict:
    now = int(time.time())
    cleaned = {
        code: used_at
        for code, used_at in data.items()
        if now - int(used_at) < COOLDOWN_SECONDS
    }
    if cleaned != data:
        save_usage_data(cleaned)
    return cleaned


def format_remaining(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_code_tier(code: str) -> str | None:
    if code in CODES_TIER_5K:
        return "tier5k"
    if code in CODES_TIER_10K:
        return "tier10k"
    if code in CODES_TIER_ZONK_FS:
        return "tierzonk"
    return None


def get_private_chat_url(bot_username: str | None, action: str = "menu") -> str | None:
    if not bot_username:
        return None
    return f"https://t.me/{bot_username}?start={action}"


def build_group_menu(bot_username: str | None = None) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Klaim Lucky Spin", callback_data="claim_spin")],
        [InlineKeyboardButton("Ambil Kode Akses", callback_data="group_get_code")],
        [
            InlineKeyboardButton("Login", url="https://www.horeg22.net/login"),
            InlineKeyboardButton("Daftar", url="https://www.horeg22.net/register"),
        ],
        [InlineKeyboardButton("Buka Halaman Lucky Spin", url="https://lckyspn.netlify.app/")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_private_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Buka Halaman Lucky Spin", url="https://lckyspn.netlify.app/")],
        [InlineKeyboardButton("Panduan Lucky Spin", callback_data="guide_spin")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reward_claim_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Cek akun Sekarang", url="https://horeg22.net/login")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_group_private_redirect_menu(bot_username: str | None = None) -> InlineKeyboardMarkup:
    private_chat_url = get_private_chat_url(bot_username, "getkode")
    keyboard = [
        [InlineKeyboardButton("Buka Private Chat Bot", url=private_chat_url or "https://lckyspn.netlify.app/")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_after_validation_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Buka Lucky Spin", url="https://lckyspn.netlify.app/")],
        [InlineKeyboardButton("Klaim Lagi", callback_data="claim_spin")],
        [InlineKeyboardButton("Panduan Klaim", callback_data="guide_spin")],
    ]
    return InlineKeyboardMarkup(keyboard)


def reset_user_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("step", None)
    context.user_data.pop("claim_user_id", None)


def get_group_menu_store(context: ContextTypes.DEFAULT_TYPE) -> dict:
    store = context.bot_data.get(BOT_GROUP_MENU_MESSAGES_KEY)
    if not isinstance(store, dict):
        store = {}
        context.bot_data[BOT_GROUP_MENU_MESSAGES_KEY] = store
    return store


def get_pending_admin_claims_store(context: ContextTypes.DEFAULT_TYPE | None = None) -> dict:
    data = load_pending_admin_claims()
    if context is not None:
        context.bot_data[PENDING_ADMIN_CLAIMS_KEY] = data
    return data


def remember_group_menu_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
    store = get_group_menu_store(context)
    message_ids = store.get(chat_id)
    if not isinstance(message_ids, list):
        message_ids = []
        store[chat_id] = message_ids
    if message_id not in message_ids:
        message_ids.append(message_id)


def remember_group_bot_message(context: ContextTypes.DEFAULT_TYPE, message) -> None:
    if not message or not getattr(message, "chat", None):
        return

    if message.chat.type == "private":
        return

    remember_group_menu_message(context, message.chat_id, message.message_id)


async def send_group_reply_text(
    target_message,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    parse_mode: str | None = None,
):
    sent_message = await target_message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    remember_group_bot_message(context, sent_message)
    return sent_message


async def send_group_menu_message(target_message, context: ContextTypes.DEFAULT_TYPE, text: str):
    sent_message = await send_group_reply_text(
        target_message,
        context,
        text,
        reply_markup=build_group_menu(context.bot.username),
    )
    return sent_message


def get_tier_message(tier: str) -> str:
    if tier == "tier5k":
        return "Kode valid. Tier hadiah kamu mengarah ke hadiah Rp 5.000."
    if tier == "tier10k":
        return "Kode valid. Tier hadiah kamu bisa mengarah ke Rp 5.000 atau Rp 10.000."
    if tier == "tierzonk":
        return "Kode valid. Tier ini hanya mengarah ke ZONK atau Free Spin."
    return "Kode valid."


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        text = f"Halo {member.first_name} Selamat Bergabung di Group Horeg22 Official, semoga nyaman yaa !! Ada Bonus Lucky Spin nih, Yuk ambil sekarang !!"
        await send_group_menu_message(update.message, context, text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if args and args[0] == "getkode":
        await begin_private_get_code_flow(update, context)
        return

    if update.effective_chat and update.effective_chat.type == "private":
        reset_user_state(context)
        await update.message.reply_text(
            "Halo, saya Taro Admin.\n\n"
            "Kirim User ID kamu untuk ambil kode akses Lucky Spin.\n"
            "Contoh User ID: User1234"
        )
        context.user_data["step"] = STEP_PRIVATE_GET_CODE_USER_ID
        return

    await spin(update, context)


async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reset_user_state(context)
    text = (
        "Halo, saya Taro Admin.\n\n"
        "Pilih menu di bawah untuk ambil kode akses atau lanjut klaim Lucky Spin."
    )
    await send_group_menu_message(update.message, context, text)


async def begin_private_get_code_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    reset_user_state(context)
    context.user_data["step"] = STEP_PRIVATE_GET_CODE_USER_ID
    await update.message.reply_text(
        "Di bantu berikan User ID-nya ya bosku.\n"
        "Contoh User ID: User1234"
    )


async def begin_claim_flow(target_message, context: ContextTypes.DEFAULT_TYPE) -> None:
    reset_user_state(context)
    await send_group_menu_message(
        target_message,
        context,
        "Lucky Spin dapat Di klaim 1 kali dalam 1 hari, Jika kamu belum ada Klaim Lucky Spin nya langsung klik menu Ambil kode akses ya !",
    )


async def show_guide(target_message, context: ContextTypes.DEFAULT_TYPE) -> None:
    guide_text = (
        "Panduan klaim Lucky Spin:\n"
        "1. Salin Kode akses yang telah di berikan.\n"
        "2. Buka halaman Lcuky Spin.\n"
        "3. Pada Kolom input USER ID kamu masukan user id atau username.\n"
        "4. Pada kolom input Kode Akses kamu masukan Kode Akses tadi yang telah kamu salin.\n"
        "5. Setleh semua sudah cocok, klik Tombol Lanjutkan.\n"
        "6. Setelah nya Kamu sudah bisa melakukan SPIN, Dan Screenshot hasil yang di dapat.\n"
        "7. Selamat mencoba semoga beruntung ya!! ."
    )

    if target_message.chat.type == "private" and GUIDE_IMAGE_FILE.exists():
        with GUIDE_IMAGE_FILE.open("rb") as photo:
            await target_message.reply_photo(
                photo=photo,
                caption=guide_text,
                reply_markup=build_private_menu(),
            )
        return

    await send_group_menu_message(target_message, context, guide_text)


async def delete_message_safe(message) -> None:
    if not message:
        return

    try:
        await message.delete()
    except Exception:
        pass


async def delete_message_after_delay(message, delay_seconds: int) -> None:
    await asyncio.sleep(delay_seconds)
    await delete_message_safe(message)


def get_reward_amount_label(result: str) -> str | None:
    if result == SPIN_RESULT_5K:
        return "5.000"
    if result == SPIN_RESULT_10K:
        return "10.000"
    return None


def normalize_reward_amount_text(raw_amount: str) -> str:
    digits = re.sub(r"\D", "", raw_amount)
    if not digits:
        return raw_amount.strip()

    reversed_digits = digits[::-1]
    grouped = [reversed_digits[index:index + 3] for index in range(0, len(reversed_digits), 3)]
    return ".".join(part[::-1] for part in grouped[::-1])


def extract_reward_amount_from_text(text: str) -> str | None:
    lowered = text.lower()
    compact = lowered.replace(" ", "")

    known_amount_patterns = (
        ("10.000", ("10000", "10.000", "10,000")),
        ("5.000", ("5000", "5.000", "5,000")),
    )
    for normalized, patterns in known_amount_patterns:
        if any(pattern in compact for pattern in patterns):
            return normalized

    amount_match = re.search(r"(?:rp\s*)?(\d{4,9}(?:[.,]\d{3})*)", lowered)
    if amount_match:
        return normalize_reward_amount_text(amount_match.group(1))

    return None


async def notify_admin_claim(
    context: ContextTypes.DEFAULT_TYPE,
    member_chat_id: int,
    member_user_id: str,
    reward_result: str,
) -> bool:
    reward_amount = get_reward_amount_label(reward_result)
    if not reward_amount:
        return False

    admin_target = os.getenv("ADMIN_CHAT_ID", "").strip() or f"@{os.getenv('ADMIN_USERNAME', ADMIN_USERNAME).lstrip('@')}"
    admin_message = await context.bot.send_message(
        chat_id=admin_target,
        text=(
            f"User id : {member_user_id}\n"
            f"Klaim bonus lucky spin {reward_amount}"
        ),
    )

    pending_claims = get_pending_admin_claims_store(context)
    pending_claims[str(admin_message.message_id)] = {
        "member_chat_id": member_chat_id,
        "member_user_id": member_user_id,
    }
    save_pending_admin_claims(pending_claims)
    return True


async def notify_admin_claim_by_amount(
    context: ContextTypes.DEFAULT_TYPE,
    member_chat_id: int,
    member_user_id: str,
    reward_amount: str,
) -> bool:
    normalized_amount = normalize_reward_amount_text(reward_amount)
    if not normalized_amount:
        return False

    admin_target = os.getenv("ADMIN_CHAT_ID", "").strip() or f"@{os.getenv('ADMIN_USERNAME', ADMIN_USERNAME).lstrip('@')}"
    admin_message = await context.bot.send_message(
        chat_id=admin_target,
        text=(
            f"User id : {member_user_id}\n"
            f"Klaim bonus lucky spin {normalized_amount}"
        ),
    )

    pending_claims = get_pending_admin_claims_store(context)
    pending_claims[str(admin_message.message_id)] = {
        "member_chat_id": member_chat_id,
        "member_user_id": member_user_id,
    }
    save_pending_admin_claims(pending_claims)
    return True


async def handle_private_reward_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.message or not update.message.text or not update.effective_chat:
        return False

    if update.effective_chat.type != "private":
        return False

    validated_user_id = str(context.user_data.get("validated_user_id", "")).strip()
    if not validated_user_id:
        return False

    text = update.message.text.strip()
    lowered = text.lower()

    forgot_patterns = (
        "lupa screenshot",
        "lupa screenshoot",
        "lupa ss",
        "ga sempet ss",
        "gak sempet ss",
        "tidak sempat ss",
        "nggak sempet ss",
    )
    if any(pattern in lowered for pattern in forgot_patterns):
        await update.message.reply_text(
            "Jika kamu lupa screenshot, maka bonus lucky spin hangus ya!!\n\n"
            "Kamu mendapatkan hadiah berapa ya ?"
        )
        return True

    reward_amount = extract_reward_amount_from_text(lowered)
    if reward_amount:
        try:
            await notify_admin_claim_by_amount(
                context=context,
                member_chat_id=update.effective_chat.id,
                member_user_id=validated_user_id,
                reward_amount=reward_amount,
            )
        except Exception as exc:
            print(f"Gagal mengirim notifikasi klaim teks ke admin: {exc}")
            await update.message.reply_text(
                "Hadiah kamu belum bisa saya teruskan ke admin. Coba kirim lagi nominal hadiahnya beberapa saat lagi."
            )
            return True

        await update.message.reply_text(
            "Untuk Selanjutnya nanti kamu jangan lupa Screenshot hasil lucky spin nya ya !\n"
            "Hadiah kamu saya bantu proseskan, mohon di tunggu !!",
            reply_markup=build_reward_claim_menu(),
        )
        return True

    if any(keyword in lowered for keyword in ("hadiah", "bonus", "spin", "ss", "screenshot", "screenshoot")):
        await update.message.reply_text(
            "Kalau hasil Lucky Spin kamu sudah keluar, kirim screenshot-nya di chat ini ya.\n"
            "Kalau kamu lupa screenshot, kasih tahu hadiah yang kamu dapat biar saya cek bantu proses."
        )
        return True

    return False


async def handle_admin_done_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.message or not update.message.text or not update.effective_chat or not update.effective_user:
        return False

    if update.effective_chat.type != "private":
        return False

    incoming_text = update.message.text.strip().lower()
    if incoming_text != "done":
        return False

    admin_username = (update.effective_user.username or "").lower()
    expected_admin = os.getenv("ADMIN_USERNAME", ADMIN_USERNAME).lstrip("@").lower()
    admin_chat_id = os.getenv("ADMIN_CHAT_ID", "").strip()
    is_admin_by_username = admin_username == expected_admin if expected_admin else False
    is_admin_by_chat_id = admin_chat_id and str(update.effective_chat.id) == admin_chat_id
    if not is_admin_by_username and not is_admin_by_chat_id:
        return False

    if not update.message.reply_to_message:
        await update.message.reply_text("Balas pesan klaim admin dengan teks Done.")
        return True

    pending_claims = get_pending_admin_claims_store(context)
    claim_key = None
    reply_key = str(update.message.reply_to_message.message_id)
    if reply_key in pending_claims:
        claim_key = reply_key

    if not claim_key:
        await update.message.reply_text("Pesan klaim tidak ditemukan. Balas langsung pesan klaim yang benar dengan teks Done.")
        return True

    claim_data = pending_claims.pop(claim_key, None)
    save_pending_admin_claims(pending_claims)
    if not isinstance(claim_data, dict):
        await update.message.reply_text("Pesan klaim tidak ditemukan atau sudah diproses.")
        return True

    member_chat_id = claim_data.get("member_chat_id")
    member_user_id = str(claim_data.get("member_user_id", "")).strip() or "member"
    if not member_chat_id:
        await update.message.reply_text("Data member untuk klaim ini tidak valid.")
        return True

    await context.bot.send_message(
        chat_id=member_chat_id,
        text=f"Hadiah Lucky Spin {member_user_id} kamu telah di proseskan ya!!",
        reply_markup=build_reward_claim_menu(),
    )
    await update.message.reply_text("Konfirmasi ke member berhasil dikirim.")
    return True


async def clear_group_lucky_spin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text("Perintah ini hanya bisa dipakai di grup.")
        return

    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    except Exception:
        await send_group_reply_text(update.message, context, "Gagal cek status admin grup.")
        return

    if member.status not in {"administrator", "creator"}:
        await send_group_reply_text(update.message, context, "Perintah /hapus hanya bisa dipakai admin grup.")
        return

    store = get_group_menu_store(context)
    message_ids = list(store.get(update.effective_chat.id, []))
    deleted_count = 0

    for message_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
            deleted_count += 1
        except Exception:
            pass

    store[update.effective_chat.id] = []

    try:
        await update.message.delete()
    except Exception:
        pass

    confirmation = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Pesan bot berhasil dihapus: {deleted_count}",
    )
    context.application.create_task(delete_message_after_delay(confirmation, 10))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if query.data == "claim_spin":
        await begin_claim_flow(query.message, context)
        return

    if query.data == "group_get_code":
        redirect_message = None
        if query.message:
            store = get_group_menu_store(context)
            tracked_ids = store.get(query.message.chat_id, [])
            if query.message.message_id in tracked_ids:
                store[query.message.chat_id] = [mid for mid in tracked_ids if mid != query.message.message_id]
            redirect_message = await send_group_reply_text(
                query.message,
                context,
                "Lanjut ambil kode akses di private chat ya bosku.",
                reply_markup=build_group_private_redirect_menu(context.bot.username),
            )
            await delete_message_safe(query.message)

        if redirect_message:
            context.application.create_task(delete_message_after_delay(redirect_message, 15))
        return

    if query.data == "guide_spin":
        await show_guide(query.message, context)
        return


async def handle_private_spin_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return

    if not update.effective_chat or update.effective_chat.type != "private":
        return

    try:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        image_bytes = bytes(await photo_file.download_as_bytearray())
        result = detect_spin_result_from_image(image_bytes=image_bytes)
    except RuntimeError as exc:
        print(f"Gagal membaca screenshot Lucky Spin: {exc}")
        await update.message.reply_text(
            "Pemeriksaan screenshot Lucky Spin belum siap di server. Pastikan OCR lokal sudah terpasang, lalu coba lagi."
        )
        return
    except Exception as exc:
        print(f"Error tak terduga saat membaca screenshot Lucky Spin: {exc}")
        await update.message.reply_text(
            "Screenshot belum bisa diproses. Coba kirim ulang gambar yang jelas."
        )
        return

    stored_user_id = str(context.user_data.get("validated_user_id", "")).strip()
    fallback_user_id = ""
    if update.effective_user and update.effective_user.username:
        fallback_user_id = update.effective_user.username
    member_user_id = stored_user_id or fallback_user_id or "member"

    if get_reward_amount_label(result):
        try:
            await notify_admin_claim(
                context=context,
                member_chat_id=update.effective_chat.id,
                member_user_id=member_user_id,
                reward_result=result,
            )
        except Exception as exc:
            print(f"Gagal mengirim notifikasi klaim ke admin: {exc}")
            await update.message.reply_text(
                "Klaim hadiah belum bisa diteruskan ke admin. Coba lagi beberapa saat."
            )
            return

    await update.message.reply_text(
        get_spin_result_reply(result),
        reply_markup=build_reward_claim_menu() if get_reward_amount_label(result) else build_private_menu(),
    )


async def handle_claim_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.message or not update.message.text:
        return False

    step = context.user_data.get("step")
    if not step:
        return False

    text = update.message.text.strip()

    if step == STEP_PRIVATE_GET_CODE_USER_ID:
        user_id = text
        if len(user_id) < 3:
            await update.message.reply_text("User ID minimal 3 karakter. Kirim ulang User ID yang valid.")
            return True

        try:
            result = claim_code_from_apps_script(
                user_id=user_id,
                tele_id=str(update.effective_user.id) if update.effective_user else "",
            )
        except RuntimeError as exc:
            reset_user_state(context)
            print(f"Gagal claim kode via Apps Script: {exc}")
            await update.message.reply_text(
                "Sistem kode akses sedang bermasalah. Coba lagi beberapa saat."
            )
            return True

        reset_user_state(context)

        if result.get("ok"):
            data = result.get("data", {})
            code = str(data.get("kode", "")).strip().upper()
            context.user_data["validated_user_id"] = user_id
            await update.message.reply_text(
                "Kode akses Lucky Spin kamu:\n\n"
                f"`{code}`\n\n"
                "Simpan kode akses kamu dan lanjutkan pilih menu di bawah ini untuk melanjutkan memutar Lucky Spin nya.",
                parse_mode="Markdown",
                reply_markup=build_private_menu(),
            )
            return True

        status = str(result.get("status", "")).strip().lower()
        message = str(result.get("message", "")).strip() or "Kode akses tidak bisa diproses."
        if status == "already_claimed":
            await update.message.reply_text(message)
            return True

        await update.message.reply_text(message)
        return True

    if step == STEP_USER_ID:
        if len(text) < 3:
            await update.message.reply_text("User ID minimal 3 karakter. Kirim ulang User ID yang valid.")
            return True

        context.user_data["claim_user_id"] = text
        context.user_data["step"] = STEP_ACCESS_CODE
        await update.message.reply_text(
            "Sekarang kirim Kode Akses Lucky Spin yang kamu terima di chat pribadi.\n"
            "Format huruf kecil atau besar tetap akan saya baca otomatis."
        )
        return True

    if step == STEP_ACCESS_CODE:
        code = text.upper()
        user_id = context.user_data.get("claim_user_id", "-")

        if code not in VALID_CODES:
            await update.message.reply_text(
                "Kode akses tidak valid.\n"
                "Ketik /spin lalu ulangi proses klaim."
            )
            reset_user_state(context)
            return True

        usage_data = cleanup_expired_codes(load_usage_data())
        used_at = usage_data.get(code)
        now = int(time.time())

        if used_at:
            remaining = COOLDOWN_SECONDS - (now - int(used_at))
            if remaining > 0:
                await update.message.reply_text(
                    "Kode ini masih cooldown.\n"
                    f"Coba lagi dalam {format_remaining(remaining)}."
                )
                reset_user_state(context)
                return True

        usage_data[code] = now
        save_usage_data(usage_data)

        tier = get_code_tier(code)
        context.user_data["validated_user_id"] = user_id
        context.user_data["validated_code"] = code
        context.user_data["validated_tier"] = tier
        reset_user_state(context)

        await update.message.reply_text(
            "Validasi berhasil.\n\n"
            f"User ID: {user_id}\n"
            f"Kode: {code}\n"
            f"{get_tier_message(tier)}\n\n"
            "Lanjut buka halaman Lucky Spin, lakukan spin, lalu screenshot hasilnya setelah selesai.",
            reply_markup=build_after_validation_menu(),
        )
        return True

    return False


async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_done_handled = await handle_admin_done_reply(update, context)
    if admin_done_handled:
        return

    handled = await handle_claim_input(update, context)
    if handled or not update.message or not update.message.text:
        return

    text = update.message.text.lower()

    if update.effective_chat and update.effective_chat.type == "private":
        reward_text_handled = await handle_private_reward_text(update, context)
        if reward_text_handled:
            return

        if "kode akses" in text:
            await begin_private_get_code_flow(update, context)
        return

    if not any(keyword in text for keyword in TRIGGER_KEYWORDS):
        return

    if not update.effective_chat:
        return

    if "spin" in text or "klaim" in text:
        await send_group_reply_text(
            update.message,
            context,
            "Untuk mulai Lucky Spin, ketik /spin lalu pilih 'Ambil Kode Akses' atau 'Klaim Lucky Spin'."
        )
    elif "kode" in text:
        await send_group_reply_text(
            update.message,
            context,
            "Ketik /spin lalu tekan tombol 'Ambil Kode Akses'. Bot akan membuka chat pribadi untuk meminta User ID."
        )
    elif "login" in text:
        await send_group_reply_text(update.message, context, "Login: https://www.horeg22.net/login")
    elif "daftar" in text or "register" in text:
        await send_group_reply_text(update.message, context, "Daftar: https://www.horeg22.net/register")
    else:
        await send_group_reply_text(
            update.message,
            context,
            "Taro admin fokus untuk Lucky Spin. Ketik /spin untuk membuka menu klaim."
        )


async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    allowed_domains = (
        "lckyspn.netlify.app",
        "horeg22.net",
    )
    if "http" in text and not any(domain in text for domain in allowed_domains):
        try:
            await update.message.delete()
        except Exception:
            pass


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN belum diatur. Isi file .env dengan BOT_TOKEN Telegram bot.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hapus", clear_group_lucky_spin_messages))
    app.add_handler(CommandHandler("spin", spin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_private_spin_screenshot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))
    app.add_handler(MessageHandler(filters.TEXT, anti_spam))

    print("Bot Lucky Spin berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
