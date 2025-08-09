import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import re
from typing import Optional

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
        self.driver = None
        
    def setup_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Setup Chrome WebDriver with proper configuration"""
        chrome_options = Options()
        
        # Set Chrome binary path explicitly
        chrome_options.binary_location = os.getenv('CHROME_BIN', '/usr/bin/google-chrome')
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # Additional options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Use direct chromedriver path from environment
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
        logger.info(f"Using ChromeDriver at: {chromedriver_path}")
        service = Service(chromedriver_path)
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
        return self.driver
    
    def access_survey_page(self, survey_url: str, customer_code: str) -> bool:
        """Access Starbucks survey page and enter customer code"""
        try:
            logger.info(f"Navigating to: {survey_url}")
            
            self.driver.get(survey_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for customer code input field
            customer_code_input = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text']"))
            )
            
            # Enter customer code
            customer_code_input.clear()
            customer_code_input.send_keys(customer_code)
            
            # Find and click start button
            start_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit'], .start-btn, #start")
            start_button.click()
            
            # Wait for survey to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form, .survey-form, .question"))
            )
            
            logger.info("Successfully accessed survey page")
            return True
            
        except Exception as e:
            logger.error(f"Error accessing survey page: {str(e)}")
            return False
    
    def select_language_indonesian(self) -> bool:
        """Select Indonesian language if language selection is available"""
        try:
            # Look for language selector
            language_selectors = [
                "select[name*='lang']",
                "select[id*='lang']",
                ".language-select",
                "#language-selector"
            ]
            
            for selector in language_selectors:
                try:
                    language_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    select = Select(language_element)
                    
                    # Try to find Indonesian option
                    for option in select.options:
                        if any(keyword in option.text.lower() for keyword in ['indonesia', 'bahasa', 'id']):
                            select.select_by_visible_text(option.text)
                            logger.info("Selected Indonesian language")
                            return True
                            
                except:
                    continue
                    
            logger.info("No language selector found or Indonesian not available")
            return True
            
        except Exception as e:
            logger.error(f"Error selecting language: {str(e)}")
            return False
    
    def generate_customer_code(self) -> str:
        """Generate realistic customer code if needed"""
        import random
        import string
        
        # Generate format like: 16644 078108050916
        part1 = ''.join([str(random.randint(0,9)) for _ in range(5)])
        part2 = ''.join([str(random.randint(0,9)) for _ in range(12)])
        
        return f"{part1} {part2}"

    def fill_survey_questions(self, custom_message: str = None) -> bool:
        """Fill out all survey questions with positive responses and custom message"""
        try:
            # Select Indonesian language first
            self.select_language_indonesian()
            time.sleep(2)
            
            logger.info("🔍 Mencari semua pertanyaan survey...")
            
            # Find all radio buttons and select positive answers (value 7)
            radio_groups = {}
            radio_buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            
            for radio in radio_buttons:
                name = radio.get_attribute('name')
                value = radio.get_attribute('value')
                
                if name and value:
                    if name not in radio_groups:
                        radio_groups[name] = []
                    radio_groups[name].append((radio, value))
            
            # Select value 7 (highest rating) for each question
            question_count = 0
            for group_name, radios in radio_groups.items():
                try:
                    # Look for value 7 first, then highest available
                    target_radio = None
                    
                    # Try to find value 7 (Sangat Setuju)
                    for radio, value in radios:
                        if value == '7':
                            target_radio = radio
                            break
                    
                    # If no value 7, get highest value
                    if not target_radio:
                        radios.sort(key=lambda x: int(x[1]) if x[1].isdigit() else 0, reverse=True)
                        target_radio = radios[0][0]
                    
                    if target_radio and target_radio.is_enabled():
                        self.driver.execute_script("arguments[0].click();", target_radio)
                        question_count += 1
                        logger.info(f"✅ Pertanyaan {question_count}: Memilih nilai 7 (Sangat Setuju)")
                        time.sleep(1)  # Small delay between selections
                        
                except Exception as e:
                    logger.warning(f"Could not select radio for {group_name}: {str(e)}")
            
            # Handle dropdown selects with positive choices
            selects = self.driver.find_elements(By.CSS_SELECTOR, "select")
            for i, select_element in enumerate(selects):
                try:
                    select = Select(select_element)
                    options = select.options[1:]  # Skip first option (usually empty)
                    
                    if options:
                        # Select positive options in priority order
                        selected = False
                        positive_keywords = [
                            'buy and go', 'membeli dan langsung pergi',
                            'yes', 'ya', 
                            'strongly agree', 'sangat setuju',
                            'excellent', 'sangat baik',
                            'today', 'hari ini'
                        ]
                        
                        for keyword in positive_keywords:
                            for option in options:
                                if keyword in option.text.lower():
                                    select.select_by_visible_text(option.text)
                                    logger.info(f"✅ Dropdown {i+1}: Memilih '{option.text}'")
                                    selected = True
                                    break
                            if selected:
                                break
                        
                        # If no positive keyword found, select first available
                        if not selected:
                            select.select_by_index(1)
                            logger.info(f"✅ Dropdown {i+1}: Memilih opsi default")
                            
                except Exception as e:
                    logger.warning(f"Could not handle select element {i}: {str(e)}")
            
            # Fill text areas with custom message
            text_areas = self.driver.find_elements(By.CSS_SELECTOR, "textarea, input[type='text']:not([name*='code'])")
            for i, textarea in enumerate(text_areas):
                try:
                    if not textarea.get_attribute('value') or len(textarea.get_attribute('value').strip()) == 0:
                        message = custom_message if custom_message else "Pelayanan sangat memuaskan, barista ramah, minuman berkualitas tinggi. Terima kasih Starbucks!"
                        textarea.clear()
                        textarea.send_keys(message)
                        logger.info(f"✅ Pesan feedback: '{message[:50]}...'")
                except Exception as e:
                    logger.warning(f"Could not fill textarea {i}: {str(e)}")
            
            logger.info(f"🎯 Survey berhasil diisi: {question_count} pertanyaan rating dengan nilai 7")
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Error filling survey questions: {str(e)}")
            return False
    
    def submit_survey(self) -> bool:
        """Submit the completed survey"""
        try:
            # Look for submit buttons
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']", 
                ".submit-btn",
                "#submit",
                "button:contains('Submit')",
                "button:contains('Kirim')"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_button.is_enabled():
                        self.driver.execute_script("arguments[0].click();", submit_button)
                        logger.info("Survey submitted successfully")
                        time.sleep(3)
                        return True
                except:
                    continue
            
            # Try JavaScript submission
            self.driver.execute_script("document.forms[0].submit();")
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Error submitting survey: {str(e)}")
            return False
    
    def extract_promo_code(self) -> Optional[str]:
        """Extract promo code from the completion page"""
        try:
            # Wait for completion page
            time.sleep(5)
            
            # Look for promo code patterns
            promo_selectors = [
                ".promo-code",
                ".voucher-code", 
                "#promo-code",
                ".code",
                "[data-promo]"
            ]
            
            for selector in promo_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    code = element.text.strip()
                    if code and len(code) >= 4:
                        logger.info(f"Found promo code: {code}")
                        return code
                except:
                    continue
            
            # Search in page text for patterns like 5-digit codes
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            promo_pattern = r'\b[A-Z0-9]{5}\b'
            matches = re.findall(promo_pattern, page_text)
            
            if matches:
                logger.info(f"Extracted promo code from text: {matches[0]}")
                return matches[0]
                
            logger.warning("No promo code found on completion page")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting promo code: {str(e)}")
            return None
    
    def run_complete_survey(self, survey_url: str, customer_code: str, custom_message: str = None) -> dict:
        """Run the complete survey automation process"""
        result = {
            'success': False,
            'promo_code': None,
            'message': ''
        }
        
        try:
            # Setup driver
            self.setup_driver(headless=True)
            
            # Access survey page
            if not self.access_survey_page(survey_url, customer_code):
                result['message'] = "Failed to access survey page"
                return result
            
            # Fill survey questions with custom message
            if not self.fill_survey_questions(custom_message):
                result['message'] = "Failed to fill survey questions"
                return result
            
            # Submit survey
            if not self.submit_survey():
                result['message'] = "Failed to submit survey"
                return result
            
            # Extract promo code
            promo_code = self.extract_promo_code()
            
            if promo_code:
                result['success'] = True
                result['promo_code'] = promo_code
                result['message'] = "Survey completed successfully!"
            else:
                result['message'] = "Survey submitted but no promo code found"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in survey automation: {str(e)}")
            result['message'] = f"Error: {str(e)}"
            return result
            
        finally:
            if self.driver:
                self.driver.quit()

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
    result = await asyncio.get_event_loop().run_in_executor(
        None, bot.run_complete_survey, survey_url, customer_code, survey_message
    )
    
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

🎁 **Promo Code**: `{promo_code}`

📋 Customer Code: `{customer_code}`
📊 Status: {status_msg}

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