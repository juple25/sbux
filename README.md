# Starbucks Survey Bot

Bot Telegram ini berfungsi sebagai alat eksperimental untuk mencoba mengotomatiskan proses pengisian survei Starbucks di `mystarbucksvisit.com` dan mendapatkan ID promo spesial.

**Penting:**
* **Otomatisasi Eksperimental:** Bot ini mencoba mengotomatiskan beberapa langkah survei (pemilihan bahasa, jenis kunjungan, jawaban "Sangat setuju", dan pengiriman pesan) menggunakan permintaan HTTP (`requests`) dan parsing HTML (`BeautifulSoup`).
* **Potensi Kegagalan:** Otomatisasi web dengan cara ini sangat rentan terhadap perubahan kecil pada struktur situs web, JavaScript dinamis, atau mekanisme anti-bot tersembunyi. **Tidak ada jaminan bahwa otomatisasi ini akan selalu berhasil.** Jika survei gagal, bot akan memberi tahu Anda.
* **Tanggung Jawab Pengguna:** Penggunaan bot ini sepenuhnya menjadi tanggung jawab pengguna.

## Fitur

* Menyediakan tautan langsung ke survei Starbucks.
* Meminta kode pelanggan dari pengguna.
* **Mencoba mengotomatiskan:**
    * Pemilihan "Bahasa Indonesia".
    * Pengisian kode pelanggan.
    * Pemilihan "Membeli dan langsung pergi" & "Ya".
    * Pemilihan "Hari ini atau besok".
    * Pengisian semua pertanyaan penilaian dengan "7 (Sangat setuju)".
    * Pengisian pesan kustom (jika disediakan).
* Mengekstrak dan menampilkan ID promo yang didapatkan setelah otomatisasi selesai.

## Cara Menggunakan Bot (Sebagai Pengguna)

1.  Mulai percakapan dengan bot dengan mengetik `/start`.
2.  Bot akan meminta kode pelanggan Anda. Masukkan kode tersebut.
3.  Bot akan meminta apakah Anda ingin menambahkan pesan kustom untuk survei. Ketik pesan Anda atau ketik `lanjut` jika tidak ada.
4.  Bot kemudian akan mencoba mengisi survei secara otomatis. Mohon tunggu sebentar.
5.  Jika berhasil, bot akan menampilkan ID promo spesial Anda. Jika gagal, bot akan memberi tahu Anda.

## Deployment

Bot ini dirancang untuk di-deploy menggunakan platform seperti Render.com, yang akan terhubung langsung ke repositori GitHub Anda.

### Persiapan

1.  **Dapatkan Token Bot Telegram:**
    * Buka Telegram dan cari [@BotFather](https://t.me/botfather).
    * Ketik `/newbot` dan ikuti instruksi. Anda akan mendapatkan **HTTP API Token** Anda. Simpan token ini dengan sangat aman! (Contoh: `8481395468:AAEFat0skeQc9Z1ntaIECMQhpb-6T0-Lzdk`)

2.  **Siapkan Repositori GitHub:**
    * Pastikan Anda telah mengunggah semua file berikut ke repositori GitHub Anda:
        * `main.py`
        * `requirements.txt`
        * `Procfile`
        * `.env.example`
        * `README.md`
    * Repositori Anda yang sudah ada: `https://github.com/juple25/sbux`

### Deployment ke Render

1.  **Buat Akun Render:** Jika Anda belum memiliki akun, daftar di [render.com](https://render.com/).

2.  **Buat Layanan Web Baru:**
    * Dari dashboard Render, klik `New` -> `Web Service`.
    * Pilih opsi untuk menghubungkan ke repositori GitHub Anda.
    * Pilih repositori Anda (`juple25/sbux`).

3.  **Konfigurasi Layanan:**
    * **Name:** Beri nama layanan Anda (misalnya, `starbucks-survey-bot`).
    * **Region:** Pilih wilayah yang terdekat dengan pengguna target Anda (misalnya, Singapore atau Oregon).
    * **Branch:** `main` (atau `master`, tergantung branch default Anda).
    * **Root Directory:** Biarkan kosong (karena file Anda ada di root repositori).
    * **Runtime:** `Python 3` (Render akan mendeteksinya dari `requirements.txt`).
    * **Build Command:** `pip install -r requirements.txt`
    * **Start Command:** `python main.py`
    * **Instance Type:** Pilih rencana gratis atau sesuai kebutuhan Anda.

4.  **Atur Variabel Lingkungan (Sangat Penting!):**
    * Di bagian "Environment Variables", klik `Add Environment Variable`.
    * **Key:** `TELEGRAM_BOT_TOKEN`
    * **Value:** Tempelkan **HTTP API Token** bot Telegram Anda di sini (`8481395468:AAEFat0skeQc9Z1ntaIECMQhpb-6T0-Lzdk`).

5.  **Deploy:** Klik `Create Web Service`.

Render akan secara otomatis membangun dan men-deploy bot Anda. Anda dapat memantau log di dashboard Render untuk memastikan bot berjalan dengan benar dan melihat apakah otomatisasi survei berhasil atau gagal.

## Pengembangan Lokal

Untuk menjalankan bot secara lokal (untuk pengujian atau pengembangan):

1.  **Clone Repositori:**
    ```bash
    git clone [https://github.com/juple25/sbux.git](https://github.com/juple25/sbux.git)
    cd sbux
    ```
2.  **Buat dan Aktifkan Virtual Environment (Disarankan):**
    ```bash
    python -m venv venv
    # Di Windows
    .\venv\Scripts\activate
    # Di macOS/Linux
    source venv/bin/activate
    ```
3.  **Instal Dependensi:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Buat File `.env`:**
    * Buat file bernama `.env` di root proyek.
    * Salin konten dari `.env.example` ke dalamnya dan ganti `YOUR_TELEGRAM_BOT_TOKEN_HERE` dengan token bot Anda.
    * Pastikan file `.env` **TIDAK** di-commit ke Git (tambahkan `.env` ke `.gitignore` jika belum ada).
5.  **Jalankan Bot:**
    ```bash
    python main.py
    ```
    Bot Anda sekarang akan berjalan secara lokal dan akan merespons di Telegram.
