# Starbucks Survey Bot

Bot Telegram untuk mengotomatisasi pengisian survey Starbucks dan mendapatkan kode promo.

## 🌟 Fitur

- ✅ Otomatis memilih bahasa Indonesia
- ✅ Otomatis mengisi semua pertanyaan dengan "Sangat Setuju" (nilai 7)
- ✅ Otomatis memilih opsi "Membeli langsung pergi" dan "Ya"
- ✅ Otomatis memilih "Hari ini"
- ✅ Input manual untuk kode pelanggan dan pesan
- ✅ Ekstraksi otomatis kode promo

## 🚀 Deployment ke Render

### Langkah 1: Persiapan GitHub

1. Fork atau clone repository ini
2. Upload semua file ke repository GitHub Anda:
   - `main.py`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
   - `render.yaml`

### Langkah 2: Deploy ke Render

1. Buat akun di [Render.com](https://render.com)
2. Klik "New +" → "Web Service"
3. Connect GitHub repository Anda
4. Pilih repository yang berisi bot
5. Konfigurasi:
   - **Name**: starbucks-survey-bot (atau nama lain)
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free

### Langkah 3: Environment Variables

Di Render dashboard, tambahkan environment variables:

```
TELEGRAM_BOT_TOKEN = 8481395468:AAEFat0skeQc9Z1ntaIECMQhpb-6T0-Lzdk
WEBHOOK_URL = https://your-app-name.onrender.com
```

### Langkah 4: Setup Webhook

Setelah deploy berhasil, bot akan otomatis setup webhook. Jika perlu manual setup:

```bash
curl https://api.telegram.org/bot8481395468:AAEFat0skeQc9Z1ntaIECMQhpb-6T0-Lzdk/setWebhook?url=https://your-app-name.onrender.com/8481395468:AAEFat0skeQc9Z1ntaIECMQhpb-6T0-Lzdk
```

## 📱 Cara Menggunakan Bot

1. Buka Telegram dan cari bot Anda
2. Ketik `/start`
3. Kirim kode pelanggan Starbucks
4. Kirim pesan untuk survey
5. Bot akan otomatis mengisi survey
6. Terima kode promo!

## 🛠️ Development Lokal

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot
python main.py
```

## ⚠️ Catatan Penting

- Bot ini untuk tujuan edukasi
- Gunakan dengan bijak sesuai terms of service Starbucks
- Kode pelanggan harus valid dari struk pembelian
- Bot akan gagal jika format survey berubah

## 🔧 Troubleshooting

### Bot tidak merespon
- Cek status deployment di Render
- Pastikan webhook URL benar
- Cek logs di Render dashboard

### Survey gagal
- Pastikan kode pelanggan valid
- Website survey mungkin sedang maintenance
- Format survey mungkin berubah

## 📝 Update & Maintenance

Jika survey format berubah, update:
1. Selector CSS di `main.py`
2. Logic pengisian form
3. Pattern ekstraksi kode promo

## 🤝 Kontribusi

Feel free to submit issues atau pull requests!

## 📄 License

MIT License
