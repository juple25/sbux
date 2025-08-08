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
from webdriver_manager.chrome import ChromeDriverManager
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
WAITING_CUSTOMER_CODE = 1

class StarbucksSurveyBot:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Setup Chrome WebDriver with proper configuration"""
        chrome_options = Options()
        
        # Set Chrome binary path explicitly
        chrome_options.binary_location = "/usr/bin/google-chrome"
        
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
        
        # Setup service with ChromeDriverManager but specify chrome binary
        try:
            service = Service(ChromeDriverManager(chrome_type=None).install())
            service.path = ChromeDriverManager().install()
        except:
            # Fallback to system chromedriver if available
            service = Service("/usr/local/bin/chromedriver")
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
        return self.driver
    
    def access_survey_page(self, customer_code: str) -> bool:
        """Access Starbucks survey page and enter customer code"""
        try:
            # Navigate to Starbucks survey page  
            survey_url = f"https://www.mystarbucksvisit.com/websurvey/2/execute?_g=NTAyMA%3D%3Dh&_s2=691c9ac9-0e05-497b-956f-cb929187a36a#!/1"
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
    
    def fill_survey_questions(self) -> bool:
        """Fill out all survey questions with positive responses"""
        try:
            # Select Indonesian language first
            self.select_language_indonesian()
            time.sleep(2)
            
            # Find all radio buttons and select positive answers (usually highest value)
            radio_groups = {}
            radio_buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            
            for radio in radio_buttons:
                name = radio.get_attribute('name')
                value = radio.get_attribute('value')
                
                if name and value:
                    if name not in radio_groups:
                        radio_groups[name] = []
                    radio_groups[name].append((radio, value))
            
            # Select highest value for each question (most positive response)
            for group_name, radios in radio_groups.items():
                try:
                    # Sort by value and select the highest (most positive)
                    radios.sort(key=lambda x: int(x[1]) if x[1].isdigit() else 0, reverse=True)
                    best_radio = radios[0][0]
                    
                    if best_radio.is_enabled():
                        self.driver.execute_script("arguments[0].click();", best_radio)
                        logger.info(f"Selected positive answer for question group: {group_name}")
                        
                except Exception as e:
                    logger.warning(f"Could not select radio for {group_name}: {str(e)}")
            
            # Handle dropdown selects
            selects = self.driver.find_elements(By.CSS_SELECTOR, "select")
            for select_element in selects:
                try:
                    select = Select(select_element)
                    options = select.options[1:]  # Skip first option (usually empty)
                    
                    if options:
                        # Select positive options
                        for option in options:
                            text = option.text.lower()
                            if any(keyword in text for keyword in ['strongly agree', 'sangat setuju', 'buy and go', 'yes', 'ya']):
                                select.select_by_visible_text(option.text)
                                logger.info(f"Selected dropdown option: {option.text}")
                                break
                        else:
                            # Default to first available option
                            select.select_by_index(1)
                            
                except Exception as e:
                    logger.warning(f"Could not handle select element: {str(e)}")
            
            # Fill text areas if any
            text_areas = self.driver.find_elements(By.CSS_SELECTOR, "textarea")
            for textarea in text_areas:
                try:
                    if not textarea.get_attribute('value'):
                        textarea.send_keys("Excellent service and great coffee quality!")
                        logger.info("Filled textarea with positive comment")
                except:
                    pass
            
            time.sleep(2)
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
    
    def run_complete_survey(self, customer_code: str) -> dict:
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
            if not self.access_survey_page(customer_code):
                result['message'] = "Failed to access survey page"
                return result
            
            # Fill survey questions
            if not self.fill_survey_questions():
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

Kirim customer code Anda untuk memulai survey otomatis.

⚠️ **Disclaimer**: Bot ini menggunakan browser automation yang sesungguhnya untuk mengisi survey Starbucks. Gunakan dengan bijak dan sesuai dengan terms of service Starbucks.

Kirimkan customer code Anda sekarang:
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    return WAITING_CUSTOMER_CODE

async def handle_customer_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle customer code input"""
    customer_code = update.message.text.strip()
    
    if len(customer_code) < 10:
        await update.message.reply_text(
            "❌ Customer code terlalu pendek. Pastikan Anda memasukkan code yang lengkap."
        )
        return WAITING_CUSTOMER_CODE
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🤖 Memproses survey dengan Selenium...\n"
        "⏳ Mohon tunggu, proses ini membutuhkan waktu 1-2 menit..."
    )
    
    # Run survey automation
    bot = StarbucksSurveyBot()
    result = await asyncio.get_event_loop().run_in_executor(
        None, bot.run_complete_survey, customer_code
    )
    
    # Send result
    if result['success']:
        response_message = f"""
✅ **Survey Berhasil Diselesaikan!**

🎁 **Promo Code**: `{result['promo_code']}`

Customer Code: `{customer_code}`
Status: {result['message']}

Terima kasih telah menggunakan bot survey automation!
        """
    else:
        response_message = f"""
❌ **Survey Gagal**

Customer Code: `{customer_code}`
Error: {result['message']}

Silakan coba lagi dengan customer code yang valid.
        """
    
    await processing_msg.edit_text(response_message, parse_mode='Markdown')
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
            WAITING_CUSTOMER_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_customer_code)
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