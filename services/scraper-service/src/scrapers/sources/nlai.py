"""
NLAI Scraper Implementation (Optimized Bulk Strategy + High Fidelity Parsing + IDs & Permalinks)
Robust Error Handling for Network vs Server Errors.
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
import structlog
import asyncio
import re
import unicodedata
import random

logger = structlog.get_logger(__name__)

# --- Custom Exceptions ---

class MaxResultsLimitExceeded(Exception):
    """Raised when total expected results exceed the configured limit."""
    def __init__(self, found, limit):
        self.found = found
        self.limit = limit
        super().__init__(f"Found {found} records, exceeding limit of {limit}")

class NetworkConnectionError(Exception):
    """Raised when there is no internet connection or DNS failure."""
    pass

class ServerResponseError(Exception):
    """Raised when the server returns 5xx, 429, or invalid responses consistently."""
    pass

class ContentParsingError(Exception):
    """Raised when the page loads but crucial elements (like result count) are missing."""
    pass


class NLAIScraper:
    BASE_URL = "https://opac.nlai.ir/opac-prod"
    
    # Endpoints
    HANDSHAKE_URL = f"{BASE_URL}/search/bibliographicAdvancedSearch.do"
    SEARCH_PROCESS_URL = f"{BASE_URL}/search/bibliographicAdvancedSearchProcess.do"
    BRIEF_LIST_URL = f"{BASE_URL}/search/briefListSearch.do"
    
    # Permalink Base
    PERMALINK_BASE = f"{BASE_URL}/bibliographic"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    FIELD_TRANSLATION = {
        "سرشناسه": "main_entry",
        "عنوان و نام پديدآور": "title_statement",
        "فروست": "series_statement",
        "شناسه افزوده": "added_entry",
        "اطلاعات رکورد کتابشناسی": "bibliographic_record_info",
        "عنوان دیگر": "other_title",
        "عنوان قراردادی": "uniform_title",
        "عنوان روی جلد": "cover_title",
        "عنوان گسترده": "expanded_title",
        "مشخصات نشر": "publication",
        "مشخصات ظاهری": "physical_description",
        "شابک": "isbn",
        "وضعیت فهرست نویسی": "cataloging_status",
        "آوانویسی عنوان": "title_transliteration",
        "موضوع": "subjects",
        "رده بندی کنگره": "lcc",
        "رده بندی دیویی": "ddc",
        "شماره کتابشناسی ملی": "nli_number",
        "یادداشت": "note",
        "ترجمه عنوان": "title_translation",
        "مندرجات": "contents",
        "وضعیت ویراست": "edition_status",
        "عنوان عطف": "spine_title",
        "عنوان به زبان دیگر": "title_in_other_language",
        "خلاصه": "abstract",
        "توصیفگر": "descriptor",
        "دسترسی و محل الکترونیکی":"electronic_access"
    }

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers=self.DEFAULT_HEADERS,
            timeout=600.0, # Reduced slightly to fail faster on bad nets
            follow_redirects=True,
            verify=False 
        )
        self.jsessionid: Optional[str] = None
        
        self.NORMALIZED_FIELD_TRANSLATION = {}
        for k, v in self.FIELD_TRANSLATION.items():
            norm_key = self._normalize_fa_key(k)
            self.NORMALIZED_FIELD_TRANSLATION[norm_key] = v

    # --- Helpers ---

    def _clean_text(self, text: str) -> str:
        if not text: return ""
        text = unicodedata.normalize("NFKC", text)
        text = text.replace('\u200f', '').replace('\u200e', '').replace('\xa0', ' ')
        text = text.strip(":： ")
        text = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        return text.strip()

    def _normalize_fa_key(self, text: str) -> str:
        if not text: return ""
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه").replace("أ", "ا").replace("إ", "ا")
        return text.strip()

    def _add_to_data(self, data: Dict, key: str, value: str):
        if key in data:
            if isinstance(data[key], list):
                data[key].append(value)
            else:
                data[key] = [data[key], value]
        else:
            data[key] = value

    # --- NEW: ID Extraction Helper ---
    
    def _parse_brief_results(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        ids = []
        target_links = soup.find_all("a", href=True)
        
        for link in target_links:
            href = link['href']
            if "command=FULL_VIEW" in href and "id=" in href:
                match = re.search(r"[?&]id=(\d+)", href)
                if match:
                    ids.append(match.group(1))
        
        if len(ids) == 0:
            logger.warning("nlai.ids_zero", html_snippet=html[:500])
        return ids


    # --- Network Logic (Updated for Robustness) ---

    async def _safe_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Executes request with retry logic.
        Raises:
            NetworkConnectionError: If DNS/Connection fails (No internet).
            ServerResponseError: If server returns 5xx/429 consistently.
        """
        delay = random.uniform(0.5, 1.5)
        await asyncio.sleep(delay)

        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                if method.upper() == "POST":
                    resp = await self.client.post(url, **kwargs)
                else:
                    resp = await self.client.get(url, **kwargs)
                
                # Handling Server-Side Errors
                if resp.status_code == 429:
                    wait_time = (attempt + 1) * 10 # More aggressive wait as per request
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                
                if resp.status_code >= 500:
                    wait_time = 10 # Fixed 10s wait for server errors as requested
                    logger.warning(f"Server error ({resp.status_code}). Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                if resp.status_code != 200:
                     # Other non-200 codes (e.g. 403, 404)
                    logger.warning("nlai.request_failed", status=resp.status_code, url=url)
                    raise ServerResponseError(f"HTTP {resp.status_code}")
                    
                return resp
                
            except httpx.RequestError as e:
                 # ✅ Covers ALL httpx network-related errors:
                 # ConnectError, ConnectTimeout, ReadTimeout,
                 # DNS resolution errors, RemoteProtocolError, etc.
                logger.error("nlai.network_error", error=str(e), attempt=attempt)
                last_exception = NetworkConnectionError(str(e))
                await asyncio.sleep(2)  # short backoff before retry
            except Exception as e:
                # ✅ Truly unexpected programmer / logic errors
                logger.exception("nlai.unexpected_low_level_error", error=str(e))
                raise

        # If we exhausted retries:
        if last_exception:
            raise last_exception
        
        # If we exhausted retries due to status codes
        raise ServerResponseError("Max retries exceeded with server errors")

    async def perform_handshake(self):
        """Public method to establish session. Use this for recovery."""
        params = {"command": "NEW_SEARCH", "classType": "0", "pageStatus": "1"}
        # We use _safe_request here too, so it will raise Network/Server errors properly
        resp = await self._safe_request("GET", self.HANDSHAKE_URL, params=params)
        
        cookies = dict(self.client.cookies)
        self.jsessionid = cookies.get("JSESSIONID")
        if not self.jsessionid:
            set_cookie = resp.headers.get("set-cookie", "")
            match = re.search(r"JSESSIONID=([^;]+)", set_cookie)
            if match: self.jsessionid = match.group(1)
        
        if not self.jsessionid: 
            raise ServerResponseError("Handshake successful but no JSESSIONID returned")

    def _extract_total_results(self, html: str) -> Optional[int]:
        """
        Returns:
            int: The number of results found.
            None: If the count could not be found (implies bad page/error page).
        """
        try:
            soup = BeautifulSoup(html, "lxml")
            for td in soup.find_all("td", nowrap="nowrap"):
                text = td.get_text(strip=True)
                if "تعداد رکوردها" in text or "Records Found" in text:
                    value_td = td.find_next("td")
                    if value_td:
                        numbers = re.findall(r"[۰-۹0-9]+", value_td.text)
                        if numbers:
                            num_str = numbers[0].translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
                            return int(num_str)
        except Exception:
            pass
        return None # Return None explicitly if not found

    def _extract_form_state(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        form = soup.find("form") 
        if not form: return {}
        payload = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            value = inp.get("value", "")
            if name: payload[name] = value
        for select in form.find_all("select"):
            name = select.get("name")
            if name:
                selected_opt = select.find("option", selected=True) or select.find("option")
                if selected_opt: payload[name] = selected_opt.get("value")
        return payload

    async def _resize_page(self, current_html: str, total_count: int, referer: str) -> Optional[str]:
        payload = self._extract_form_state(current_html)
        if not payload: return None
        payload["command"] = "BRIEF_LIST_SETUP"
        payload["pageSize"] = str(total_count)
        payload["pageNum"] = "1"
        
        headers = {
            "Referer": referer,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://opac.nlai.ir"
        }
        url = f"{self.BRIEF_LIST_URL};jsessionid={self.jsessionid}"
        resp = await self._safe_request("POST", url, data=payload, headers=headers)
        return resp.text

    async def _fetch_bulk_print_view(self, resized_html: str, referer: str) -> Optional[str]:
        payload = self._extract_form_state(resized_html)
        if not payload: return None
        payload["command"] = "SAVE_PRINT"
        
        headers = {
            "Referer": referer,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://opac.nlai.ir"
        }
        url = f"{self.BRIEF_LIST_URL};jsessionid={self.jsessionid}"
        logger.info("nlai.bulk_fetch_start", items=len(payload))
        resp = await self._safe_request("POST", url, data=payload, headers=headers)
        return resp.text

    # --- Core Parsing Logic ---

    def _parse_bulk_print_view(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        
        container = soup.find("table", id="printTable")
        if not container:
            return []

        book_tables = container.find_all("table", attrs={"dir": "rtl"})
        
        for table in book_tables:
            book_data = {}
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3: continue
                
                raw_label = cells[0].get_text()
                raw_value = cells[2].get_text()
                
                clean_key = self._normalize_fa_key(self._clean_text(raw_label))
                clean_value = self._clean_text(raw_value)
                
                if not clean_key or not clean_value: continue

                self._add_to_data(book_data, clean_key, clean_value)

                mapped_key = None
                if clean_key in self.NORMALIZED_FIELD_TRANSLATION:
                     mapped_key = self.NORMALIZED_FIELD_TRANSLATION[clean_key]
                else:
                    for norm_fa_key, en_key in self.NORMALIZED_FIELD_TRANSLATION.items():
                        if norm_fa_key in clean_key:
                            mapped_key = en_key
                            break
                
                if mapped_key:
                    self._add_to_data(book_data, mapped_key, clean_value)
            
            if book_data:
                results.append(book_data)

        return results

    async def fetch_with_custom_payload(self, initial_payload: Dict[str, Any], max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        # This method assumes Exceptions are handled by the caller (Task)
        
        if not self.client.cookies.get("JSESSIONID"):
            await self.perform_handshake()
        
        current_jsessionid = self.client.cookies.get("JSESSIONID")
        current_url = f"{self.SEARCH_PROCESS_URL};jsessionid={current_jsessionid}"
        referer = f"{self.HANDSHAKE_URL}?command=NEW_SEARCH&classType=0&pageStatus=1"
        
        headers = {
            "Origin": "https://opac.nlai.ir",
            "Referer": referer,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # 1. Search
        resp = await self._safe_request("POST", current_url, data=initial_payload, headers=headers)
        initial_html = resp.text
        
        total_expected = self._extract_total_results(initial_html)
        
        # [CRITICAL LOGIC] Only return empty if 0 is EXPLICITLY found.
        if total_expected is None:
            # We got a 200 OK, but couldn't find the results count. 
            # This means it's an error page or unexpected layout.
            logger.error("nlai.content_parsing_error", html_snippet=initial_html[:300])
            raise ContentParsingError("Results count not found in page")

        logger.info("nlai.stats", found=total_expected, limit=max_results)
        
        if total_expected == 0:
            return [] # This is a VALID success with 0 results

        # Check Max Results Limit
        if max_results and total_expected > max_results:
            raise MaxResultsLimitExceeded(total_expected, max_results)

        # 2. Resize
        resized_html = await self._resize_page(initial_html, total_expected, referer=current_url)
        if not resized_html: raise ContentParsingError("Resize failed")
        
        # Extract IDs
        ids_list = self._parse_brief_results(resized_html)
        
        # 3. Bulk Fetch
        bulk_url_base = f"{self.BRIEF_LIST_URL};jsessionid={current_jsessionid}"
        bulk_html = await self._fetch_bulk_print_view(resized_html, referer=bulk_url_base)
        if not bulk_html: raise ContentParsingError("Bulk fetch failed")

        # 4. Parse Details
        full_profiles = self._parse_bulk_print_view(bulk_html)
        
        # Merge IDs
        merged_count = 0
        for i, profile in enumerate(full_profiles):
            if i < len(ids_list):
                book_id = ids_list[i]
                if book_id:
                    profile["nlai_id"] = book_id
                    profile["nlai_permalink"] = f"{self.PERMALINK_BASE}/{book_id}"
                    merged_count += 1
        
        logger.info("nlai.done", extracted=len(full_profiles), ids_merged=merged_count, expected=total_expected)
        return full_profiles

    async def fetch_by_author_name(self, author_name: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        payload = {
            "advancedSearch.simpleSearch[0].indexFieldId": "",
            "advancedSearch.simpleSearch[0].value": author_name,
            "advancedSearch.simpleSearch[0].tokenized": "true",
            "advancedSearch.operator[0]": "1",
            "advancedSearch.simpleSearch[1].indexFieldId": "",
            "advancedSearch.simpleSearch[1].value": "",
            "advancedSearch.simpleSearch[1].tokenized": "true",
            "advancedSearch.operator[1]": "1",
            "advancedSearch.simpleSearch[2].indexFieldId": "",
            "advancedSearch.simpleSearch[2].value": "",
            "advancedSearch.simpleSearch[2].tokenized": "true",
            "nliHolding": "",
            "bibliographicLimitQueryBuilder.biblioDocType": "BF",
            "bibliographicLimitQueryBuilder.calendar": "",
            "bibliographicLimitQueryBuilder.from": "",
            "bibliographicLimitQueryBuilder.dateComparisonOperator": "eq",
            "bibliographicLimitQueryBuilder.language": "",
            "bibliographicLimitQueryBuilder.codingLevel": "",
            "bibliographicLimitQueryBuilder.gmd": "",
            "command": "I",
            "classType": "0",
            "pageStatus": "1",
            "bibliographicLimitQueryBuilder.useDateRange": "false",
            "bibliographicLimitQueryBuilder.year": "",
            "attributes.locale": "fa",
        }
        return await self.fetch_with_custom_payload(payload, max_results=max_results)

    async def close(self):
        await self.client.aclose()
