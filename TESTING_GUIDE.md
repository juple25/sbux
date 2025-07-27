# 🧪 Panduan Testing Bot Starbucks

## Status Survey Link
✅ **Link aktif dan berfungsi**
- URL: https://www.mystarbucksvisit.com/websurvey/2/execute?_g=NTAyMA%3D%3Dh&_s2=76b32521-781a-488f-98d0-996c67c945e8#!/1
- Platform: InMoment survey system
- JavaScript: Required
- Tracking: Google Analytics + ClickTale

## 🔧 Perbaikan yang Sudah Diimplementasikan

### 1. Dynamic URL Parsing ✅
```python
# Sekarang bisa handle format:
"?_g=(NTAyMA%3D%3Dh&_s2=76b32521-781a-488f-98d0-996c67c945e8)"
"?_g=NTAyMA%3D%3Dh&_s2=76b32521-781a-488f-98d0-996c67c945e8"
```

### 2. Reduced Aggressiveness ✅
- **Sebelum:** 20+ endpoints dicoba secara berurutan
- **Sekarang:** 3 priority + 2 fallback endpoints
- **Delay:** 2-8 detik antar request

### 3. Smart Session Management ✅
- Dynamic `x-im-g-id` berdasarkan URL parameter
- Proper session header: `x-session-token-2`
- Cookie management yang lebih baik

### 4. Error Handling ✅
- Rate limiting detection (HTTP 429)
- Retry dengan exponential backoff
- Success/failure pattern matching

## 🚀 Cara Testing Bot

### 1. Test Lokal (Parsing Only)
```bash
cd sbux
python test_bot.py
```

### 2. Test dengan Telegram Bot
```bash
# Install dependencies (jika belum)
pip install -r requirements.txt

# Jalankan bot
python main.py
```

### 3. Flow Testing di Telegram
1. Start bot: `/start`
2. Kirim URL: `https://www.mystarbucksvisit.com/websurvey/2/execute?_g=...`
3. Kirim customer code: `16644 08020727 0916`
4. Kirim message: `Great service!`

## 🛠️ Troubleshooting

### Jika Bot Timeout
1. **Cek koneksi internet**
2. **Tunggu lebih lama** - delay telah ditingkatkan
3. **Coba format customer code berbeda**

### Jika Session Expired
- URL QR code memiliki batas waktu
- Scan QR code baru dari receipt
- Parameter `_s2` berubah setiap scan

### Jika Rate Limited
- Bot sekarang otomatis menunggu 15-30 detik
- Implementasi exponential backoff

## 📊 Expected Behavior

### Sebelum Perbaikan ❌
- Bot mencoba 20+ endpoint → Rate limited
- Request berurutan tanpa delay → Terdeteksi sebagai bot
- Hardcoded headers → Session invalid

### Setelah Perbaikan ✅ 
- Bot mencoba 3-5 endpoint dengan delay
- Request dengan jeda 2-8 detik → Lebih natural
- Dynamic headers berdasarkan URL → Session valid

## 🎯 Tips untuk Success Rate Tinggi

1. **Gunakan URL QR code yang fresh** (baru discan)
2. **Customer code harus akurat** dari receipt
3. **Jangan spam request** - tunggu hasil sebelum retry
4. **Monitor log** untuk debug jika ada masalah

## 📝 Next Steps (Opsional)

Jika masih ada masalah, pertimbangkan:
1. **Browser automation** (Selenium/Playwright) sebagai fallback
2. **Proxy rotation** untuk menghindari IP blocking  
3. **CAPTCHA solving** jika diperlukan
4. **Mobile user-agent** untuk mengurangi deteksi

---
*Bot telah dioptimasi untuk mengurangi timeout dan meningkatkan success rate* ✨