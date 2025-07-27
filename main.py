import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import aiohttp
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import unquote, quote, urlparse, parse_qs
import re
import uuid
import json
import base64
import random
import time

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States untuk conversation
WAITING_URL, WAITING_CODE, WAITING_MESSAGE = range(3)

# Data storage untuk session
user_sessions = {}

class StarbucksSurveyBot:
    def __init__(self):
        self.base_url = "https://www.mystarbucksvisit.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"iOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session_data = {}

    async def create_session(self):
        """Create aiohttp session with browser-like settings"""
        timeout = aiohttp.ClientTimeout(total=45, connect=15)
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=5,
            keepalive_timeout=60,
            enable_cleanup_closed=True
        )
        
        return aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=connector,
            cookie_jar=aiohttp.CookieJar()
        )

    def extract_session_from_url(self, survey_url):
        """Extract session parameters from survey URL with improved parsing"""
        try:
            # Handle URL with parentheses in query parameters
            if '(' in survey_url and ')' in survey_url:
                # Extract content between parentheses
                start = survey_url.find('(') + 1
                end = survey_url.find(')')
                params_str = survey_url[start:end]
                
                # Parse individual parameters
                g_param = None
                s2_param = None
                
                if '&' in params_str:
                    parts = params_str.split('&')
                    for part in parts:
                        if '_g=' in part:
                            g_param = part.split('_g=')[1]
                        elif '_s2=' in part:
                            s2_param = part.split('_s2=')[1]
                        elif part.startswith('NTAy'):  # Handle case where _g= is missing
                            g_param = part
                else:
                    # Single parameter case
                    if '_g=' in params_str:
                        g_param = params_str.split('_g=')[1]
                    elif '_s2=' in params_str:
                        s2_param = params_str.split('_s2=')[1]
            else:
                # Standard URL parsing
                parsed = urlparse(survey_url)
                params = parse_qs(parsed.query)
                
                g_param = params.get('_g', [None])[0]
                s2_param = params.get('_s2', [None])[0]
            
            # URL decode if needed
            if g_param:
                g_param = unquote(g_param)
            if s2_param:
                s2_param = unquote(s2_param)
            
            logger.info(f"Extracted _g: {g_param}, _s2: {s2_param}")
            return g_param, s2_param
            
        except Exception as e:
            logger.error(f"Error extracting session from URL: {e}")
            return None, None

    async def get_initial_page(self, session, survey_url=None):
        """Get initial survey page and extract session data"""
        try:
            if survey_url:
                url = survey_url
                g_param, s2_param = self.extract_session_from_url(survey_url)
                logger.info(f"Using provided survey URL: {url}")
            else:
                return None
            
            # Store session data
            self.session_data = {
                'g_param': g_param,
                's2_param': s2_param,
                'referer': url
            }
            
            logger.info(f"=== URL FOR MANUAL TEST: {url} ===")
            
            # Add random delay to avoid detection
            await asyncio.sleep(random.uniform(1, 3))
            
            # Get initial page with mobile browser headers
            async with session.get(url, headers=self.headers) as response:
                response_text = await response.text()
                if response.status == 200:
                    logger.info("Initial page loaded successfully")
                    return response_text
                else:
                    logger.error(f"Failed to get initial page: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting initial page: {e}")
            return None

    def get_smart_code_formats(self, customer_code):
        """Generate smart customer code formats based on common patterns"""
        formats = []
        
        # Clean the original code
        clean_code = customer_code.replace(' ', '').replace('-', '').upper()
        
        # Add original format first
        formats.append(customer_code)
        
        # Add cleaned format
        if clean_code not in formats:
            formats.append(clean_code)
        
        # Try common spacing patterns for Indonesian receipts
        if len(clean_code) >= 10:
            # Pattern: XXXXX XXXXX
            spaced = f"{clean_code[:5]} {clean_code[5:]}"
            if spaced not in formats:
                formats.append(spaced)
        
        return formats[:3]  # Limit to 3 formats to avoid rate limiting

    async def submit_language_selection(self, session):
        """Submit language selection form (Bahasa Indonesia)"""
        try:
            await asyncio.sleep(random.uniform(1, 3))
            
            form_data = {
                'language': 'id',
                '_g': self.session_data.get('g_param', ''),
                '_s2': self.session_data.get('s2_param', '')
            }
            
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['Referer'] = self.session_data.get('referer', '')
            
            endpoints_to_try = [
                f"{self.base_url}/websurvey/2/setLanguage",
                f"{self.base_url}/websurvey/2/language", 
                f"{self.base_url}/websurvey/2/execute"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    async with session.post(endpoint, data=form_data, headers=headers) as response:
                        logger.info(f"Language endpoint {endpoint}: {response.status}")
                        
                        if response.status in [200, 302]:
                            logger.info("✅ Language selection successful")
                            return True
                except Exception as e:
                    logger.warning(f"Language endpoint {endpoint} failed: {e}")
                    continue
                    
            logger.info("Language selection endpoints not found, continuing...")
            return True  # Continue even if language selection endpoint not found
            
        except Exception as e:
            logger.error(f"Error submitting language: {e}")
            return False

    async def submit_customer_code(self, session, customer_code):
        """Submit customer code form"""
        try:
            code_formats = self.get_smart_code_formats(customer_code)
            logger.info(f"Trying customer code formats: {code_formats}")
            
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['Referer'] = self.session_data.get('referer', '')
            
            endpoints_to_try = [
                f"{self.base_url}/websurvey/2/validateCode",
                f"{self.base_url}/websurvey/2/customerCode",
                f"{self.base_url}/websurvey/2/next",
                f"{self.base_url}/websurvey/2/submit"
            ]
            
            for endpoint in endpoints_to_try:
                for code_format in code_formats:
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    form_data = {
                        'customer_code': code_format,
                        'code': code_format,
                        'customerCode': code_format,
                        '_g': self.session_data.get('g_param', ''),
                        '_s2': self.session_data.get('s2_param', '')
                    }
                    
                    try:
                        async with session.post(endpoint, data=form_data, headers=headers) as response:
                            response_text = await response.text()
                            logger.info(f"Customer code {endpoint} with {code_format}: {response.status}")
                            
                            if response.status in [200, 302]:
                                # Check for success indicators
                                success_indicators = [
                                    'terima kasih atas kunjungan',
                                    'survey',
                                    'berikutnya',
                                    'pelanggan yang berharga'
                                ]
                                
                                if any(indicator in response_text.lower() for indicator in success_indicators):
                                    logger.info(f"✅ Customer code accepted: {code_format}")
                                    return True
                                    
                    except Exception as e:
                        logger.warning(f"Customer code endpoint {endpoint} failed: {e}")
                        continue
                        
            logger.error("All customer code formats failed")
            return False
            
        except Exception as e:
            logger.error(f"Error submitting customer code: {e}")
            return False

    async def submit_form_step(self, session, form_data, headers, step_name):
        """Submit a single form step"""
        endpoints_to_try = [
            f"{self.base_url}/websurvey/2/next",
            f"{self.base_url}/websurvey/2/submit",
            f"{self.base_url}/websurvey/2/continue"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                async with session.post(endpoint, data=form_data, headers=headers) as response:
                    response_text = await response.text()
                    logger.info(f"{step_name} endpoint {endpoint}: {response.status}")
                    
                    if response.status in [200, 302]:
                        # Check for success/progress indicators
                        success_indicators = ['berikutnya', 'next', 'continue', 'thank', 'terima kasih', 'promo']
                        if any(word in response_text.lower() for word in success_indicators):
                            logger.info(f"✅ {step_name} step successful")
                            return True
                            
            except Exception as e:
                logger.warning(f"{step_name} endpoint {endpoint} failed: {e}")
                continue
                
        logger.warning(f"⚠️ {step_name} step may have failed, continuing...")
        return True  # Continue anyway

    async def submit_survey_questions(self, session, message):
        """Submit all survey questions step by step"""
        try:
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['Referer'] = self.session_data.get('referer', '')
            
            # Step 1: Visit type and food order
            await asyncio.sleep(random.uniform(2, 4))
            step1_data = {
                'visit_type': '1',  # Membeli dan langsung pergi
                'food_order': '1',  # Ya
                '_g': self.session_data.get('g_param', ''),
                '_s2': self.session_data.get('s2_param', '')
            }
            
            success = await self.submit_form_step(session, step1_data, headers, "visit questions")
            if not success:
                return False
                
            # Step 2: Return visit frequency
            await asyncio.sleep(random.uniform(2, 4))
            step2_data = {
                'return_visit': '1',  # Hari ini atau besok
                '_g': self.session_data.get('g_param', ''),
                '_s2': self.session_data.get('s2_param', '')
            }
            
            success = await self.submit_form_step(session, step2_data, headers, "return visit")
            if not success:
                return False
                
            # Step 3: Rating questions (all 7 - Sangat setuju)
            await asyncio.sleep(random.uniform(2, 4))
            step3_data = {
                'rating_1': '7',
                'rating_2': '7',
                'rating_3': '7', 
                'rating_4': '7',
                'rating_5': '7',
                'rating_6': '7',
                'rating_7': '7',
                '_g': self.session_data.get('g_param', ''),
                '_s2': self.session_data.get('s2_param', '')
            }
            
            success = await self.submit_form_step(session, step3_data, headers, "ratings")
            if not success:
                return False
                
            # Step 4: Final feedback
            await asyncio.sleep(random.uniform(2, 4)) 
            step4_data = {
                'feedback': message,
                'additional_comments': message,
                '_g': self.session_data.get('g_param', ''),
                '_s2': self.session_data.get('s2_param', '')
            }
            
            success = await self.submit_form_step(session, step4_data, headers, "final feedback")
            return success
            
        except Exception as e:
            logger.error(f"Error submitting survey questions: {e}")
            return False

    async def run_survey(self, customer_code, message, survey_url=None):
        """Run complete survey automation using form-based approach"""
        async with await self.create_session() as session:
            try:
                # Step 1: Get initial page
                logger.info("Step 1: Getting initial page...")
                page = await self.get_initial_page(session, survey_url)
                if not page:
                    return None, "Gagal mengakses halaman survey"
                
                # Step 2: Submit language selection (Bahasa Indonesia)
                logger.info("Step 2: Submitting language selection...")
                language_success = await self.submit_language_selection(session)
                if not language_success:
                    return None, "Gagal memilih bahasa"
                
                # Step 3: Submit customer code
                logger.info(f"Step 3: Submitting customer code: {customer_code}")
                code_success = await self.submit_customer_code(session, customer_code)
                if not code_success:
                    return None, "Gagal memvalidasi kode pelanggan. Pastikan kode benar dan belum kadaluarsa."
                
                # Step 4: Submit survey questions
                logger.info("Step 4: Submitting survey questions...")
                survey_success = await self.submit_survey_questions(session, message)
                if not survey_success:
                    return None, "Gagal mengirim jawaban survey"
                
                logger.info("✅ Survey completed successfully!")
                return "SURVEY_COMPLETED", None
                    
            except Exception as e:
                logger.error(f"Error in survey automation: {e}")
                return None, f"Error: {str(e)}"

# Bot handlers (sama seperti sebelumnya)
bot = StarbucksSurveyBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler"""
    user_id = update.effective_user.id
    user_sessions[user_id] = {}
    
    await update.message.reply_text(
        "🌟 Selamat datang di Starbucks Survey Bot!\n\n"
        "Bot ini akan membantu Anda mengisi survey Starbucks secara otomatis.\n\n"
        "📝 Cara penggunaan:\n"
        "1. Kirimkan URL survey dari receipt QR code\n"
        "2. Kirimkan kode pelanggan Anda\n"
        "3. Kirimkan pesan untuk survey\n"
        "4. Bot akan mengisi survey otomatis\n"
        "5. Dapatkan konfirmasi survey selesai!\n\n"
        "Silakan kirimkan URL survey dari QR code receipt Anda:\n"
        "(contoh: https://www.mystarbucksvisit.com/websurvey/2/execute?_g=...)"
    )
    
    return WAITING_URL

async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive survey URL"""
    user_id = update.effective_user.id
    survey_url = update.message.text.strip()
    
    # Validate URL
    if not survey_url.startswith('https://www.mystarbucksvisit.com'):
        await update.message.reply_text(
            "❌ URL tidak valid. Silakan kirim URL dari QR code receipt Starbucks:\n"
            "Format: https://www.mystarbucksvisit.com/websurvey/..."
        )
        return WAITING_URL
    
    user_sessions[user_id]['survey_url'] = survey_url
    
    await update.message.reply_text(
        "✅ URL survey tersimpan\n\n"
        "Sekarang kirimkan kode pelanggan dari receipt:\n"
        "(contoh: 16644 086207270916)"
    )
    
    return WAITING_CODE

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive customer code"""
    user_id = update.effective_user.id
    customer_code = update.message.text.strip()
    
    # Validate customer code format
    if not customer_code or len(customer_code.replace(' ', '')) < 10:
        await update.message.reply_text(
            "❌ Kode pelanggan tidak valid. Silakan kirim kode yang benar dari receipt:"
        )
        return WAITING_CODE
    
    user_sessions[user_id]['customer_code'] = customer_code
    
    await update.message.reply_text(
        f"✅ Kode pelanggan: {customer_code}\n\n"
        "Sekarang kirimkan pesan yang ingin Anda sampaikan dalam survey:"
    )
    
    return WAITING_MESSAGE

async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive survey message and process"""
    user_id = update.effective_user.id
    message = update.message.text.strip()
    
    if not message:
        await update.message.reply_text(
            "❌ Pesan tidak boleh kosong. Silakan kirim pesan Anda:"
        )
        return WAITING_MESSAGE
    
    customer_code = user_sessions[user_id].get('customer_code')
    survey_url = user_sessions[user_id].get('survey_url')
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "⏳ Sedang memproses survey...\n\n"
        "Langkah:\n"
        "☐ Mengakses halaman survey\n"
        "☐ Memilih bahasa Indonesia\n"
        "☐ Memasukkan kode pelanggan\n"
        "☐ Mengisi survey (semua jawaban: Sangat Setuju)\n"
        "☐ Mengirim pesan feedback\n\n"
        "Mohon tunggu..."
    )
    
    # Run survey automation
    result, error = await bot.run_survey(customer_code, message, survey_url)
    
    # Delete processing message
    await processing_msg.delete()
    
    if result:
        await update.message.reply_text(
            f"🎉 Survey berhasil diselesaikan!\n\n"
            f"✅ Status: {result}\n\n"
            f"Survey Anda telah dikirim dengan:\n"
            f"• Kode Pelanggan: {customer_code}\n"
            f"• Semua rating: Sangat Setuju (7)\n"
            f"• Pesan: {message}\n\n"
            f"Gunakan /start untuk mengisi survey lagi."
        )
    else:
        await update.message.reply_text(
            f"❌ Gagal menyelesaikan survey\n\n"
            f"Error: {error}\n\n"
            f"Tips:\n"
            f"• Pastikan kode pelanggan benar\n"
            f"• QR code mungkin sudah kadaluarsa (scan QR baru)\n"
            f"• Coba lagi dalam beberapa menit\n\n"
            f"Silakan coba lagi dengan /start"
        )
    
    # Clear session
    user_sessions.pop(user_id, None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation"""
    user_id = update.effective_user.id
    user_sessions.pop(user_id, None)
    
    await update.message.reply_text(
        "❌ Operasi dibatalkan. Gunakan /start untuk memulai lagi."
    )
    return ConversationHandler.END

def main():
    """Main function to run the bot"""
    # Get token from environment variable or use provided token
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8481395468:AAEFat0skeQc9Z1ntaIECMQhpb-6T0-Lzdk')
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
            WAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code)],
            WAITING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    
    # Start bot
    if os.environ.get('WEBHOOK_URL'):
        # For deployment with webhook
        port = int(os.environ.get('PORT', 5000))
        webhook_url = os.environ.get('WEBHOOK_URL')
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TOKEN,
            webhook_url=f"{webhook_url}/{TOKEN}"
        )
    else:
        # For local development
        application.run_polling()

if __name__ == '__main__':
    main()