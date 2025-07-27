# 🎯 Correct Starbucks Survey Flow

Berdasarkan screenshot yang diberikan, ini adalah flow yang benar:

## 📱 Actual Survey Flow

### 1. Language Selection
- **Page:** Language selection (English/Bahasa Indonesia)
- **Action:** Klik "BAHASA INDONESIA"
- **Method:** Likely form POST or JavaScript

### 2. Customer Code Entry  
- **Page:** "Kode Pelanggan" input field
- **Input:** `16644086207270916` (tanpa spasi)
- **Action:** Klik tombol "MASUKKAN" (hijau)
- **Method:** Form POST validation

### 3. Welcome & Survey Start
- **Page:** "Terima kasih atas kunjungan Anda ke Starbucks!"
- **Action:** Klik "Berikutnya"
- **Info:** Survey 3 menit, pelanggan berharga

### 4. Survey Questions - Page 1
- **Question 1:** "Pilih jenis kunjungan Anda"
  - ✅ Membeli dan langsung pergi (selected)
  - ○ Membeli dan menetap di Starbucks  
  - ○ Membeli melalui Drive - Thru
- **Question 2:** "Apakah Anda pesan makanan?"
  - ✅ Ya (selected)
  - ○ Tidak
- **Action:** Klik "Berikutnya"

### 5. Survey Questions - Page 2  
- **Question:** "Kapan kemungkinan anda akan kembali ke Starbucks untuk membeli lagi?"
  - ✅ Hari ini atau besok (selected)
  - ○ Minggu depan
  - ○ Bulan depan
  - ○ Lebih dari sebulan dari sekarang
  - ○ Tidak pernah
  - ○ Belum tahu
- **Action:** Klik "Berikutnya"

### 6. Rating Questions
Multiple rating questions dengan dropdown 1-7:
- **Format:** "1 Sangat tidak setuju" sampai "7 Sangat setuju"
- **Questions include:**
  - Karyawan berusaha untuk mengenal saya
  - Saya dianggap sebagai pelanggan istimewa  
  - Karyawan berusaha untuk memenuhi kebutuhan
  - Ruang toko nyaman
  - Karyawan berkomitmen untuk memberikan layanan tepat
  - Pembelian Starbucks pantas dengan harga yang dibayar
  - Makanan saya terasa enak
- **All selections:** "7 Sangat setuju"

### 7. Final Feedback
- **Question:** "Apakah ada hal lain yang ingin disampaikan pada kunjungan ini ke Starbucks?"
- **Input:** Text area untuk feedback manual
- **Action:** Klik "Berikutnya"

## 🔧 Technical Implementation Needed

### Problem dengan Current Bot:
1. ❌ **Direct API calls** - Bot langsung ke endpoint tanpa form flow
2. ❌ **Wrong endpoints** - Semua return 404 karena tidak mengikuti form sequence
3. ❌ **Missing session handling** - Tidak maintain state antar form

### Solution Required:
1. ✅ **Form-based submission** - Follow HTML form POST sequence  
2. ✅ **State management** - Maintain session cookies dan form state
3. ✅ **Sequential flow** - Submit each form step by step
4. ✅ **Response parsing** - Parse HTML response untuk next step

## 🚀 Next Steps

1. **Inspect Network Traffic** saat mengisi survey manual
2. **Identify exact endpoints** untuk setiap form submission
3. **Update bot** untuk mengikuti form flow sequence  
4. **Test** dengan session yang valid

## 📊 Expected Endpoints (Guess)

Berdasarkan form flow:
```
POST /websurvey/2/setLanguage → language=id
POST /websurvey/2/validateCode → code=16644086207270916  
POST /websurvey/2/next → question responses
POST /websurvey/2/next → rating responses
POST /websurvey/2/submit → final feedback
```

Bot harus mengikuti sequence ini, bukan langsung ke endpoint terakhir!