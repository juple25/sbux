import logging
import os
import re
import requests # Ditambahkan untuk permintaan HTTP
from bs4 import BeautifulSoup # Ditambahkan untuk parsing HTML
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Mengaktifkan logging untuk melihat aktivitas bot
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
# Mengatur level logging yang lebih tinggi untuk httpx agar tidak terlalu banyak log request
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Mendefinisikan status (states) untuk ConversationHandler
ENTER_CUSTOMER_CODE, AUTOMATE_SURVEY_STEPS, ENTER_MESSAGE, DISPLAY_PROMO = range(4) # Status disederhanakan

# --- Konfigurasi ---
# Mendapatkan token bot dari variabel lingkungan untuk keamanan.
# PASTIKAN Anda mengatur variabel lingkungan TELEGRAM_BOT_TOKEN di Render!
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("Variabel lingkungan TELEGRAM_BOT_TOKEN tidak diatur. Bot tidak dapat dimulai.")
    exit(1) # Keluar jika token tidak diatur

# URL survei Starbucks
STARBUCKS_SURVEY_URL = "https://www.mystarbucksvisit.com/websurvey/2/execute?_g=NTAyMA%3D%3Dh&_s2=7e892124-f2b8-4823-8088-a5f0eb4afc44#!/1"

# --- Handler Perintah ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mengirim pesan selamat datang dan memulai proses survei."""
    await update.message.reply_text(
        "Halo! Saya bot untuk membantu Anda mengisi survei Starbucks.\n"
        "Silakan mulai dengan mengunjungi tautan survei ini di browser Anda untuk memastikan berfungsi:\n"
        f"{STARBUCKS_SURVEY_URL}\n\n"
        "Setelah itu, silakan masukkan kode pelanggan Anda (biasanya 16 digit, ditemukan di struk):\n"
        "Contoh: `1234567890123456`"
    )
    # Mengarahkan percakapan ke status ENTER_CUSTOMER_CODE
    return ENTER_CUSTOMER_CODE

