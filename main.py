import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import aiohttp
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import unquote, quote
import re
import uuid

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States untuk conversation
WAITING_CODE, WAITING_MESSAGE = range(2)

# Data storage untuk session
user_sessions = {}

class StarbucksSurveyBot:
    def __init__(self):
        self.base_url = "https://www.mystarbucksvisit.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    async def create_session(self):
        """Create aiohttp session with headers"""
        return aiohttp.ClientSession(headers=self.headers)

    def generate_session_id(self):
        """Generate new session ID"""
        return str(uuid.uuid4())

    async def get_initial_page(self, session):
        """Get initial survey page - try multiple approaches"""
        try:
            # Try with Indonesian language directly
            session_id = self.generate_session_id()
            url = f"{self.base_url}/websurvey/2/execute?_g=NTAyMA%3D%3Dh&_s2={session_id}&language=id#!/2"
            logger.info(f"Generated new session ID: {session_id}")
            logger.info(f"Trying URL with Indonesian language: {url}")
            
            async with session.get(url) as response:
                response_text = await response.text()
                if response.status == 200 and 'gateway error' not in response_text.lower():
                    logger.info("Direct Indonesian URL successful")
                    return response_text
                else:
                    logger.warning(f"Direct Indonesian URL failed: {response.status}")
            
            # Fallback: try without language parameter
            url2 = f"{self.base_url}/websurvey/2/execute?_g=NTAyMA%3D%3Dh&_s2={session_id}#!/1"
            logger.info(f"Trying fallback URL: {url2}")
            
            async with session.get(url2) as response:
                response_text = await response.text()
                if response.status == 200:
                    return response_text
                else:
                    logger.error(f"Failed to get initial page: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting initial page: {e}")
            return None

    async def submit_language(self, session, page_content):
        """Submit Indonesian language selection"""
        try:
            # Parse form data from page
            soup = BeautifulSoup(page_content, 'html.parser')
            form = soup.find('form')
            if not form:
                logger.error("No form found on language page")
                logger.info(f"Language page content: {page_content[:1000]}")
                return None
            
            # Debug: Log form details
            logger.info(f"Language form action: {form.get('action', '')}")
            
            # Look for language selection elements
            select_elements = form.find_all('select')
            radio_elements = form.find_all('input', type='radio')
            
            logger.info(f"Found {len(select_elements)} select elements and {len(radio_elements)} radio elements")
            
            # Extract form action and data
            action = form.get('action', '')
            form_data = {}
            
            # Check for language dropdown
            for select in select_elements:
                name = select.get('name', '')
                if 'language' in name.lower() or 'lang' in name.lower():
                    form_data[name] = 'id'  # Indonesian
                    logger.info(f"Set language field '{name}' to 'id'")
            
            # Check for language radio buttons
            for radio in radio_elements:
                value = radio.get('value', '')
                if value == 'id' or 'indo' in value.lower():
                    form_data[radio.get('name', '')] = value
                    logger.info(f"Set radio field '{radio.get('name')}' to '{value}'")
            
            # Fallback to default language field
            if not any('language' in key.lower() or 'lang' in key.lower() for key in form_data.keys()):
                form_data['language'] = 'id'
            
            # Add submit button value
            submit_buttons = form.find_all('input', type='submit') + form.find_all('button', type='submit')
            for submit in submit_buttons:
                value = submit.get('value', submit.get_text(strip=True))
                if value:
                    form_data['_submit'] = value
                    break
            else:
                form_data['_submit'] = 'Continue'
            
            # Add hidden fields
            for hidden in form.find_all('input', type='hidden'):
                form_data[hidden.get('name', '')] = hidden.get('value', '')
            
            logger.info(f"Language form data: {form_data}")
            
            # Submit form
            async with session.post(f"{self.base_url}{action}", data=form_data) as response:
                response_text = await response.text()
                if response.status == 200:
                    logger.info(f"Language submission successful, response length: {len(response_text)}")
                    # Log first part of response to debug
                    logger.info(f"Response preview: {response_text[:500]}")
                    return response_text
                else:
                    logger.error(f"Failed to submit language: {response.status}")
                    logger.error(f"Response: {response_text[:500]}")
                    return None
        except Exception as e:
            logger.error(f"Error submitting language: {e}")
            return None

    async def submit_customer_code(self, session, page_content, customer_code):
        """Submit customer code"""
        try:
            soup = BeautifulSoup(page_content, 'html.parser')
            form = soup.find('form')
            if not form:
                logger.error("No form found on customer code page")
                return None
            
            action = form.get('action', '')
            
            # Debug: Log all input fields to find correct field name
            input_fields = form.find_all('input')
            logger.info(f"Found {len(input_fields)} input fields:")
            for inp in input_fields:
                logger.info(f"  Input: name='{inp.get('name')}', type='{inp.get('type')}', placeholder='{inp.get('placeholder')}'")
            
            # Format customer code with space (as shown on receipt)
            formatted_code = customer_code.replace(' ', '')  # Remove existing spaces
            if len(formatted_code) >= 12:  # If long enough, add space after 5th digit
                formatted_code = f"{formatted_code[:5]} {formatted_code[5:]}"
            
            # Try different possible field names
            possible_names = ['customerCode', 'customer_code', 'code', 'surveyCode', 'receipt_code']
            customer_field_name = None
            
            for inp in input_fields:
                if inp.get('type') == 'text' or inp.get('type') is None:
                    name = inp.get('name', '')
                    if any(possible in name.lower() for possible in ['customer', 'code', 'receipt']):
                        customer_field_name = name
                        break
            
            if not customer_field_name:
                customer_field_name = 'customerCode'  # fallback
            
            form_data = {
                customer_field_name: formatted_code,
                '_submit': 'Berikutnya'
            }
            
            # Add hidden fields
            for hidden in form.find_all('input', type='hidden'):
                form_data[hidden.get('name', '')] = hidden.get('value', '')
            
            logger.info(f"Submitting customer code with field '{customer_field_name}': '{formatted_code}'")
            logger.info(f"Form data: {form_data}")
            
            async with session.post(f"{self.base_url}{action}", data=form_data) as response:
                response_text = await response.text()
                if response.status == 200:
                    # Check if submission was successful by looking for error messages
                    if 'error' in response_text.lower() or 'invalid' in response_text.lower():
                        logger.error(f"Customer code rejected by server")
                        return None
                    return response_text
                else:
                    logger.error(f"Failed to submit customer code: {response.status}")
                    logger.error(f"Response: {response_text[:500]}")
                    return None
        except Exception as e:
            logger.error(f"Error submitting customer code: {e}")
            return None

    async def submit_survey_answers(self, session, page_content):
        """Submit all survey answers with 7 (Sangat Setuju)"""
        try:
            current_page = page_content
            
            while True:
                soup = BeautifulSoup(current_page, 'html.parser')
                form = soup.find('form')
                if not form:
                    break
                
                action = form.get('action', '')
                form_data = {}
                
                # Add hidden fields
                for hidden in form.find_all('input', type='hidden'):
                    form_data[hidden.get('name', '')] = hidden.get('value', '')
                
                # Find all radio buttons and select highest value (7)
                radio_groups = {}
                for radio in form.find_all('input', type='radio'):
                    name = radio.get('name', '')
                    value = radio.get('value', '')
                    if name and value:
                        if name not in radio_groups or int(value) > int(radio_groups[name]):
                            radio_groups[name] = value
                
                # Add radio selections
                form_data.update(radio_groups)
                
                # Check for dropdowns and select appropriate values
                for select in form.find_all('select'):
                    name = select.get('name', '')
                    if 'visit_type' in name:
                        form_data[name] = 'direct'  # Membeli langsung pergi
                    elif 'return' in name:
                        form_data[name] = 'yes'  # Ya
                    elif 'day' in name:
                        form_data[name] = 'today'  # Hari ini
                
                form_data['_submit'] = 'Berikutnya'
                
                # Submit form
                async with session.post(f"{self.base_url}{action}", data=form_data) as response:
                    if response.status == 200:
                        current_page = await response.text()
                        
                        # Check if we've reached the message page
                        if 'textarea' in current_page or 'message' in current_page.lower():
                            return current_page
                    else:
                        logger.error(f"Failed to submit survey answer: {response.status}")
                        return None
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error submitting survey answers: {e}")
            return None

    async def submit_message(self, session, page_content, message):
        """Submit final message"""
        try:
            soup = BeautifulSoup(page_content, 'html.parser')
            form = soup.find('form')
            if not form:
                return None
            
            action = form.get('action', '')
            form_data = {
                'message': message,
                '_submit': 'Kirim'
            }
            
            # Add hidden fields
            for hidden in form.find_all('input', type='hidden'):
                form_data[hidden.get('name', '')] = hidden.get('value', '')
            
            async with session.post(f"{self.base_url}{action}", data=form_data) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Failed to submit message: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error submitting message: {e}")
            return None

    async def extract_promo_code(self, page_content):
        """Extract promo code from final page"""
        try:
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Look for promo code in various possible locations
            promo_patterns = [
                r'[A-Z0-9]{6,12}',  # Common promo code format
                r'ID.*?([A-Z0-9]{6,})',  # ID followed by code
                r'kode.*?([A-Z0-9]{6,})',  # kode followed by code
                r'promo.*?([A-Z0-9]{6,})'  # promo followed by code
            ]
            
            text = soup.get_text()
            for pattern in promo_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1) if match.groups() else match.group(0)
            
            # Look in specific elements
            for elem in soup.find_all(['div', 'span', 'p', 'h1', 'h2', 'h3', 'h4']):
                if 'promo' in elem.get_text().lower() or 'kode' in elem.get_text().lower():
                    # Extract alphanumeric codes
                    codes = re.findall(r'[A-Z0-9]{6,12}', elem.get_text())
                    if codes:
                        return codes[0]
            
            return None
        except Exception as e:
            logger.error(f"Error extracting promo code: {e}")
            return None

    async def run_survey(self, customer_code, message):
        """Run complete survey automation"""
        async with await self.create_session() as session:
            try:
                # Step 1: Get initial page
                logger.info("Getting initial page...")
                page = await self.get_initial_page(session)
                if not page:
                    return None, "Gagal mengakses halaman survey"
                
                # Step 2: Select Indonesian language (skip if already on customer code page)
                if 'customer' in page.lower() or 'kode' in page.lower():
                    logger.info("Already on customer code page, skipping language selection")
                else:
                    logger.info("Selecting Indonesian language...")
                    page = await self.submit_language(session, page)
                    if not page:
                        return None, "Gagal memilih bahasa"
                
                # Step 3: Submit customer code
                logger.info(f"Submitting customer code: {customer_code}")
                page = await self.submit_customer_code(session, page, customer_code)
                if not page:
                    return None, "Gagal memasukkan kode pelanggan. Pastikan kode valid."
                
                # Step 4: Submit all survey answers
                logger.info("Submitting survey answers...")
                page = await self.submit_survey_answers(session, page)
                if not page:
                    return None, "Gagal mengisi survey"
                
                # Step 5: Submit message
                logger.info("Submitting message...")
                page = await self.submit_message(session, page, message)
                if not page:
                    return None, "Gagal mengirim pesan"
                
                # Step 6: Extract promo code
                logger.info("Extracting promo code...")
                promo_code = await self.extract_promo_code(page)
                if promo_code:
                    return promo_code, None
                else:
                    return None, "Tidak dapat menemukan kode promo"
                    
            except Exception as e:
                logger.error(f"Error in survey automation: {e}")
                return None, f"Error: {str(e)}"

