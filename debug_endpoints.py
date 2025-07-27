#!/usr/bin/env python3
"""
Tool untuk debug endpoint Starbucks survey
Berdasarkan screenshot flow yang benar
"""

import asyncio
import aiohttp
import json
from urllib.parse import unquote

class StarbucksDebugger:
    def __init__(self):
        self.base_url = "https://www.mystarbucksvisit.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"iOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        
    async def test_form_submission(self, survey_url, customer_code):
        """Test form submission seperti yang dilakukan di browser"""
        
        # Extract session parameters
        g_param, s2_param = self.extract_session_from_url(survey_url)
        print(f"Session params: _g={g_param}, _s2={s2_param}")
        
        async with aiohttp.ClientSession() as session:
            # 1. Get initial page (language selection)
            print("\n1. Getting initial page...")
            async with session.get(survey_url, headers=self.headers) as response:
                initial_html = await response.text()
                print(f"Initial page status: {response.status}")
                
            # 2. Submit language selection (Bahasa Indonesia)
            print("\n2. Submitting language selection...")
            language_data = {
                'language': 'id',
                '_g': g_param,
                '_s2': s2_param
            }
            
            # Try common form submission endpoints
            possible_language_endpoints = [
                f"{self.base_url}/websurvey/2/language",
                f"{self.base_url}/websurvey/2/setLanguage", 
                f"{self.base_url}/websurvey/2/execute",
                f"{self.base_url}/websurvey/2/start"
            ]
            
            for endpoint in possible_language_endpoints:
                try:
                    async with session.post(endpoint, data=language_data, headers=self.headers) as response:
                        response_text = await response.text()
                        print(f"Language endpoint {endpoint}: {response.status}")
                        if response.status == 200:
                            print("✅ Language endpoint found!")
                            break
                except Exception as e:
                    print(f"❌ {endpoint}: {e}")
            
            # 3. Submit customer code
            print(f"\n3. Submitting customer code: {customer_code}")
            customer_data = {
                'customer_code': customer_code,
                'code': customer_code,
                '_g': g_param,
                '_s2': s2_param
            }
            
            possible_customer_endpoints = [
                f"{self.base_url}/websurvey/2/validateCode",
                f"{self.base_url}/websurvey/2/customerCode",
                f"{self.base_url}/websurvey/2/checkCode",
                f"{self.base_url}/websurvey/2/submitCode",
                f"{self.base_url}/websurvey/2/next"
            ]
            
            for endpoint in possible_customer_endpoints:
                try:
                    async with session.post(endpoint, data=customer_data, headers=self.headers) as response:
                        response_text = await response.text()
                        print(f"Customer code endpoint {endpoint}: {response.status}")
                        if response.status == 200 and 'error' not in response_text.lower():
                            print("✅ Customer code endpoint found!")
                            print(f"Response preview: {response_text[:200]}...")
                            break
                except Exception as e:
                    print(f"❌ {endpoint}: {e}")
            
            # 4. Test survey submission endpoints
            print(f"\n4. Testing survey submission...")
            survey_data = {
                'visit_type': '1',  # Membeli dan langsung pergi
                'food_order': '1',  # Ya
                'return_visit': '1', # Hari ini atau besok
                'rating_1': '7',
                'rating_2': '7', 
                'rating_3': '7',
                'rating_4': '7',
                'rating_5': '7',
                'rating_6': '7',
                'rating_7': '7',
                'feedback': 'Great service!',
                '_g': g_param,
                '_s2': s2_param
            }
            
            possible_survey_endpoints = [
                f"{self.base_url}/websurvey/2/submit",
                f"{self.base_url}/websurvey/2/complete",
                f"{self.base_url}/websurvey/2/finish",
                f"{self.base_url}/websurvey/2/next",
                f"{self.base_url}/websurvey/2/save"
            ]
            
            for endpoint in possible_survey_endpoints:
                try:
                    async with session.post(endpoint, data=survey_data, headers=self.headers) as response:
                        response_text = await response.text()
                        print(f"Survey endpoint {endpoint}: {response.status}")
                        if response.status == 200:
                            print("✅ Survey endpoint found!")
                            print(f"Response preview: {response_text[:200]}...")
                            
                            # Check for promo code in response
                            if any(word in response_text.lower() for word in ['promo', 'kode', 'reward', 'coupon']):
                                print("🎁 Potential promo code found in response!")
                            break
                except Exception as e:
                    print(f"❌ {endpoint}: {e}")

    def extract_session_from_url(self, survey_url):
        """Extract session parameters dari URL"""
        try:
            if '(' in survey_url and ')' in survey_url:
                start = survey_url.find('(') + 1
                end = survey_url.find(')')
                params_str = survey_url[start:end]
                
                g_param = None
                s2_param = None
                
                if '&' in params_str:
                    parts = params_str.split('&')
                    for part in parts:
                        if '_g=' in part:
                            g_param = part.split('_g=')[1]
                        elif '_s2=' in part:
                            s2_param = part.split('_s2=')[1]
                        elif part.startswith('NTAy'):
                            g_param = part
                
                if g_param:
                    g_param = unquote(g_param)
                if s2_param:
                    s2_param = unquote(s2_param)
                    
                return g_param, s2_param
                
        except Exception as e:
            print(f"Error extracting session: {e}")
            return None, None

async def main():
    debugger = StarbucksDebugger()
    
    # Test URL dari screenshot
    test_url = "https://www.mystarbucksvisit.com/websurvey/2/execute?_g=NTAyMA%3D%3Dh&_s2=76b32521-781a-488f-98d0-996c67c945e8#!/1"
    customer_code = "16644086207270916"
    
    print("🔍 Debug Starbucks Survey Endpoints")
    print(f"URL: {test_url}")
    print(f"Customer Code: {customer_code}")
    print("="*50)
    
    await debugger.test_form_submission(test_url, customer_code)
    
    print("\n" + "="*50)
    print("🎯 Berdasarkan flow screenshot:")
    print("1. Form submission menggunakan POST dengan form data")
    print("2. Endpoint kemungkinan menggunakan /next atau /submit")
    print("3. Response mungkin HTML redirect, bukan JSON")
    print("4. Perlu follow redirect untuk mendapat promo code")

if __name__ == "__main__":
    asyncio.run(main())