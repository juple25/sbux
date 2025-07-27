#!/usr/bin/env python3
"""
Test script untuk bot Starbucks - versi sederhana untuk testing
"""

import asyncio
import json
import re
from urllib.parse import urlparse, parse_qs, unquote

class StarbucksTestBot:
    def __init__(self):
        self.base_url = "https://www.mystarbucksvisit.com"
        
    def extract_session_from_url(self, survey_url):
        """Extract session parameters from survey URL with improved parsing"""
        try:
            print(f"Testing URL extraction for: {survey_url}")
            
            # Handle URL with parentheses in query parameters
            if '(' in survey_url and ')' in survey_url:
                # Extract content between parentheses
                start = survey_url.find('(') + 1
                end = survey_url.find(')')
                params_str = survey_url[start:end]
                
                print(f"Found params in parentheses: {params_str}")
                
                # Parse individual parameters
                g_param = None
                s2_param = None
                
                if '&' in params_str:
                    parts = params_str.split('&')
                    print(f"Split parts: {parts}")
                    for part in parts:
                        print(f"Processing part: '{part}'")
                        if '_g=' in part:
                            g_param = part.split('_g=')[1] if '_g=' in part else part[3:]
                            print(f"Found g_param: {g_param}")
                        elif '_s2=' in part:
                            s2_param = part.split('_s2=')[1] if '_s2=' in part else part[4:]
                            print(f"Found s2_param: {s2_param}")
                        elif part.startswith('NTAy'):  # Handle case where _g= is missing
                            g_param = part
                            print(f"Found g_param without prefix: {g_param}")
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
            
            print(f"Extracted _g: {g_param}")
            print(f"Extracted _s2: {s2_param}")
            return g_param, s2_param
            
        except Exception as e:
            print(f"Error extracting session from URL: {e}")
            return None, None
    
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

def test_url_extraction():
    """Test URL parameter extraction"""
    bot = StarbucksTestBot()
    
    # Test cases
    test_urls = [
        "https://www.mystarbucksvisit.com/websurvey/2/execute?_g=(NTAyMA%3D%3Dh&_s2=76b32521-781a-488f-98d0-996c67c945e8)#!/1",
        "https://www.mystarbucksvisit.com/websurvey/2/execute?_g=NTAyMA%3D%3Dh&_s2=76b32521-781a-488f-98d0-996c67c945e8#!/1",
        "https://www.mystarbucksvisit.com/websurvey/2/execute?_g=(NTAyMA%3D%3Dh)&_s2=(76b32521-781a-488f-98d0-996c67c945e8)#!/1"
    ]
    
    for url in test_urls:
        print(f"\n{'='*50}")
        print(f"Testing URL: {url}")
        g_param, s2_param = bot.extract_session_from_url(url)
        print(f"Result - g_param: {g_param}, s2_param: {s2_param}")

def test_code_formats():
    """Test customer code format generation"""
    bot = StarbucksTestBot()
    
    test_codes = [
        "16644 08020727 0916",
        "1664408020727 0916",
        "16644080207270916",
        "ABC123 DEF456",
        "ABC123DEF456"
    ]
    
    for code in test_codes:
        print(f"\n{'='*30}")
        print(f"Testing code: '{code}'")
        formats = bot.get_smart_code_formats(code)
        print(f"Generated formats: {formats}")

if __name__ == "__main__":
    print("Testing Starbucks Bot Improvements")
    print("\n1. Testing URL Parameter Extraction:")
    test_url_extraction()
    
    print("\n2. Testing Customer Code Formats:")
    test_code_formats()
    
    print("\nTesting completed!")
    print("\nSummary of Improvements:")
    print("1. Dynamic URL parameter extraction (handles parentheses)")
    print("2. Smart customer code format generation")
    print("3. Reduced endpoint brute-forcing (3 priority + 2 fallback)")
    print("4. Added delays between requests (2-8 seconds)")
    print("5. Improved error handling and rate limit detection")
    print("6. Better session management with dynamic headers")