# --- Fungsi Otomatisasi Web (Eksperimental) ---
async def automate_survey_steps(session: requests.Session, url: str, customer_code: str, user_message: str = None) -> str:
    """
    Mencoba mengotomatiskan langkah-langkah survei Starbucks.
    Ini adalah fungsi eksperimental dan mungkin tidak berfungsi jika situs web memiliki anti-bot.
    """
    try:
        # Langkah 1: Akses halaman awal dan pilih Bahasa Indonesia
        logger.info(f"Mengakses URL survei: {url}")
        response = session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Cari tombol "Bahasa Indonesia" dan klik (simulasi)
        # Asumsi: Ada link atau form yang mengarahkan ke bahasa Indonesia
        # Ini adalah bagian yang paling mungkin perlu disesuaikan.
        # Contoh sederhana: mencari link dengan teks "Bahasa Indonesia"
        # Atau form dengan input tersembunyi untuk bahasa.
        # Untuk survei ini, URL sudah mengarahkan ke survei, jadi pemilihan bahasa mungkin terjadi di awal.
        # Jika ada tombol eksplisit:
        # indo_button = soup.find('button', string='BAHASA INDONESIA')
        # if indo_button and indo_button.form:
        #     form_data = {input.get('name'): input.get('value') for input in indo_button.form.find_all('input')}
        #     response = session.post(indo_button.form.get('action'), data=form_data)
        #     soup = BeautifulSoup(response.text, 'html.parser')
        # else:
        #     logger.warning("Tombol 'Bahasa Indonesia' tidak ditemukan atau tidak memiliki form. Melanjutkan.")

        # Langkah 2: Masukkan kode pelanggan
        # Cari form yang berisi input kode pelanggan
        # Asumsi: input memiliki name 'CustomerCode' atau 'kodePelanggan'
        form = soup.find('form') # Cari form pertama atau yang relevan
        if not form:
            raise ValueError("Form survei tidak ditemukan di halaman awal.")

        # Ekstrak semua input tersembunyi (hidden inputs) dari form
        form_data = {}
        for input_tag in form.find_all('input', type='hidden'):
            if input_tag.get('name'):
                form_data[input_tag.get('name')] = input_tag.get('value')

        # Tambahkan kode pelanggan
        # Asumsi nama input untuk kode pelanggan adalah 'CustomerCode' atau 'kodePelanggan'
        # Anda mungkin perlu menyesuaikan ini berdasarkan inspeksi HTML survei
        form_data['CustomerCode'] = customer_code # Coba nama ini
        # form_data['kodePelanggan'] = customer_code # Atau nama ini

        # Cari action URL untuk form
        form_action = form.get('action') or response.url # Gunakan URL saat ini jika action tidak ada
        if not form_action.startswith('http'): # Handle relative paths
            form_action = response.url.split('?')[0].rsplit('/', 1)[0] + '/' + form_action

        logger.info(f"Mengirim kode pelanggan ke: {form_action} dengan data: {form_data}")
        response = session.post(form_action, data=form_data)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Langkah 3: Pilih "Membeli dan langsung pergi" & "Ya"
        # Asumsi: Radio button untuk jenis kunjungan memiliki name 'VisitType' atau 'Q1'
        # Asumsi: Radio button untuk makanan memiliki name 'FoodOrdered' atau 'Q2'
        # Asumsi: Value untuk "Membeli dan langsung pergi" adalah 'TakeAway' atau '1'
        # Asumsi: Value untuk "Ya" adalah 'Yes' atau '1'
        
        # Cari form berikutnya
        form = soup.find('form')
        if not form:
            raise ValueError("Form jenis kunjungan tidak ditemukan.")

        form_data = {}
        for input_tag in form.find_all('input', type='hidden'):
            if input_tag.get('name'):
                form_data[input_tag.get('name')] = input_tag.get('value')

        # Coba mengisi pilihan
        form_data['VisitType'] = 'TakeAway' # Asumsi nama input dan value
        form_data['FoodOrdered'] = 'Yes' # Asumsi nama input dan value
        # Anda mungkin perlu menyesuaikan ini:
        # form_data['Q1'] = '1' # Contoh lain
        # form_data['Q2'] = '1' # Contoh lain

        form_action = form.get('action') or response.url
        if not form_action.startswith('http'):
            form_action = response.url.split('?')[0].rsplit('/', 1)[0] + '/' + form_action

        logger.info(f"Mengirim pilihan kunjungan/makanan ke: {form_action}")
        response = session.post(form_action, data=form_data)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Langkah 4: Pilih "Hari ini atau besok"
        # Asumsi: Radio button untuk waktu kembali memiliki name 'ReturnTime' atau 'Q3'
        # Asumsi: Value untuk "Hari ini atau besok" adalah 'TodayTomorrow' atau '1'

        form = soup.find('form')
        if not form:
            raise ValueError("Form waktu kembali tidak ditemukan.")

        form_data = {}
        for input_tag in form.find_all('input', type='hidden'):
            if input_tag.get('name'):
                form_data[input_tag.get('name')] = input_tag.get('value')
        
        form_data['ReturnTime'] = 'TodayTomorrow' # Asumsi nama input dan value
        # form_data['Q3'] = '1' # Contoh lain

        form_action = form.get('action') or response.url
        if not form_action.startswith('http'):
            form_action = response.url.split('?')[0].rsplit('/', 1)[0] + '/' + form_action

        logger.info(f"Mengirim pilihan waktu kembali ke: {form_action}")
        response = session.post(form_action, data=form_data)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Langkah 5: Pilih angka 7 (Sangat setuju) untuk semua pertanyaan
        # Ini adalah bagian yang paling tricky dan sangat bergantung pada struktur HTML.
        # Asumsi: Semua pertanyaan penilaian adalah radio button group atau select dropdown
        # dengan nama yang mengikuti pola (misal 'Q4', 'Q5', dst) atau memiliki class tertentu.
        # Asumsi: Value untuk 'Sangat setuju' adalah '7'.

        form = soup.find('form')
        if not form:
            raise ValueError("Form pertanyaan penilaian tidak ditemukan.")

        form_data = {}
        for input_tag in form.find_all('input', type='hidden'):
            if input_tag.get('name'):
                form_data[input_tag.get('name')] = input_tag.get('value')

        # Cari semua input radio button atau select yang mungkin merupakan pertanyaan penilaian
        # Ini adalah tebakan terbaik tanpa melihat HTML langsung
        for input_tag in form.find_all('input', type='radio'):
            if 'Q' in input_tag.get('name', '') and input_tag.get('value') == '7':
                form_data[input_tag.get('name')] = '7'
        
        for select_tag in form.find_all('select'):
            if 'Q' in select_tag.get('name', ''):
                # Cari option dengan value '7'
                option_7 = select_tag.find('option', value='7')
                if option_7:
                    form_data[select_tag.get('name')] = '7'

        form_action = form.get('action') or response.url
        if not form_action.startswith('http'):
            form_action = response.url.split('?')[0].rsplit('/', 1)[0] + '/' + form_action

        logger.info(f"Mengisi semua pertanyaan dengan '7' ke: {form_action}")
        response = session.post(form_action, data=form_data)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Langkah 6: Isi pesan (jika ada)
        # Asumsi: Input textarea untuk pesan memiliki name 'Comments' atau 'Message'
        form = soup.find('form')
        if form: # Form pesan mungkin opsional
            form_data = {}
            for input_tag in form.find_all('input', type='hidden'):
                if input_tag.get('name'):
                    form_data[input_tag.get('name')] = input_tag.get('value')
            
            # Coba mengisi pesan jika input field ada
            if form.find('textarea', {'name': 'Comments'}):
                form_data['Comments'] = user_message if user_message else ''
            elif form.find('textarea', {'name': 'Message'}):
                form_data['Message'] = user_message if user_message else ''
            # Anda mungkin perlu menyesuaikan ini

            form_action = form.get('action') or response.url
            if not form_action.startswith('http'):
                form_action = response.url.split('?')[0].rsplit('/', 1)[0] + '/' + form_action

            logger.info(f"Mengirim pesan ke: {form_action}")
            response = session.post(form_action, data=form_data)
            soup = BeautifulSoup(response.text, 'html.parser')
        else:
            logger.info("Form pesan tidak ditemukan atau sudah dilewati.")

        # Langkah 7: Dapatkan ID Special Promo
        # Asumsi: ID promo ada di halaman terakhir, mungkin dalam tag <p>, <div>, atau <span>
        # dengan teks "ID Special Promo: XXXXX"
        # Ini adalah bagian yang paling bervariasi. Perlu inspeksi HTML yang akurat.
        promo_id = "Tidak ditemukan"
        # Mencari teks yang mengandung "ID Special Promo:"
        promo_text_elements = soup.find_all(text=re.compile(r"ID Special Promo:\s*(\d+)"))
        if promo_text_elements:
            match = re.search(r"ID Special Promo:\s*(\d+)", promo_text_elements[0])
            if match:
                promo_id = match.group(1)
                logger.info(f"ID Promo ditemukan: {promo_id}")
            else:
                logger.warning("Regex untuk ID Promo tidak cocok.")
        else:
            logger.warning("Teks 'ID Special Promo:' tidak ditemukan di halaman akhir.")

        return promo_id

    except requests.exceptions.RequestException as e:
        logger.error(f"Kesalahan koneksi saat mengotomatisasi survei: {e}")
        return f"Error: Kesalahan koneksi. ({e})"
    except ValueError as e:
        logger.error(f"Kesalahan parsing HTML saat mengotomatisasi survei: {e}")
        return f"Error: Kesalahan parsing halaman survei. ({e})"
    except Exception as e:
        logger.error(f"Kesalahan tak terduga saat mengotomatisasi survei: {e}")
        return f"Error: Terjadi kesalahan tak terduga. ({e})"