# Bot handlers
bot = StarbucksSurveyBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler"""
    user_id = update.effective_user.id
    user_sessions[user_id] = {}
    
    await update.message.reply_text(
        "🌟 *Selamat datang di Starbucks Survey Bot!*\n\n"
        "Bot ini akan membantu Anda mengisi survey Starbucks secara otomatis.\n\n"
        "📝 *Cara penggunaan:*\n"
        "1. Kirimkan kode pelanggan Anda\n"
        "2. Kirimkan pesan untuk survey\n"
        "3. Bot akan mengisi survey otomatis\n"
        "4. Dapatkan kode promo Anda!\n\n"
        "Silakan kirimkan *kode pelanggan* Anda:",
        parse_mode='Markdown'
    )
    
    return WAITING_CODE

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive customer code"""
    user_id = update.effective_user.id
    customer_code = update.message.text.strip()
    
    # Validate customer code format (adjust as needed)
    if not customer_code or len(customer_code) < 5:
        await update.message.reply_text(
            "❌ Kode pelanggan tidak valid. Silakan kirim kode yang benar:"
        )
        return WAITING_CODE
    
    user_sessions[user_id]['customer_code'] = customer_code
    
    await update.message.reply_text(
        f"✅ Kode pelanggan: `{customer_code}`\n\n"
        "Sekarang kirimkan *pesan* yang ingin Anda sampaikan dalam survey:",
        parse_mode='Markdown'
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
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "⏳ *Sedang memproses survey...*\n\n"
        "Langkah:\n"
        "☐ Mengakses halaman survey\n"
        "☐ Memilih bahasa Indonesia\n"
        "☐ Memasukkan kode pelanggan\n"
        "☐ Mengisi survey (semua jawaban: Sangat Setuju)\n"
        "☐ Mengirim pesan\n"
        "☐ Mendapatkan kode promo\n\n"
        "Mohon tunggu...",
        parse_mode='Markdown'
    )
    
    # Run survey automation
    promo_code, error = await bot.run_survey(customer_code, message)
    
    # Delete processing message
    await processing_msg.delete()
    
    if promo_code:
        await update.message.reply_text(
            f"🎉 *Survey berhasil diselesaikan!*\n\n"
            f"🎁 *Kode Promo Anda:* `{promo_code}`\n\n"
            f"📱 Tunjukkan kode ini di Starbucks untuk mendapatkan promo!\n\n"
            f"Gunakan /start untuk mengisi survey lagi.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ *Gagal menyelesaikan survey*\n\n"
            f"Error: {error}\n\n"
            f"Silakan coba lagi dengan /start",
            parse_mode='Markdown'
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
