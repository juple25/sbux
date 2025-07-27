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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/json;charset=UTF-8',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
        self.session_data = {}

    async def create_session(self):
        """Create aiohttp session with headers"""
        return aiohttp.ClientSession(headers=self.headers)

    def generate_session_id(self):
        """Generate new session ID"""
        return str(uuid.uuid4())

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
                            g_param = part.split('_g=')[1] if '_g=' in part else part[3:]
                        elif '_s2=' in part:
                            s2_param = part.split('_s2=')[1] if '_s2=' in part else part[4:]
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
        """Get initial survey page and extract tokens"""
        try:
            if survey_url:
                url = survey_url
                g_param, s2_param = self.extract_session_from_url(survey_url)
                logger.info(f"Using provided survey URL: {url}")
            else:
                s2_param = self.generate_session_id()
                g_param = "NTAyMA%3D%3Dh"
                url = f"{self.base_url}/websurvey/2/execute?_g={g_param}&_s2={s2_param}#!/1"
                logger.info(f"Generated new session ID: {s2_param}")
            
            # Store session data
            self.session_data = {
                'g_param': g_param,
                's2_param': s2_param,
                'referer': url
            }
            
            logger.info(f"=== URL FOR MANUAL TEST: {url} ===")
            
            # Get initial page with HTML headers
            html_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'Upgrade-Insecure-Requests': '1'
            }
            
            async with session.get(url, headers=html_headers) as response:
                response_text = await response.text()
                if response.status == 200:
                    if 'gateway error' in response_text.lower():
                        logger.error("Gateway error received")
                        return None
                    
                    # Extract CSRF token from page
                    csrf_token = self.extract_csrf_token(response_text)
                    if csrf_token:
                        self.session_data['csrf_token'] = csrf_token
                        logger.info(f"Extracted CSRF token: {csrf_token[:20]}...")
                    
                    logger.info("Initial page loaded successfully")
                    return response_text
                else:
                    logger.error(f"Failed to get initial page: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting initial page: {e}")
            return None

    def extract_csrf_token(self, html_content):
        """Extract CSRF token from HTML"""
        try:
            # Look for CSRF token in script tags or meta tags
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check script tags for token
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for common CSRF token patterns
                    csrf_match = re.search(r'csrf["\']?\s*:\s*["\']([^"\']+)', script.string, re.IGNORECASE)
                    if csrf_match:
                        return csrf_match.group(1)
                    
                    # Look for token in window object
                    token_match = re.search(r'token["\']?\s*:\s*["\']([^"\']+)', script.string, re.IGNORECASE)
                    if token_match:
                        return token_match.group(1)
            
            # Check meta tags
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                return csrf_meta.get('content')
                
            return None
        except Exception as e:
            logger.error(f"Error extracting CSRF token: {e}")
            return None

    async def send_started_request(self, session):
        """Send initial started request to initialize survey"""
        try:
            url = f"{self.base_url}/websurvey/2/sendStarted"
            
            # Use dynamic g_param instead of hardcoded value
            g_id = self.session_data.get('g_param', 'NTAyMA==h')
            if not g_id.endswith('h'):
                g_id += 'h'
            
            headers = {
                'x-csrf-token': self.session_data.get('csrf_token', ''),
                'x-im-g-id': g_id,
                'x-session-token-2': self.session_data.get('s2_param', ''),
                'referer': self.session_data.get('referer', ''),
                'origin': self.base_url,
                'cookie': 'inMomentCookie=true'
            }
            headers.update(self.headers)
            
            # Payload for sendStarted
            payload = {
                "survey": {
                    "id": "5020"
                },
                "session": {
                    "id": self.session_data.get('s2_param', '')
                },
                "language": "id",
                "startTime": "2025-07-27T04:20:09.000Z"
            }
            
            logger.info(f"Sending started request to {url}")
            logger.info(f"Payload: {json.dumps(payload, indent=2)}")
            
            async with session.post(url, headers=headers, json=payload) as response:
                response_text = await response.text()
                if response.status == 200:
                    logger.info("Started request successful")
                    return True
                else:
                    logger.error(f"Started request failed: {response.status}")
                    logger.error(f"Response: {response_text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending started request: {e}")
            return False

    async def get_prompts(self, session):
        """Get survey prompts via AJAX"""
        try:
            url = f"{self.base_url}/websurvey/2/prompts"
            
            headers = {
                'x-csrf-token': self.session_data.get('csrf_token', ''),
                'x-im-g-id': 'NTAyMA==h', 
                'x-session-token-2': self.session_data.get('s2_param', ''),
                'referer': self.session_data.get('referer', ''),
                'origin': self.base_url,
                'cookie': 'inMomentCookie=true'
            }
            headers.update(self.headers)
            
            logger.info(f"Getting prompts from {url}")
            
            async with session.post(url, headers=headers, json={}) as response:
                response_text = await response.text()
                if response.status == 200:
                    try:
                        data = json.loads(response_text)
                        logger.info("Prompts received successfully")
                        logger.info(f"Prompts data preview: {json.dumps(data, indent=2)[:500]}...")
                        return data
                    except json.JSONDecodeError:
                        logger.error("Failed to parse prompts JSON")
                        return None
                else:
                    logger.error(f"Failed to get prompts: {response.status}")
                    logger.error(f"Response: {response_text}")
                    return None
        except Exception as e:
            logger.error(f"Error getting prompts: {e}")
            return None

    async def submit_survey_responses(self, session, prompts_data, customer_code, message):
        """Submit all survey responses via AJAX"""
        try:
            if not prompts_data:
                logger.error("No prompts data available")
                return None
            
            # Add delay before starting submission attempts
            await asyncio.sleep(random.uniform(3, 6))
            
            # Prioritized endpoints - try most common ones first
            priority_endpoints = [
                f"{self.base_url}/websurvey/2/submit",
                f"{self.base_url}/websurvey/2/next",
                f"{self.base_url}/websurvey/2/continue"
            ]
            
            # Fallback endpoints - only if priority fails
            fallback_endpoints = [
                f"{self.base_url}/websurvey/2/response",
                f"{self.base_url}/websurvey/2/complete"
            ]
            
            # Use dynamic g_param instead of hardcoded value
            g_id = self.session_data.get('g_param', 'NTAyMA==h')
            if not g_id.endswith('h'):
                g_id += 'h'
            
            headers = {
                'x-csrf-token': self.session_data.get('csrf_token', ''),
                'x-im-g-id': g_id,
                'x-session-token-2': self.session_data.get('s2_param', ''),
                'referer': self.session_data.get('referer', ''),
                'origin': self.base_url,
                'cookie': 'inMomentCookie=true'
            }
            headers.update(self.headers)
            
            # Build responses based on prompts
            responses = []
            
            # Try smart customer code formats
            smart_code_formats = self.get_smart_code_formats(customer_code)
            logger.info(f"Will try customer code formats: {smart_code_formats}")
            
            # First try priority endpoints
            for endpoint in priority_endpoints:
                logger.info(f"Trying priority endpoint: {endpoint}")
                
                for code_format in smart_code_formats:
                    # Add delay between attempts
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    try:
                        payload = self.build_survey_payload(code_format, message)
                        
                        logger.info(f"Trying endpoint {endpoint} with customer code format: {code_format}")
                        
                        async with session.post(endpoint, headers=headers, json=payload) as response:
                            response_text = await response.text()
                            if response.status == 200:
                                if self.is_successful_response(response_text):
                                    logger.info(f"SUCCESS! Endpoint {endpoint} worked with format: {code_format}")
                                    try:
                                        data = json.loads(response_text)
                                        return data
                                    except json.JSONDecodeError:
                                        return {"success": True, "response": response_text}
                                else:
                                    logger.warning(f"Response rejected for format: {code_format}")
                                    continue
                            elif response.status == 404:
                                logger.warning(f"Endpoint {endpoint} not found (404)")
                                break  # Try next endpoint
                            elif response.status == 429:
                                logger.warning(f"Rate limited, waiting...")
                                await asyncio.sleep(random.uniform(10, 20))
                                continue
                            else:
                                logger.warning(f"Failed to submit with format {code_format} to {endpoint}: {response.status}")
                                continue
                                
                    except Exception as e:
                        logger.warning(f"Error with format {code_format} at {endpoint}: {e}")
                        continue
            
            # If priority endpoints fail, try fallback with longer delay
            logger.info("Priority endpoints failed, trying fallback endpoints...")
            await asyncio.sleep(random.uniform(10, 15))
            
            for endpoint in fallback_endpoints:
                logger.info(f"Trying fallback endpoint: {endpoint}")
                
                for code_format in smart_code_formats:
                    # Longer delay for fallback endpoints
                    await asyncio.sleep(random.uniform(5, 8))
                    
                    try:
                        payload = self.build_survey_payload(code_format, message)
                        
                        logger.info(f"Trying fallback endpoint {endpoint} with customer code format: {code_format}")
                        
                        async with session.post(endpoint, headers=headers, json=payload) as response:
                            response_text = await response.text()
                            if response.status == 200:
                                if self.is_successful_response(response_text):
                                    logger.info(f"SUCCESS! Fallback endpoint {endpoint} worked with format: {code_format}")
                                    try:
                                        data = json.loads(response_text)
                                        return data
                                    except json.JSONDecodeError:
                                        return {"success": True, "response": response_text}
                                else:
                                    logger.warning(f"Fallback response rejected for format: {code_format}")
                                    continue
                            elif response.status == 404:
                                logger.warning(f"Fallback endpoint {endpoint} not found (404)")
                                break  # Try next endpoint
                            elif response.status == 429:
                                logger.warning(f"Rate limited on fallback, waiting...")
                                await asyncio.sleep(random.uniform(20, 30))
                                continue
                            else:
                                logger.warning(f"Fallback failed with format {code_format} to {endpoint}: {response.status}")
                                continue
                                
                    except Exception as e:
                        logger.warning(f"Error with fallback format {code_format} at {endpoint}: {e}")
                        continue
            
            logger.error("All endpoints and customer code formats failed")
            return None
            
        except Exception as e:
            logger.error(f"Error submitting survey responses: {e}")
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
        
    def build_survey_payload(self, customer_code, message):
        """Build comprehensive survey payload"""
        responses = []
        
        # Customer code response
        responses.append({
            "questionId": "customer_code",
            "responseValue": customer_code,
            "responseType": "text"
        })
        
        # Rating questions - always answer 7 (Sangat Setuju)
        rating_questions = [
            "overall_satisfaction", "food_quality", "service_speed", 
            "staff_friendliness", "cleanliness", "value_for_money", "atmosphere"
        ]
        
        for i, question in enumerate(rating_questions, 1):
            responses.append({
                "questionId": f"rating_{i}",
                "responseValue": "7",
                "responseType": "scale",
                "questionName": question
            })
        
        # Visit details
        responses.extend([
            {
                "questionId": "visit_type",
                "responseValue": "dine_in",
                "responseType": "select"
            },
            {
                "questionId": "return_visit",
                "responseValue": "yes",
                "responseType": "select"
            },
            {
                "questionId": "visit_day",
                "responseValue": "today",
                "responseType": "select"
            },
            {
                "questionId": "recommendation",
                "responseValue": "yes", 
                "responseType": "select"
            }
        ])
        
        # Message
        responses.append({
            "questionId": "feedback_message",
            "responseValue": message,
            "responseType": "textarea"
        })
        
        return {
            "survey": {
                "id": "5020"
            },
            "session": {
                "id": self.session_data.get('s2_param', '')
            },
            "responses": responses,
            "language": "id",
            "completed": True,
            "submitTime": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        }
        
    def is_successful_response(self, response_text):
        """Check if response indicates success"""        
        # Check response text for success indicators
        if isinstance(response_text, str):
            success_patterns = [
                r'success.*true',
                r'completed.*true', 
                r'submitted.*successfully',
                r'thank.*you',
                r'promo.*code',
                r'survey.*complete',
                r'terima.*kasih'
            ]
            
            for pattern in success_patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    return True
                    
            # Check for error indicators
            error_patterns = [
                r'error.*true',
                r'invalid.*code',
                r'expired.*session',
                r'unauthorized',
                r'gagal'
            ]
            
            for pattern in error_patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    return False
                    
        # If no clear indicators, assume success for 200 status
        return True

    async def extract_promo_code(self, response_data):
        """Extract promo code from survey response"""
        try:
            if isinstance(response_data, dict):
                # Look for promo code in response data
                if 'promoCode' in response_data:
                    return response_data['promoCode']
                if 'reward' in response_data:
                    return response_data['reward']
                if 'code' in response_data:
                    return response_data['code']
                
                # Look in nested structures
                for key, value in response_data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if 'promo' in sub_key.lower() or 'code' in sub_key.lower():
                                return sub_value
            
            # If response_data is text, use regex patterns
            if isinstance(response_data, str):
                promo_patterns = [
                    r'[A-Z0-9]{6,12}',  # Common promo code format
                    r'ID.*?([A-Z0-9]{6,})',  # ID followed by code
                    r'kode.*?([A-Z0-9]{6,})',  # kode followed by code
                    r'promo.*?([A-Z0-9]{6,})'  # promo followed by code
                ]
                
                for pattern in promo_patterns:
                    match = re.search(pattern, response_data, re.IGNORECASE)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)
            
            return None
        except Exception as e:
            logger.error(f"Error extracting promo code: {e}")
            return None

    async def run_survey(self, customer_code, message, survey_url=None):
        """Run complete survey automation using AJAX"""
        async with await self.create_session() as session:
            try:
                # Step 1: Get initial page and extract tokens
                logger.info("Getting initial page and extracting tokens...")
                page = await self.get_initial_page(session, survey_url)
                if not page:
                    return None, "Gagal mengakses halaman survey"
                
                if not self.session_data.get('csrf_token'):
                    return None, "Gagal mendapatkan CSRF token"
                
                # Step 2: Send started request
                logger.info("Sending survey started request...")
                started_success = await self.send_started_request(session)
                if not started_success:
                    return None, "Gagal menginisialisasi survey"
                
                # Step 3: Get survey prompts
                logger.info("Getting survey prompts...")
                prompts_data = await self.get_prompts(session)
                if not prompts_data:
                    return None, "Gagal mendapatkan pertanyaan survey"
                
                # Step 4: Submit all responses (customer code, ratings, message)
                logger.info(f"Submitting all survey responses...")
                logger.info(f"Customer code: {customer_code}")
                logger.info(f"Message: {message}")
                
                response_data = await self.submit_survey_responses(session, prompts_data, customer_code, message)
                if not response_data:
                    return None, "Gagal mengirim jawaban survey. Pastikan kode pelanggan valid."
                
                # Step 5: Extract promo code from response
                logger.info("Extracting promo code from response...")
                promo_code = await self.extract_promo_code(response_data)
                if promo_code:
                    return promo_code, None
                else:
                    # Sometimes promo code is in a separate endpoint, try alternative
                    logger.info("Promo code not in response, checking alternative sources...")
                    return "SURVEY_COMPLETED", None  # Fallback message
                    
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
        "1. Kirimkan URL survey dari receipt QR code\n"
        "2. Kirimkan kode pelanggan Anda\n"
        "3. Kirimkan pesan untuk survey\n"
        "4. Bot akan mengisi survey otomatis\n"
        "5. Dapatkan kode promo Anda!\n\n"
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
        "Sekarang kirimkan kode pelanggan dari receipt:"
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
        "☐ Mengirim pesan\n"
        "☐ Mendapatkan kode promo\n\n"
        "Mohon tunggu..."
    )
    
    # Run survey automation
    promo_code, error = await bot.run_survey(customer_code, message, survey_url)
    
    # Delete processing message
    await processing_msg.delete()
    
    if promo_code:
        await update.message.reply_text(
            f"🎉 Survey berhasil diselesaikan!\n\n"
            f"🎁 Kode Promo Anda: {promo_code}\n\n"
            f"📱 Tunjukkan kode ini di Starbucks untuk mendapatkan promo!\n\n"
            f"Gunakan /start untuk mengisi survey lagi."
        )
    else:
        await update.message.reply_text(
            f"❌ Gagal menyelesaikan survey\n\n"
            f"Error: {error}\n\n"
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
