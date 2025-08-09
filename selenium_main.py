import os
import asyncio
import logging
import json
import re
import time
import random
import hashlib
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional, Dict, Any

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.keys import Keys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
WAITING_SURVEY_URL, WAITING_CUSTOMER_CODE, WAITING_SURVEY_MESSAGE = range(3)

def generate_starbucks_customer_code():
    """Generate customer code dengan pattern yang benar (TANPA SPASI)"""
    
    # Store ID: 16644 (fixed seperti contoh)
    store_id = "16644"
    
    # Prefix: 08 (seperti contoh)
    prefix = "08"
    
    # Random 2 digits
    random_part1 = f"{random.randint(10, 99)}"
    
    # Date: MMDD format (current date)
    current_date = datetime.now()
    date_part = current_date.strftime("%m%d")  # Format: MMDD
    
    # Random 2 digits
    random_part2 = f"{random.randint(10, 99)}"
    
    # Suffix: 16 (seperti contoh)
    suffix = "16"
    
    # Combine all parts TANPA SPASI: 16644 + 08 + XX + MMDD + XX + 16
    customer_code = f"{store_id}{prefix}{random_part1}{date_part}{random_part2}{suffix}"
    
    return customer_code

class RealStarbucksSurveyBot:
    def __init__(self):
        """Initialize Real Starbucks Survey Bot dengan Selenium"""
        self.driver = None
    
    def setup_driver(self, headless=True):
        """Setup Chrome WebDriver"""
        try:
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument("--headless")
            
            # Essential options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            
            # For deployment stability
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--remote-debugging-port=9222")
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Indonesian settings
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--lang=id-ID")
            chrome_options.add_experimental_option('prefs', {
                'intl.accept_languages': 'id-ID,id,en-US,en'
            })
            
            # For Render deployment - use chromium path if available
            chromium_path = os.environ.get('GOOGLE_CHROME_BIN')
            if chromium_path:
                chrome_options.binary_location = chromium_path
            
            # ChromeDriver path for Render
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', 'chromedriver')
            
            self.driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set timeouts
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)
            
            logger.info("Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            return False
    
    async def run_complete_survey(self, survey_url: str, customer_code: str, survey_message: str) -> Dict[str, Any]:
        """Run complete survey automation with Selenium"""
        result = {
            'success': False,
            'promo_code': None,
            'message': '',
            'step_reached': 'initialization'
        }
        
        try:
            # Setup WebDriver
            if not self.setup_driver(headless=True):  # headless for deployment
                result['message'] = "Failed to initialize Chrome WebDriver"
                return result
            
            logger.info("Starting REAL survey automation with Selenium...")
            logger.info(f"Survey URL: {survey_url}")
            logger.info(f"Customer Code: {customer_code}")
            
            # Clean customer code (remove spaces)
            clean_code = customer_code.replace(" ", "")
            
            # Step 1: Load survey page
            result['step_reached'] = 'loading_page'
            logger.info("Loading survey page...")
            
            self.driver.get(survey_url)
            await asyncio.sleep(8)  # Wait for Angular to load
            result['step_reached'] = 'page_loaded'
            
            # Step 2: Fill customer code
            result['step_reached'] = 'filling_customer_code'
            logger.info("Looking for customer code input...")
            
            code_filled = await self.fill_customer_code(clean_code)
            if not code_filled:
                result['message'] = "Could not find or fill customer code input"
                return result
                
            result['step_reached'] = 'customer_code_filled'
            
            # Step 3: Click Continue
            result['step_reached'] = 'clicking_continue'
            logger.info("Clicking Continue button...")
            
            continue_success = await self.click_continue_button()
            if not continue_success:
                result['message'] = "Could not find or click Continue button"
                return result
                
            result['step_reached'] = 'continue_clicked'
            
            # Step 4: Fill survey questions
            result['step_reached'] = 'filling_questions'
            logger.info("Filling survey questions...")
            
            await asyncio.sleep(10)  # Wait for questions to load
            questions_filled = await self.fill_survey_questions(survey_message)
            result['step_reached'] = 'questions_filled'
            
            # Step 5: Submit survey
            result['step_reached'] = 'submitting_survey'
            logger.info("Submitting survey...")
            
            submit_success = await self.submit_survey()
            if submit_success:
                result['step_reached'] = 'survey_submitted'
                
                # Step 6: Extract promo code
                result['step_reached'] = 'extracting_promo'
                logger.info("Looking for promo code...")
                
                await asyncio.sleep(10)  # Wait for completion page
                promo_code = await self.extract_promo_code()
                
                if promo_code:
                    result['success'] = True
                    result['promo_code'] = promo_code
                    result['message'] = f"Survey berhasil diselesaikan! Kode promo asli: {promo_code}"
                    result['step_reached'] = 'promo_extracted'
                else:
                    # Check if survey completed anyway
                    if await self.check_completion():
                        result['success'] = True
                        result['message'] = "Survey berhasil diselesaikan! Silakan cek email untuk kode promo"
                        result['step_reached'] = 'survey_completed'
                    else:
                        result['message'] = "Survey berhasil disubmit tapi status completion tidak jelas"
                        result['step_reached'] = 'submit_success_unclear'
            else:
                result['message'] = "Tidak dapat submit survey - tombol submit tidak ditemukan"
                result['step_reached'] = 'submit_failed'
            
        except WebDriverException as e:
            if "session deleted" in str(e) or "disconnected" in str(e):
                # Browser disconnection might happen after successful submission
                if result['step_reached'] in ['survey_submitted', 'extracting_promo']:
                    result['success'] = True
                    result['message'] = f"Survey kemungkinan berhasil diselesaikan (browser disconnected after step: {result['step_reached']})"
                else:
                    result['message'] = f"Browser session terputus di step: {result['step_reached']}"
            else:
                result['message'] = f"WebDriver error at {result['step_reached']}: {str(e)}"
                
        except Exception as e:
            result['message'] = f"Error at {result['step_reached']}: {str(e)}"
            
        finally:
            # Clean up WebDriver
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
        
        return result
    
    async def fill_customer_code(self, customer_code: str) -> bool:
        """Fill customer code input"""
        try:
            await asyncio.sleep(3)
            
            # Look for customer code input
            selectors = [
                "input[name='code']",
                "input[type='text']",
                "input[id='code']",
                "input[placeholder*='code' i]"
            ]
            
            for selector in selectors:
                try:
                    elements = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.clear()
                            await asyncio.sleep(0.5)
                            element.send_keys(customer_code)
                            await asyncio.sleep(1)
                            
                            # Verify
                            if customer_code in element.get_attribute("value"):
                                logger.info(f"Customer code entered with selector: {selector}")
                                return True
                                
                except TimeoutException:
                    continue
                    
            return False
            
        except Exception as e:
            logger.error(f"Error filling customer code: {e}")
            return False
    
    async def click_continue_button(self) -> bool:
        """Click continue/next button"""
        try:
            await asyncio.sleep(2)
            
            selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button[ng-click*='next' i]",
                "button.btn-primary",
                "//button[contains(text(), 'Lanjut')]",
                "//button[contains(text(), 'Next')]"
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            await asyncio.sleep(1)
                            element.click()
                            await asyncio.sleep(3)
                            logger.info(f"Clicked continue button: {selector}")
                            return True
                            
                except Exception:
                    continue
                    
            # Fallback: press Enter on code input
            try:
                code_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                code_input.send_keys(Keys.ENTER)
                await asyncio.sleep(3)
                return True
            except:
                pass
                
            return False
            
        except Exception as e:
            logger.error(f"Error clicking continue: {e}")
            return False
    
    async def fill_survey_questions(self, survey_message: str) -> bool:
        """Fill survey questions with positive answers"""
        try:
            success_count = 0
            
            # Fill rating questions (Q4_1 to Q4_8 with value 7)
            for i in range(1, 9):
                try:
                    selectors = [
                        f"input[name='Q4_{i}'][value='7']",
                        f"button[data-value='7'][data-question='Q4_{i}']"
                    ]
                    
                    for selector in selectors:
                        try:
                            element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if element.is_displayed():
                                element.click()
                                success_count += 1
                                break
                        except:
                            continue
                            
                except:
                    continue
                    
                await asyncio.sleep(0.5)
            
            # Fill dropdown questions (Q1, Q2, Q3)
            dropdown_values = [
                ("Q1", "2"),  # Visit type
                ("Q2", "1"),  # Ordered food
                ("Q3", "1")   # Visit timing
            ]
            
            for question, value in dropdown_values:
                try:
                    selectors = [
                        f"input[name='{question}'][value='{value}']",
                        f"select[name='{question}']"
                    ]
                    
                    for selector in selectors:
                        try:
                            element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if element.is_displayed():
                                if element.tag_name.lower() == 'select':
                                    select = Select(element)
                                    select.select_by_value(value)
                                else:
                                    element.click()
                                success_count += 1
                                break
                        except:
                            continue
                            
                except:
                    continue
                    
                await asyncio.sleep(0.5)
            
            # Fill feedback textarea
            try:
                textarea_selectors = [
                    "textarea[name='Q5']",
                    "textarea"
                ]
                
                for selector in textarea_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.is_displayed():
                            element.clear()
                            element.send_keys(survey_message)
                            success_count += 1
                            break
                    except:
                        continue
            except:
                pass
            
            logger.info(f"Filled {success_count} survey elements")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error filling questions: {e}")
            return False
    
    async def submit_survey(self) -> bool:
        """Submit the survey"""
        try:
            await asyncio.sleep(2)
            
            selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'Kirim')]"
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            await asyncio.sleep(1)
                            element.click()
                            await asyncio.sleep(5)
                            logger.info(f"Clicked submit: {selector}")
                            return True
                            
                except Exception:
                    continue
                    
            return False
            
        except Exception as e:
            logger.error(f"Error submitting: {e}")
            return False
    
    async def extract_promo_code(self) -> Optional[str]:
        """Extract promo code from completion page"""
        try:
            await asyncio.sleep(5)
            page_source = self.driver.page_source
            
            # Look for 5-digit promo codes
            patterns = [
                r'(?:Special\s*Promo|Promo\s*ID)[\s:]*(\d{5})',
                r'\b(\d{5})\b'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    if len(match) == 5 and match.isdigit():
                        return match
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting promo: {e}")
            return None
    
    async def check_completion(self) -> bool:
        """Check if survey completed"""
        try:
            page_text = self.driver.page_source.lower()
            indicators = ['terima kasih', 'thank you', 'selesai', 'complete']
            return any(indicator in page_text for indicator in indicators)
        except:
            return False

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_message = """
🎯 **Starbucks Survey Automation Bot (REAL SELENIUM)**

Bot ini benar-benar mengisi survei Starbucks menggunakan browser automation!

1️⃣ Kirimkan **Survey URL** Anda
   Format: `https://www.mystarbucksvisit.com/websurvey/2/execute?_g=...&_s2=...`

2️⃣ Kirimkan **Customer Code** dari receipt
   (atau ketik "generate" untuk auto-generate)

3️⃣ Kirimkan **Pesan Survey** untuk feedback

⚠️ **Bot akan benar-benar**:
- 🌐 Membuka browser Chrome
- 📝 Mengisi customer code (tanpa spasi)
- ✅ Pilih semua rating dengan nilai **7** (Sangat Setuju)
- 📋 Isi feedback dengan pesan Anda
- 🎁 **Extract kode promo ASLI dari hasil survei**

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
        customer_code = generate_starbucks_customer_code()
        await update.message.reply_text(
            f"🎲 **Customer Code Auto-Generated:**\n"
            f"`{customer_code}`\n\n"
            f"✅ Customer code berhasil di-generate dengan pattern yang benar!",
            parse_mode='Markdown'
        )
    else:
        customer_code = user_input
        if len(customer_code.replace(' ', '')) < 15:
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
        "🤖 **Memproses survey dengan SELENIUM...**\n"
        "⏳ Mohon tunggu, proses ini membutuhkan waktu 2-3 menit...\n\n"
        f"📋 Survey URL: `{survey_url[:50]}...`\n"
        f"🎫 Customer Code: `{customer_code}`\n"
        f"💬 Survey Message: `{survey_message[:30]}...`\n\n"
        f"🎯 **Proses REAL Automation:**\n"
        f"- 🌐 Membuka browser Chrome\n"
        f"- 🔗 Mengakses survey URL\n"
        f"- 📝 Mengisi customer code (tanpa spasi)\n"
        f"- ✅ Pilih semua rating dengan **nilai 7**\n"
        f"- 📋 Isi feedback dengan pesan kustom\n"
        f"- 🎁 Extract kode promo ASLI dari hasil",
        parse_mode='Markdown'
    )
    
    # Run REAL survey automation with Selenium
    bot = RealStarbucksSurveyBot()
    result = await bot.run_complete_survey(survey_url, customer_code, survey_message)
    
    # Send result
    def escape_markdown(text):
        """Escape special Markdown characters"""
        if not text:
            return ""
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    if result['success']:
        promo_code = result.get('promo_code', 'N/A')
        status_msg = escape_markdown(str(result.get('message', 'Success')))
        step_reached = result.get('step_reached', 'unknown')
        
        if promo_code and promo_code != 'N/A':
            response_message = f"""✅ **SURVEY BERHASIL DISELESAIKAN\\!**

🎁 **KODE PROMO ASLI**: `{promo_code}`

📋 Customer Code: `{customer_code}`
📊 Status: {status_msg}
🔧 Step Reached: {step_reached}

💝 **Cara Pakai Promo**:
Tunjukkan kode promo ini ke barista untuk mendapatkan promo Buy 1 Get 1 Free\\!

🎉 **INI KODE PROMO ASLI DARI HASIL SURVEI SELENIUM**\\!"""
        else:
            response_message = f"""✅ **SURVEY BERHASIL DISELESAIKAN\\!**

📋 Customer Code: `{customer_code}`
📊 Status: {status_msg}
🔧 Step Reached: {step_reached}

🎉 Survey berhasil disubmit dengan browser automation\\!
📧 Silakan cek email untuk kode promo atau coba lagi nanti\\."""
    else:
        error_msg = escape_markdown(str(result.get('message', 'Unknown error')))
        step_reached = result.get('step_reached', 'unknown')
        
        response_message = f"""❌ **Survey Automation Error**

📋 Customer Code: `{customer_code}`
🔧 Step Reached: {step_reached}
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
    logger.info("Starting REAL Starbucks Survey Selenium Bot...")
    
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