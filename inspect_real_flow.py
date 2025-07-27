#!/usr/bin/env python3
"""
Inspect real flow dari Starbucks survey untuk menemukan endpoint yang benar
"""

import asyncio
import aiohttp
import json
from urllib.parse import unquote
import re

class StarbucksFlowInspector:
    def __init__(self):
        self.base_url = "https://www.mystarbucksvisit.com"
        
    async def inspect_initial_page(self, survey_url):
        """Inspect halaman awal untuk menemukan JavaScript dan form actions"""
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(survey_url, headers=headers) as response:
                    html_content = await response.text()
                    
                    print(f"Response Status: {response.status}")
                    print(f"Content Length: {len(html_content)}")
                    print("="*50)
                    
                    # Extract JavaScript that might contain API endpoints
                    js_pattern = r'<script[^>]*>(.*?)</script>'
                    js_matches = re.findall(js_pattern, html_content, re.DOTALL)
                    
                    print("🔍 SEARCHING FOR API ENDPOINTS IN JAVASCRIPT:")
                    
                    for i, js_content in enumerate(js_matches):
                        if len(js_content.strip()) > 100:  # Only substantial JS
                            print(f"\n--- Script {i+1} ---")
                            
                            # Look for API endpoints
                            api_patterns = [
                                r'["\']([^"\']*(?:websurvey|api|submit|validate|customer|code)[^"\']*)["\']',
                                r'url["\s]*:["\s]*["\']([^"\']+)["\']',
                                r'endpoint["\s]*:["\s]*["\']([^"\']+)["\']',
                                r'action["\s]*:["\s]*["\']([^"\']+)["\']',
                            ]
                            
                            for pattern in api_patterns:
                                matches = re.findall(pattern, js_content, re.IGNORECASE)
                                for match in matches:
                                    if 'websurvey' in match or 'api' in match:
                                        print(f"  📡 Found endpoint: {match}")
                            
                            # Look for form submission code
                            form_patterns = [
                                r'\.submit\(\)',
                                r'\.post\(',
                                r'ajax\(',
                                r'fetch\(',
                                r'XMLHttpRequest'
                            ]
                            
                            for pattern in form_patterns:
                                if re.search(pattern, js_content, re.IGNORECASE):
                                    print(f"  🔧 Found form submission method: {pattern}")
                                    # Show surrounding context
                                    lines = js_content.split('\n')
                                    for line_num, line in enumerate(lines):
                                        if re.search(pattern, line, re.IGNORECASE):
                                            start = max(0, line_num - 2)
                                            end = min(len(lines), line_num + 3)
                                            print(f"    Context (lines {start}-{end}):")
                                            for ctx_line in lines[start:end]:
                                                marker = ">>> " if ctx_line == line else "    "
                                                print(f"    {marker}{ctx_line.strip()}")
                                            break
                    
                    # Look for HTML forms
                    print("\n🔍 SEARCHING FOR HTML FORMS:")
                    form_pattern = r'<form[^>]*>(.*?)</form>'
                    form_matches = re.findall(form_pattern, html_content, re.DOTALL | re.IGNORECASE)
                    
                    for i, form_content in enumerate(form_matches):
                        print(f"\n--- Form {i+1} ---")
                        
                        # Extract form action
                        action_match = re.search(r'action=["\']([^"\']*)["\']', form_content, re.IGNORECASE)
                        if action_match:
                            print(f"  📤 Action: {action_match.group(1)}")
                        
                        # Extract form method
                        method_match = re.search(r'method=["\']([^"\']*)["\']', form_content, re.IGNORECASE)
                        if method_match:
                            print(f"  🔧 Method: {method_match.group(1)}")
                        
                        # Extract input fields
                        input_pattern = r'<input[^>]*>'
                        inputs = re.findall(input_pattern, form_content, re.IGNORECASE)
                        for input_tag in inputs:
                            name_match = re.search(r'name=["\']([^"\']*)["\']', input_tag)
                            type_match = re.search(r'type=["\']([^"\']*)["\']', input_tag)
                            if name_match:
                                input_type = type_match.group(1) if type_match else "text"
                                print(f"    📝 Input: {name_match.group(1)} ({input_type})")
                    
                    # Look for Angular/React components
                    print("\n🔍 SEARCHING FOR SPA FRAMEWORKS:")
                    spa_patterns = [
                        r'ng-app',
                        r'angular',
                        r'react',
                        r'vue',
                        r'app\.js',
                        r'main\.js'
                    ]
                    
                    for pattern in spa_patterns:
                        if re.search(pattern, html_content, re.IGNORECASE):
                            print(f"  🎯 Found SPA framework: {pattern}")
                    
                    # Look for configuration or API base URLs
                    print("\n🔍 SEARCHING FOR API CONFIGURATION:")
                    config_patterns = [
                        r'baseUrl["\s]*:["\s]*["\']([^"\']+)["\']',
                        r'apiUrl["\s]*:["\s]*["\']([^"\']+)["\']',
                        r'serviceUrl["\s]*:["\s]*["\']([^"\']+)["\']',
                        r'["\']([^"\']*mystarbucksvisit[^"\']*)["\']'
                    ]
                    
                    for pattern in config_patterns:
                        matches = re.findall(pattern, html_content, re.IGNORECASE)
                        for match in matches:
                            print(f"  🔧 Config URL: {match}")
                    
                    # Save full HTML for manual inspection
                    with open('survey_page.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print(f"\n💾 Full HTML saved to survey_page.html for manual inspection")
                    
            except Exception as e:
                print(f"❌ Error inspecting page: {e}")

async def main():
    inspector = StarbucksFlowInspector()
    
    # Test URL from previous attempts
    test_url = "https://www.mystarbucksvisit.com/websurvey/2/execute?_g=NTAyMA%3D%3Dh&_s2=76b32521-781a-488f-98d0-996c67c945e8#!/1"
    
    print("🔍 INSPECTING STARBUCKS SURVEY FLOW")
    print(f"URL: {test_url}")
    print("="*70)
    
    await inspector.inspect_initial_page(test_url)
    
    print("\n" + "="*70)
    print("💡 RECOMMENDATIONS:")
    print("1. Check survey_page.html for complete page structure")
    print("2. Look for JavaScript that handles form submission")
    print("3. Survey might be SPA (Single Page App) using AJAX")
    print("4. Customer code validation might happen client-side first")
    print("5. Real submission might happen via different endpoint")

if __name__ == "__main__":
    asyncio.run(main())