# --- Handler Status Percakapan ---
async def enter_customer_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima kode pelanggan dari pengguna dan memulai otomatisasi."""
    customer_code = update.message.text.strip()
    if not re.match(r"^\d{16}$", customer_code): # Asumsi 16 digit
        await update.message.reply_text(
            "Kode pelanggan tidak valid. Mohon masukkan 16 digit angka saja.\n"
            "Contoh: `1234567890123456`"
        )
        return ENTER_CUSTOMER_CODE

    context.user_data['customer_code'] = customer_code
    await update.message.reply_text(
        f"Kode pelanggan Anda: `{customer_code}`. "
        f"Sekarang saya akan mencoba mengisi survei secara otomatis untuk Anda.\n"
        f"Mohon tunggu sebentar..."
    )
    
    # Langsung pindah ke status AUTOMATE_SURVEY_STEPS untuk memicu otomatisasi
    await update.message.reply_text(
        "Apakah Anda ingin menambahkan pesan kustom untuk survei? "
        "Ketik pesan Anda (maks 500 karakter) atau ketik `lanjut` jika tidak ada pesan."
    )
    return ENTER_MESSAGE # Pindah ke ENTER_MESSAGE setelah kode pelanggan diterima

async def enter_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima pesan kustom dari pengguna atau melanjutkan jika tidak ada pesan, lalu memicu otomatisasi."""
    user_input = update.message.text.strip()

    if user_input.lower() == 'lanjut':
        context.user_data['user_message'] = None
    else:
        user_message = user_input
        if len(user_message) > 500:
            await update.message.reply_text(
                "Pesan terlalu panjang. Maksimal 500 karakter. Mohon coba lagi "
                "atau ketik `lanjut` jika tidak ada pesan."
            )
            return ENTER_MESSAGE

        context.user_data['user_message'] = user_message
        await update.message.reply_text(f"Pesan Anda: \"{user_message}\"")

    await update.message.reply_text("Memulai otomatisasi survei...")
    
    # Panggil fungsi otomatisasi
    promo_id = await automate_survey_steps(
        requests.Session(), # Gunakan session untuk mempertahankan cookies
        STARBUCKS_SURVEY_URL,
        context.user_data['customer_code'],
        context.user_data.get('user_message')
    )

    if promo_id.startswith("Error:"):
        await update.message.reply_text(
            f"Maaf, terjadi kesalahan saat mengotomatisasi survei: {promo_id}\n"
            "Mungkin ada perubahan pada situs web atau mekanisme anti-bot.\n"
            "Silakan coba lagi nanti atau isi survei secara manual."
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"Otomatisasi selesai! ID Special Promo Anda adalah: **`{promo_id}`**\n\n"
            "Anda dapat menuliskan ID ini di struk Anda dan menunjukkannya kepada barista Starbucks "
            "untuk menukarkan promo **Buy 1 Get 1 Free**. Promo ini berlaku selama 7 hari.\n\n"
            "Selamat menikmati! 😊"
        )
        await update.message.reply_text("Terima kasih telah menggunakan bot ini!")
        return ConversationHandler.END

# --- Handler Fallback ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan dan mengakhiri percakapan."""
    await update.message.reply_text(
        "Proses survei dibatalkan. Jika Anda ingin mulai lagi, ketik /start."
    )
    return ConversationHandler.END

# --- Fungsi Utama ---
def main() -> None:
    """Memulai bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ENTER_CUSTOMER_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_customer_code)],
            ENTER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_message)],
            # DISPLAY_PROMO tidak lagi menjadi status terpisah karena promo langsung ditampilkan setelah otomatisasi
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    logger.info("Bot sedang memulai polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

