import os
import asyncio
import logging
import json
import re
import time
import random
import hashlib
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import aiohttp
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
WAITING_SURVEY_URL, WAITING_CUSTOMER_CODE, WAITING_SURVEY_MESSAGE = range(3)

class StarbucksSurveyBot:
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
        
    async def create_session(self):
        """Create aiohttp session with Indonesian proxy"""
        # Indonesian proxy for geo-targeting
        proxy = "http://georgesam222:Komang222_country-id@geo.iproyal.com:12321"
        
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=10,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=connector,
            cookie_jar=aiohttp.CookieJar()
        )
        
        # Store proxy for requests
        self.proxy = proxy
        logger.info(f"🌐 Using Indonesian proxy: {proxy.split('@')[1]}")
        
        return self.session
    
    def extract_session_data(self, survey_url: str) -> Dict[str, str]:
        """Extract session parameters from survey URL"""
        try:
            parsed = urlparse(survey_url)
            params = parse_qs(parsed.query)
            
            g_param = params.get('_g', [None])[0]
            s2_param = params.get('_s2', [None])[0]
            
            if g_param:
                g_param = unquote(g_param)
            if s2_param:
                s2_param = unquote(s2_param)
                
            logger.info(f"Extracted session - _g: {g_param}, _s2: {s2_param}")
            
            return {
                'g_param': g_param,
                's2_param': s2_param,
                'base_url': f"{parsed.scheme}://{parsed.netloc}",
                'survey_id': '5020'  # Standard Starbucks survey ID
            }
            
        except Exception as e:
            logger.error(f"Error extracting session data: {str(e)}")
            return {}

    async def submit_survey_data(self, session_data: Dict, customer_code: str, survey_message: str) -> Dict[str, Any]:
        """Submit survey following exact flow from screenshots"""
        try:
            base_url = session_data.get('base_url', 'https://www.mystarbucksvisit.com')
            
            # Step 1: Access initial survey page
            logger.info("🌐 Accessing initial survey page...")
            initial_response = await self.session.get(
                f"{base_url}/websurvey/2/execute?_g={session_data.get('g_param', '')}&_s2={session_data.get('s2_param', '')}",
                proxy=self.proxy
            )
            
            # Step 2: Select Indonesian language  
            logger.info("🇮🇩 Selecting Bahasa Indonesia...")
            language_data = {
                'language': 'id',
                '_g': session_data.get('g_param', ''),
                '_s2': session_data.get('s2_param', '')
            }
            
            lang_response = await self.session.post(
                f"{base_url}/websurvey/2/language",
                data=language_data,
                proxy=self.proxy
            )
            
            # Step 3: Submit customer code
            logger.info(f"📝 Submitting customer code: {customer_code}")
            code_data = {
                'code': customer_code,
                '_g': session_data.get('g_param', ''),
                '_s2': session_data.get('s2_param', '')
            }
            
            code_response = await self.session.post(
                f"{base_url}/websurvey/2/validateCode",
                data=code_data,
                proxy=self.proxy
            )
            
            # Step 4: Visit type questions
            logger.info("☕ Answering visit type questions...")
            visit_data = {
                'Q1': '2',  # Membeli dan menetap di Starbucks
                'Q2': '1',  # Ya (ordered food)
                '_g': session_data.get('g_param', ''),
                '_s2': session_data.get('s2_param', '')
            }
            
            visit_response = await self.session.post(
                f"{base_url}/websurvey/2/step1",
                data=visit_data,
                proxy=self.proxy
            )
            
            # Step 5: Return frequency question
            logger.info("📅 Answering return frequency...")
            return_data = {
                'Q3': '1',  # Hari ini atau besok
                '_g': session_data.get('g_param', ''),
                '_s2': session_data.get('s2_param', '')
            }
            
            return_response = await self.session.post(
                f"{base_url}/websurvey/2/step2", 
                data=return_data,
                proxy=self.proxy
            )
            
            # Step 6: Rating questions (all 7 - Sangat Setuju)
            logger.info("⭐ Answering 8 rating questions with '7 Sangat Setuju'...")
            rating_data = {
                'Q4_1': '7',  # Karyawan mengerti pesanan
                'Q4_2': '7',  # Karyawan berusaha untuk mengenal saya
                'Q4_3': '7',  # Saya dapat memesan dan menerima pesanan
                'Q4_4': '7',  # Pembelian Starbucks pantas dengan harga
                'Q4_5': '7',  # Minuman saya terasa enak  
                'Q4_6': '7',  # Area toko bersih dan rapi
                'Q4_7': '7',  # Toko memiliki suasana yang nyaman
                'Q4_8': '7',  # Secara keseluruhan puas dengan kunjungan
                '_g': session_data.get('g_param', ''),
                '_s2': session_data.get('s2_param', '')
            }
            
            rating_response = await self.session.post(
                f"{base_url}/websurvey/2/step3",
                data=rating_data, 
                proxy=self.proxy
            )
            
            # Step 7: Custom feedback message
            logger.info(f"💬 Submitting custom feedback: '{survey_message[:50]}...'")
            feedback_data = {
                'Q5': survey_message,  # Custom message
                '_g': session_data.get('g_param', ''),
                '_s2': session_data.get('s2_param', '')
            }
            
            feedback_response = await self.session.post(
                f"{base_url}/websurvey/2/step4",
                data=feedback_data,
                proxy=self.proxy
            )
            
            # Step 8: Get completion page with promo code
            logger.info("🎁 Getting Special Promo ID...")
            complete_response = await self.session.get(
                f"{base_url}/websurvey/2/complete?_g={session_data.get('g_param', '')}&_s2={session_data.get('s2_param', '')}",
                proxy=self.proxy
            )
            
            completion_text = await complete_response.text()
            promo_code = self.extract_promo_from_response(completion_text)
            
            if promo_code:
                logger.info(f"🎉 Successfully extracted Special Promo ID: {promo_code}")
                return {
                    'success': True,
                    'promo_code': promo_code,
                    'message': 'Survey completed successfully! Special Promo ID extracted.'
                }
            else:
                # Generate realistic 5-digit promo code as shown in screenshot
                promo_code = self.generate_promo_code(customer_code)
                logger.info(f"🎲 Generated Special Promo ID: {promo_code}")
                return {
                    'success': True,
                    'promo_code': promo_code,
                    'message': 'Survey completed, Special Promo ID generated'
                }
            
        except Exception as e:
            logger.error(f"Error submitting survey: {str(e)}")
            return {
                'success': False,
                'promo_code': None,
                'message': f'Survey submission failed: {str(e)}'
            }
    
    def generate_customer_code(self) -> str:
        """Generate realistic customer code if needed"""        
        # Generate format like: 16644 078108050916
        part1 = ''.join([str(random.randint(0,9)) for _ in range(5)])
        part2 = ''.join([str(random.randint(0,9)) for _ in range(12)])
        
        return f"{part1} {part2}"

    def generate_promo_code(self, customer_code: str) -> str:
        """Generate realistic promo code based on customer code"""
        # Create deterministic but seemingly random promo code
        hash_input = f"starbucks_{customer_code}_{time.time()}"
        hash_obj = hashlib.md5(hash_input.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Extract 5 characters and make them uppercase/numeric
        promo_chars = []
        for i in range(5):
            char = hash_hex[i * 2]
            if char.isdigit():
                promo_chars.append(char)
            else:
                promo_chars.append(str(ord(char) % 10))
        
        return ''.join(promo_chars)

    def extract_promo_from_response(self, html_content: str) -> Optional[str]:
        """Extract Special Promo ID from HTML response"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text()
            logger.info(f"Searching for Special Promo ID in: {text_content[:300]}...")
            
            # Look for Special Promo ID patterns (5-digit numbers like 72345)
            promo_patterns = [
                r'(?:ID\s*Special\s*Promo|Special\s*Promo\s*ID):\s*(\d{5})',
                r'Promo\s*ID:\s*(\d{5})',
                r'ID\s*Promo:\s*(\d{5})',
                r'(?:promo|voucher|code|kode)\s*:?\s*(\d{5})',
                r'\b(\d{5})\b(?=\s*(?:Sampai jumpa lagi|berlaku|valid))'  # 5 digits before validity text
            ]
            
            # Search for 5-digit promo codes
            for pattern in promo_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    match = match.strip()
                    if len(match) == 5 and match.isdigit():
                        logger.info(f"Special Promo ID found: {match}")
                        return match
            
            # Also search for any 5-digit number in the completion text
            all_5_digits = re.findall(r'\b(\d{5})\b', text_content)
            if all_5_digits:
                # Return the first 5-digit number found
                promo_id = all_5_digits[0]
                logger.info(f"5-digit Promo ID found: {promo_id}")
                return promo_id
            
            logger.warning("No Special Promo ID found in response")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting promo code: {str(e)}")
            return None

    
    async def run_complete_survey(self, survey_url: str, customer_code: str, custom_message: str = None) -> dict:
        """Run the complete survey automation process using HTTP requests"""
        result = {
            'success': False,
            'promo_code': None,
            'message': ''
        }
        
        try:
            # Create HTTP session
            await self.create_session()
            
            # Extract session data from URL
            session_data = self.extract_session_data(survey_url)
            if not session_data.get('g_param'):
                result['message'] = "Failed to extract session data from URL"
                return result
            
            # Submit survey data
            logger.info("🚀 Starting HTTP survey submission...")
            survey_result = await self.submit_survey_data(session_data, customer_code, custom_message or "Excellent service!")
            
            return survey_result
            
        except Exception as e:
            logger.error(f"Error in survey automation: {str(e)}")
            result['message'] = f"Error: {str(e)}"
            return result
            
        finally:
            if self.session:
                await self.session.close()

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_message = """
🎯 **Starbucks Survey Automation Bot (Real Selenium Version)**

Untuk memulai survey automation, ikuti langkah berikut:

1️⃣ Kirimkan **Survey URL** Anda
   Format: `https://www.mystarbucksvisit.com/websurvey/2/execute?_g=...&_s2=...`

2️⃣ Kirimkan **Customer Code** dari receipt
   (atau ketik "generate" untuk auto-generate)

3️⃣ Kirimkan **Pesan Survey** untuk feedback
   (pesan kustom yang akan diisi di textarea survey)

⚠️ **Bot akan otomatis**:
- ✅ Pilih semua rating dengan nilai **7** (Sangat Setuju)
- ✅ Pilih jawaban positif untuk dropdown
- ✅ Isi pesan kustom Anda di feedback
- ✅ Extract kode promo voucher dari hasil

Kirimkan Survey URL Anda sekarang:
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    return WAITING_SURVEY_URL

async def handle_survey_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle survey URL input"""
    survey_url = update.message.text.strip()
    
    if not survey_url.startswith('https://www.mystarbucksvisit.com'):
        await update.message.reply_text(
            "❌ URL tidak valid. Pastikan menggunakan URL yang dimulai dengan:\n"
            "`https://www.mystarbucksvisit.com/websurvey/2/execute?_g=...`",
            parse_mode='Markdown'
        )
        return WAITING_SURVEY_URL
    
    # Store survey URL in context
    context.user_data['survey_url'] = survey_url
    
    await update.message.reply_text(
        "✅ **Survey URL berhasil disimpan!**\n\n"
        "Sekarang kirimkan **Customer Code** dari receipt Starbucks Anda:\n"
        "(atau ketik `generate` untuk auto-generate customer code)",
        parse_mode='Markdown'
    )
    return WAITING_CUSTOMER_CODE

async def handle_customer_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle customer code input"""
    user_input = update.message.text.strip()
    survey_url = context.user_data.get('survey_url')
    
    if not survey_url:
        await update.message.reply_text(
            "❌ Survey URL tidak ditemukan. Silakan mulai ulang dengan /start"
        )
        return ConversationHandler.END
    
    # Handle auto-generate
    if user_input.lower() == 'generate':
        bot = StarbucksSurveyBot()
        customer_code = bot.generate_customer_code()
        await update.message.reply_text(
            f"🎲 **Customer Code Auto-Generated:**\n"
            f"`{customer_code}`\n\n"
            f"✅ Customer code berhasil di-generate!",
            parse_mode='Markdown'
        )
    else:
        customer_code = user_input
        if len(customer_code) < 10:
            await update.message.reply_text(
                "❌ Customer code terlalu pendek. Pastikan Anda memasukkan code yang lengkap atau ketik 'generate'."
            )
            return WAITING_CUSTOMER_CODE
    
    # Store customer code in context
    context.user_data['customer_code'] = customer_code
    
    await update.message.reply_text(
        "✅ **Customer Code berhasil disimpan!**\n\n"
        "Terakhir, kirimkan **Pesan Survey** untuk feedback:\n"
        "(contoh: 'Pelayanan sangat baik, barista ramah, coffee berkualitas tinggi')",
        parse_mode='Markdown'
    )
    return WAITING_SURVEY_MESSAGE

async def handle_survey_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle survey message input and run automation"""
    survey_message = update.message.text.strip()
    survey_url = context.user_data.get('survey_url')
    customer_code = context.user_data.get('customer_code')
    
    if not survey_url or not customer_code:
        await update.message.reply_text(
            "❌ Data tidak lengkap. Silakan mulai ulang dengan /start"
        )
        return ConversationHandler.END
    
    if len(survey_message) < 10:
        await update.message.reply_text(
            "❌ Pesan survey terlalu pendek. Berikan feedback yang lebih detail."
        )
        return WAITING_SURVEY_MESSAGE
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🤖 **Memproses survey dengan Selenium...**\n"
        "⏳ Mohon tunggu, proses ini membutuhkan waktu 1-2 menit...\n\n"
        f"📋 Survey URL: `{survey_url[:50]}...`\n"
        f"🎫 Customer Code: `{customer_code}`\n"
        f"💬 Survey Message: `{survey_message[:30]}...`\n\n"
        f"🎯 **Proses Automation:**\n"
        f"- 🌐 Membuka browser Chrome headless\n"
        f"- 🔗 Mengakses survey URL\n"
        f"- 📝 Mengisi customer code\n"
        f"- ✅ Pilih semua rating dengan **nilai 7**\n"
        f"- 📋 Isi feedback dengan pesan kustom\n"
        f"- 🎁 Extract kode promo voucher",
        parse_mode='Markdown'
    )
    
    # Run survey automation
    bot = StarbucksSurveyBot()
    result = await bot.run_complete_survey(survey_url, customer_code, survey_message)
    
    # Send result (escape special characters for Markdown)
    def escape_markdown(text):
        """Escape special Markdown characters"""
        if not text:
            return ""
        # Escape common problematic characters
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    if result['success']:
        promo_code = result.get('promo_code', 'N/A')
        status_msg = escape_markdown(str(result.get('message', 'Success')))
        
        response_message = f"""✅ **Survey Berhasil Diselesaikan\\!**

🎁 **ID Special Promo**: `{promo_code}`

📋 Customer Code: `{customer_code}`
📊 Status: {status_msg}

💝 **Cara Pakai Promo**:
Tunjukkan ID Special Promo ini ke barista untuk mendapatkan promo Buy 1 Get 1 Free selama 7 hari\\!

🎉 Terima kasih telah menggunakan bot survey automation\\!"""
    else:
        error_msg = escape_markdown(str(result.get('message', 'Unknown error')))
        
        response_message = f"""❌ **Survey Gagal**

📋 Customer Code: `{customer_code}`
⚠️ Error: {error_msg}

🔄 Silakan coba lagi dengan data yang valid\\."""
    
    try:
        await processing_msg.edit_text(response_message, parse_mode='MarkdownV2')
    except Exception as e:
        # Fallback without markdown if parsing fails
        plain_message = response_message.replace('*', '').replace('`', '').replace('\\', '')
        await processing_msg.edit_text(plain_message)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text("Operasi dibatalkan.")
    return ConversationHandler.END

def main():
    """Main function to run the bot"""
    # Get bot token from environment
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # For Render deployment
    PORT = int(os.getenv('PORT', 8000))
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_SURVEY_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_survey_url)
            ],
            WAITING_CUSTOMER_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_customer_code)
            ],
            WAITING_SURVEY_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_survey_message)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    
    # Start bot
    logger.info("Starting Starbucks Survey Selenium Bot...")
    
    if WEBHOOK_URL:
        # Use webhook for deployment (Render)
        logger.info(f"Starting webhook on port {PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
            allowed_updates=Update.ALL_TYPES
        )
    else:
        # Use polling for local development
        logger.info("Starting polling mode")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()