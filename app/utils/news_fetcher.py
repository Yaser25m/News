"""
وحدة جلب الأخبار من المصادر الإخبارية
تحتوي على فئة NewsFetcher التي تقوم بجلب الأخبار من المصادر الإخبارية المختلفة
وتخزينها في قاعدة البيانات
"""

import requests
from bs4 import BeautifulSoup
import hashlib
import logging
import re
from datetime import datetime, date, timedelta
from urllib.parse import urljoin, urlparse
import time
import random
from dateutil import parser
import concurrent.futures
import traceback

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('news_fetcher')

class NewsFetcher:
    """فئة لجلب الأخبار من المصادر الإخبارية"""

    def __init__(self, db, ScrapedNews, NewsSource):
        """تهيئة جالب الأخبار"""
        self.db = db
        self.ScrapedNews = ScrapedNews
        self.NewsSource = NewsSource

        # إعدادات الجلب
        self.max_retries = 3  # عدد محاولات إعادة المحاولة
        self.timeout = 15  # مهلة الاتصال بالثواني
        self.max_workers = 5  # عدد العمليات المتزامنة

        # قائمة وكلاء المستخدم المختلفة لتجنب الحظر
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
        ]

        # رؤوس HTTP الافتراضية
        self.headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }

        # كلمات دالة على أخبار العراق
        self.iraq_keywords = [
            'iraq', 'iraqi', 'العراق', 'عراقي', 'عراقية', 'بغداد', 'baghdad',
            'موصل', 'mosul', 'basra', 'البصرة', 'كركوك', 'kirkuk', 'اربيل', 'erbil',
            'النجف', 'najaf', 'كربلاء', 'karbala', 'الانبار', 'anbar', 'ديالى', 'diyala',
            'ذي قار', 'dhi qar', 'ميسان', 'maysan', 'المثنى', 'muthanna',
            'صلاح الدين', 'salah al-din', 'بابل', 'babylon', 'واسط', 'wasit',
            'دهوك', 'duhok', 'السليمانية', 'sulaymaniyah'
        ]

    def fetch_all_sources(self, only_active=True, only_iraqi=True, max_news_per_source=30):
        """جلب الأخبار من جميع المصادر النشطة"""
        # جلب المصادر النشطة
        query = self.NewsSource.query
        if only_active:
            query = query.filter_by(is_active=True)
        if only_iraqi:
            query = query.filter_by(is_iraqi=True)

        sources = query.all()
        logger.info(f"بدء جلب الأخبار من {len(sources)} مصدر")

        # إذا لم تكن هناك مصادر، أضف مصدرًا افتراضيًا للاختبار
        if len(sources) == 0:
            default_sources = [
                {
                    'name': 'السومرية نيوز',
                    'url': 'https://www.alsumaria.tv/',
                    'is_iraqi': True
                },
                {
                    'name': 'شبكة أخبار العراق',
                    'url': 'https://aliraqnews.com/',
                    'is_iraqi': True
                },
                {
                    'name': 'بغداد اليوم',
                    'url': 'https://baghdadtoday.news/',
                    'is_iraqi': True
                }
            ]

            for source_data in default_sources:
                source = self.NewsSource(
                    name=source_data['name'],
                    url=source_data['url'],
                    is_active=True,
                    is_iraqi=source_data['is_iraqi']
                )
                self.db.session.add(source)

            self.db.session.commit()
            sources = self.NewsSource.query.filter_by(is_active=True).all()
            logger.info(f"تم إضافة {len(default_sources)} مصدر افتراضي")

        total_fetched = 0
        results = []

        for source in sources:
            try:
                news_list = self.fetch_from_source(source, max_news=max_news_per_source)
                total_fetched += len(news_list)
                results.append({
                    'source': source.name,
                    'count': len(news_list),
                    'status': 'success'
                })
                logger.info(f"تم جلب {len(news_list)} خبر من {source.name}")

                # إضافة فترة انتظار عشوائية بين الطلبات لتجنب الحظر
                time.sleep(random.uniform(1, 3))

            except Exception as e:
                logger.error(f"خطأ في جلب الأخبار من {source.name}: {str(e)}")
                results.append({
                    'source': source.name,
                    'count': 0,
                    'status': 'error',
                    'error': str(e)
                })

        logger.info(f"اكتمل جلب الأخبار. تم جلب {total_fetched} خبر بنجاح")
        return results

    def fetch_from_source(self, source, max_news=30, max_pages=3):
        """جلب الأخبار من مصدر محدد"""
        logger.info(f"جلب الأخبار من {source.name} ({source.url})")

        try:
            news_list = []
            all_news_links = []

            # جلب الصفحة الرئيسية
            main_page_links = self._get_links_from_page(source.url, source)
            all_news_links.extend(main_page_links)

            # جلب روابط من صفحات إضافية (مثل صفحات الأقسام أو الصفحات التالية)
            additional_pages = self._get_additional_pages(source.url, source, max_pages)

            # استخدام طريقة متسلسلة بدلاً من المعالجة المتوازية لتجنب مشاكل سياق التطبيق
            for page_url in additional_pages:
                try:
                    page_links = self._get_links_from_page(page_url, source)
                    all_news_links.extend(page_links)
                    logger.info(f"تم جلب {len(page_links)} رابط من {page_url}")

                    # إضافة فترة انتظار عشوائية بين الطلبات لتجنب الحظر
                    time.sleep(random.uniform(0.5, 1))
                except Exception as e:
                    logger.error(f"خطأ في جلب الروابط من {page_url}: {str(e)}")

            # إزالة الروابط المكررة
            all_news_links = list(set(all_news_links))
            logger.info(f"تم العثور على {len(all_news_links)} رابط أخبار في {source.name}")

            # تحديد الروابط التي لم يتم جلبها مسبقًا
            links_to_fetch = []
            for link in all_news_links[:max_news]:
                # التحقق من أن الرابط لم يتم جلبه مسبقًا
                existing_url = self.ScrapedNews.query.filter_by(source_url=link).first()
                if not existing_url:
                    links_to_fetch.append(link)
                else:
                    logger.info(f"الخبر موجود مسبقًا (الرابط): {link}")

            logger.info(f"سيتم جلب {len(links_to_fetch)} خبر جديد من {source.name}")

            # استخدام المعالجة المتوازية لجلب محتوى الأخبار
            if links_to_fetch:
                # دالة لجلب محتوى الخبر وحفظه في قاعدة البيانات
                def fetch_and_save_news(link):
                    try:
                        news = self._fetch_news_content(link, source)
                        if news:
                            # التحقق من عدم وجود الخبر مسبقًا (بناءً على بصمة المحتوى)
                            existing_news = self.ScrapedNews.query.filter_by(content_hash=news['content_hash']).first()
                            if not existing_news:
                                return news
                            else:
                                logger.info(f"الخبر موجود مسبقًا (المحتوى): {news['title']}")
                        return None
                    except Exception as e:
                        logger.error(f"خطأ في جلب محتوى الخبر {link}: {str(e)}")
                        return None

                # استخدام طريقة متسلسلة بدلاً من المعالجة المتوازية لتجنب مشاكل سياق التطبيق
                for link in links_to_fetch:
                    try:
                        news = fetch_and_save_news(link)
                        if news:
                            # إنشاء خبر جديد
                            scraped_news = self.ScrapedNews(
                                title=news['title'],
                                content=news['content'],
                                date=news['date'],
                                source=source.name,
                                source_url=news['url'],
                                content_hash=news['content_hash'],
                                source_id=source.id
                            )
                            self.db.session.add(scraped_news)
                            news_list.append(news)
                            logger.info(f"تم جلب الخبر: {news['title']}")

                            # حفظ التغييرات في قاعدة البيانات بعد كل 5 أخبار
                            if len(news_list) % 5 == 0:
                                try:
                                    self.db.session.commit()
                                except Exception as e:
                                    logger.error(f"خطأ في حفظ التغييرات في قاعدة البيانات: {str(e)}")
                                    self.db.session.rollback()
                    except Exception as e:
                        logger.error(f"خطأ في معالجة نتيجة جلب الخبر {link}: {str(e)}")

            # حفظ التغييرات المتبقية في قاعدة البيانات
            try:
                self.db.session.commit()
                logger.info(f"تم حفظ {len(news_list)} خبر من {source.name} في قاعدة البيانات")
            except Exception as e:
                logger.error(f"خطأ في حفظ التغييرات في قاعدة البيانات: {str(e)}")
                self.db.session.rollback()

            return news_list

        except Exception as e:
            logger.error(f"خطأ في جلب الأخبار من {source.name}: {str(e)}")
            logger.debug(traceback.format_exc())
            # محاولة إعادة ضبط الجلسة في حالة حدوث خطأ
            try:
                self.db.session.rollback()
            except:
                pass
            return []

    def _get_links_from_page(self, page_url, source):
        """جلب روابط الأخبار من صفحة محددة"""
        try:
            # جلب صفحة المصدر
            response = requests.get(page_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # التأكد من أن الصفحة بالعربية
            if 'content-type' in response.headers and 'charset' in response.headers['content-type']:
                encoding = response.headers['content-type'].split('charset=')[-1]
                response.encoding = encoding
            else:
                response.encoding = 'utf-8'

            # تحليل الصفحة
            soup = BeautifulSoup(response.text, 'html.parser')

            # البحث عن روابط الأخبار
            news_links = self._extract_news_links(soup, page_url)

            return news_links
        except Exception as e:
            logger.error(f"خطأ في جلب روابط الأخبار من {page_url}: {str(e)}")
            return []

    def _get_additional_pages(self, base_url, source, max_pages=3):
        """الحصول على صفحات إضافية للجلب منها (مثل صفحات الأقسام أو الصفحات التالية)"""
        additional_pages = []

        try:
            # جلب صفحة المصدر
            response = requests.get(base_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # التأكد من أن الصفحة بالعربية
            if 'content-type' in response.headers and 'charset' in response.headers['content-type']:
                encoding = response.headers['content-type'].split('charset=')[-1]
                response.encoding = encoding
            else:
                response.encoding = 'utf-8'

            # تحليل الصفحة
            soup = BeautifulSoup(response.text, 'html.parser')

            # البحث عن روابط الأقسام
            section_links = []

            # البحث عن روابط في القائمة الرئيسية
            for nav in soup.find_all(['nav', 'ul', 'div'], class_=lambda c: c and any(keyword in c.lower() for keyword in ['menu', 'nav', 'header', 'قائمة', 'رئيسية'])):
                for a in nav.find_all('a', href=True):
                    href = a.get('href')
                    if href and not href.startswith('#') and not href.startswith('javascript:'):
                        # تحويل الرابط النسبي إلى رابط مطلق
                        full_url = urljoin(base_url, href)

                        # التأكد من أن الرابط في نفس النطاق
                        if urlparse(full_url).netloc == urlparse(base_url).netloc:
                            # التحقق من أن الرابط يشير إلى قسم أخبار
                            if any(keyword in href.lower() or keyword in a.text.lower() for keyword in ['news', 'article', 'category', 'section', 'أخبار', 'مقالات', 'أقسام', 'تصنيف', 'عاجل', 'محلية', 'دولية', 'سياسية', 'اقتصادية']):
                                section_links.append(full_url)

            # إضافة الصفحات التالية (2, 3, ...) إذا كانت موجودة
            pagination_links = []
            for a in soup.find_all('a', href=True):
                href = a.get('href')
                if href and not href.startswith('#') and not href.startswith('javascript:'):
                    # البحث عن روابط الصفحات التالية
                    if re.search(r'page=\d+|/page/\d+|[?&]p=\d+', href):
                        # تحويل الرابط النسبي إلى رابط مطلق
                        full_url = urljoin(base_url, href)

                        # التأكد من أن الرابط في نفس النطاق
                        if urlparse(full_url).netloc == urlparse(base_url).netloc:
                            pagination_links.append(full_url)

            # إضافة روابط الأقسام (بحد أقصى 5 أقسام)
            additional_pages.extend(section_links[:5])

            # إضافة روابط الصفحات التالية (بحد أقصى max_pages صفحة)
            additional_pages.extend(pagination_links[:max_pages])

            # إزالة الروابط المكررة
            additional_pages = list(set(additional_pages))

            logger.info(f"تم العثور على {len(additional_pages)} صفحة إضافية في {source.name}")

            return additional_pages
        except Exception as e:
            logger.error(f"خطأ في الحصول على صفحات إضافية من {base_url}: {str(e)}")
            return []

    def _extract_news_links(self, soup, base_url):
        """استخراج روابط الأخبار من صفحة المصدر"""
        links = []

        # البحث عن جميع الروابط في الصفحة
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            # تجاهل الروابط الخارجية والروابط غير المتعلقة بالأخبار
            if self._is_news_link(href, a_tag):
                # تحويل الرابط النسبي إلى رابط مطلق
                full_url = urljoin(base_url, href)

                # التأكد من أن الرابط في نفس النطاق
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    links.append(full_url)

        # إزالة الروابط المكررة
        return list(set(links))

    def _is_news_link(self, href, a_tag):
        """التحقق مما إذا كان الرابط هو رابط خبر"""
        # تجاهل الروابط الفارغة أو روابط الصفحة الحالية
        if not href or href == '#' or href.startswith('javascript:'):
            return False

        # تجاهل روابط وسائل التواصل الاجتماعي والبريد الإلكتروني
        if href.startswith(('mailto:', 'tel:', 'sms:', 'whatsapp:')):
            return False
        if any(domain in href for domain in ['facebook.com', 'twitter.com', 'instagram.com', 'youtube.com']):
            return False

        # البحث عن كلمات دالة على أنه رابط خبر
        news_keywords = ['news', 'article', 'story', 'post', 'خبر', 'مقال', 'قصة', 'منشور', 'تقرير', 'report']

        # كلمات دالة على أخبار العراق
        iraq_keywords = ['iraq', 'iraqi', 'العراق', 'عراقي', 'عراقية', 'بغداد', 'baghdad', 'موصل', 'mosul', 'basra', 'البصرة', 'كركوك', 'kirkuk', 'اربيل', 'erbil']

        # التحقق من وجود كلمات دالة في الرابط
        if any(keyword in href.lower() for keyword in news_keywords):
            # التحقق من وجود كلمات دالة على العراق في الرابط أو نص الرابط
            if any(keyword in href.lower() for keyword in iraq_keywords):
                return True
            if a_tag.text and any(keyword in a_tag.text.lower() for keyword in iraq_keywords):
                return True

        # التحقق من وجود كلمات دالة في نص الرابط
        if a_tag.text and any(keyword in a_tag.text.lower() for keyword in news_keywords):
            # التحقق من وجود كلمات دالة على العراق في الرابط أو نص الرابط
            if any(keyword in href.lower() for keyword in iraq_keywords):
                return True
            if a_tag.text and any(keyword in a_tag.text.lower() for keyword in iraq_keywords):
                return True

        # التحقق من وجود تاريخ في الرابط (مثل 2023/05/18)
        if re.search(r'\d{4}/\d{1,2}/\d{1,2}', href):
            # التحقق من وجود كلمات دالة على العراق في الرابط أو نص الرابط
            if any(keyword in href.lower() for keyword in iraq_keywords):
                return True
            if a_tag.text and any(keyword in a_tag.text.lower() for keyword in iraq_keywords):
                return True

        # التحقق من وجود معرف رقمي في الرابط (مثل id=123 أو news/123)
        if re.search(r'id=\d+', href) or re.search(r'/\d+$', href):
            # التحقق من وجود كلمات دالة على العراق في الرابط أو نص الرابط
            if any(keyword in href.lower() for keyword in iraq_keywords):
                return True
            if a_tag.text and any(keyword in a_tag.text.lower() for keyword in iraq_keywords):
                return True

        return False

    def _fetch_news_content(self, url, source):
        """جلب محتوى الخبر من الرابط"""
        # تحديد المصدر واستخدام الدالة المخصصة إذا كانت متوفرة
        domain = urlparse(url).netloc.lower()

        # استخدام الدوال المخصصة للمواقع الشائعة
        if 'alsumaria.tv' in domain:
            news = self._extract_from_alsumaria(url)
        elif 'aliraqnews.com' in domain:
            news = self._extract_from_iraqnews(url)
        elif 'baghdadtoday.news' in domain:
            # يمكن إضافة دالة مخصصة لموقع بغداد اليوم لاحقًا
            news = self._extract_generic_news(url)
        else:
            # استخدام الدالة العامة للمواقع الأخرى
            news = self._extract_generic_news(url)

        # التحقق من صحة البيانات المستخرجة
        if news:
            # التحقق من أن الخبر يتعلق بالعراق
            if not self._is_iraq_related(news['title'], news['content']):
                logger.info(f"الخبر لا يتعلق بالعراق: {news['title']}")
                return None

            # التحقق من أن الخبر منشور في تاريخ اليوم
            if not self._is_today(news['date']):
                logger.info(f"الخبر ليس من تاريخ اليوم: {news['title']} - {news['date']}")
                return None

        return news

    def _extract_generic_news(self, url):
        """استخراج الأخبار من المواقع العامة"""
        try:
            # تحديد رؤوس HTTP عشوائية لتجنب الحظر
            headers = self.headers.copy()
            headers['User-Agent'] = random.choice(self.user_agents)

            # محاولات إعادة المحاولة
            for attempt in range(self.max_retries):
                try:
                    # جلب صفحة الخبر
                    response = requests.get(url, headers=headers, timeout=self.timeout)
                    response.raise_for_status()
                    break
                except (requests.RequestException, ConnectionError) as e:
                    if attempt < self.max_retries - 1:
                        # انتظار قبل إعادة المحاولة
                        wait_time = random.uniform(1, 3) * (attempt + 1)
                        logger.warning(f"فشل في جلب {url}. إعادة المحاولة بعد {wait_time:.1f} ثوان...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"فشل في جلب {url} بعد {self.max_retries} محاولات: {str(e)}")
                        return None

            # التأكد من أن الصفحة بالعربية
            if 'content-type' in response.headers and 'charset' in response.headers['content-type']:
                encoding = response.headers['content-type'].split('charset=')[-1]
                response.encoding = encoding
            else:
                response.encoding = 'utf-8'

            # تحليل الصفحة
            soup = BeautifulSoup(response.text, 'html.parser')

            # استخراج عنوان الخبر
            title = self._extract_title(soup)
            if not title:
                logger.warning(f"لم يتم العثور على عنوان للخبر: {url}")
                return None

            # استخراج محتوى الخبر
            content = self._extract_content(soup)
            if not content:
                logger.warning(f"لم يتم العثور على محتوى للخبر: {url}")
                return None

            # استخراج تاريخ الخبر
            news_date = self._extract_date(soup)

            # إنشاء بصمة المحتوى
            hash_text = f"{title}|{content}"
            content_hash = hashlib.md5(hash_text.encode('utf-8')).hexdigest()

            return {
                'title': title,
                'content': content,
                'date': news_date,
                'url': url,
                'content_hash': content_hash
            }

        except Exception as e:
            logger.error(f"خطأ في جلب محتوى الخبر {url}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None

    def _is_iraq_related(self, title, content):
        """التحقق من أن الخبر يتعلق بالعراق"""
        # التحقق من وجود كلمات دالة على العراق في العنوان
        if any(keyword in title.lower() for keyword in self.iraq_keywords):
            return True

        # التحقق من وجود كلمات دالة على العراق في المحتوى
        if any(keyword in content.lower() for keyword in self.iraq_keywords):
            return True

        # حساب نسبة الكلمات المتعلقة بالعراق في المحتوى
        words = re.findall(r'\b\w+\b', content.lower())
        iraq_words = [word for word in words if any(keyword in word for keyword in self.iraq_keywords)]

        # إذا كانت نسبة الكلمات المتعلقة بالعراق أكثر من 5%، فالخبر متعلق بالعراق
        if len(words) > 0 and len(iraq_words) / len(words) > 0.05:
            return True

        return False

    def _is_arabic_text(self, text):
        """التحقق من أن النص باللغة العربية"""
        if not text:
            return False

        # نطاق الأحرف العربية في يونيكود
        arabic_range = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')

        # حساب عدد الأحرف العربية في النص
        arabic_chars = len(re.findall(arabic_range, text))
        total_chars = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

        # إذا كانت نسبة الأحرف العربية أكثر من 30%، فالنص عربي
        return total_chars > 0 and arabic_chars / total_chars > 0.3

    def _is_today(self, news_date):
        """التحقق من أن الخبر منشور في تاريخ اليوم"""
        # إذا كان التاريخ غير محدد، نفترض أنه من تاريخ اليوم
        if not news_date:
            return True

        today = date.today()

        # تحقق إضافي من صحة التاريخ
        try:
            # التأكد من أن التاريخ ليس في المستقبل
            if news_date > today:
                logger.warning(f"تاريخ الخبر في المستقبل: {news_date}، سيتم اعتباره من تاريخ اليوم")
                return True

            # التأكد من أن التاريخ ليس قديمًا جدًا (أكثر من 3 أيام)
            if (today - news_date).days > 3:
                logger.warning(f"تاريخ الخبر قديم جدًا: {news_date}، سيتم تجاهله")
                return False

            # نقبل الأخبار المنشورة في تاريخ اليوم أو الأمس (لمراعاة فروق التوقيت)
            return news_date >= today - timedelta(days=1)

        except Exception as e:
            logger.error(f"خطأ في التحقق من تاريخ الخبر: {str(e)}")
            # في حالة حدوث خطأ، نفترض أنه من تاريخ اليوم
            return True

    # دوال مخصصة للمواقع الشائعة

    def _extract_from_alsumaria(self, url):
        """استخراج الأخبار من موقع السومرية نيوز"""
        try:
            # جلب صفحة الخبر
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # تحليل الصفحة
            soup = BeautifulSoup(response.text, 'html.parser')

            # استخراج العنوان
            title_element = soup.find('h1', class_='title')
            if not title_element:
                title_element = soup.find('meta', property='og:title')
                title = title_element.get('content') if title_element else None
            else:
                title = title_element.text.strip()

            if not title:
                return None

            # استخراج المحتوى
            content_element = soup.find('div', class_='details')
            if content_element:
                # إزالة العناصر غير المرغوب فيها
                for element in content_element.find_all(['script', 'style', 'iframe', 'aside', 'nav']):
                    element.decompose()

                # الحصول على النص من الفقرات
                paragraphs = content_element.find_all('p')
                if paragraphs:
                    content = '\n\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
                else:
                    content = content_element.get_text(separator='\n\n').strip()
            else:
                return None

            # استخراج التاريخ
            date_element = soup.find('div', class_='date')
            if date_element:
                date_text = date_element.text.strip()
                try:
                    # تحليل التاريخ
                    news_date = parser.parse(date_text, fuzzy=True).date()
                except:
                    news_date = date.today()
            else:
                news_date = date.today()

            # إنشاء بصمة المحتوى
            hash_text = f"{title}|{content}"
            content_hash = hashlib.md5(hash_text.encode('utf-8')).hexdigest()

            return {
                'title': title,
                'content': content,
                'date': news_date,
                'url': url,
                'content_hash': content_hash
            }
        except Exception as e:
            logger.error(f"خطأ في استخراج الخبر من السومرية: {str(e)}")
            return None

    def _extract_from_iraqnews(self, url):
        """استخراج الأخبار من موقع شبكة أخبار العراق"""
        try:
            # جلب صفحة الخبر
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # تحليل الصفحة
            soup = BeautifulSoup(response.text, 'html.parser')

            # استخراج العنوان
            title_element = soup.find('h1', class_='entry-title')
            if not title_element:
                title_element = soup.find('meta', property='og:title')
                title = title_element.get('content') if title_element else None
            else:
                title = title_element.text.strip()

            if not title:
                return None

            # استخراج المحتوى
            content_element = soup.find('div', class_='entry-content')
            if content_element:
                # إزالة العناصر غير المرغوب فيها
                for element in content_element.find_all(['script', 'style', 'iframe', 'aside', 'nav', 'div', 'figure']):
                    element.decompose()

                # الحصول على النص من الفقرات
                paragraphs = content_element.find_all('p')
                if paragraphs:
                    content = '\n\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
                else:
                    content = content_element.get_text(separator='\n\n').strip()
            else:
                return None

            # استخراج التاريخ
            date_element = soup.find('time', class_='entry-date')
            if date_element:
                date_text = date_element.get('datetime') or date_element.text.strip()
                try:
                    # تحليل التاريخ
                    news_date = parser.parse(date_text).date()
                except:
                    news_date = date.today()
            else:
                news_date = date.today()

            # إنشاء بصمة المحتوى
            hash_text = f"{title}|{content}"
            content_hash = hashlib.md5(hash_text.encode('utf-8')).hexdigest()

            return {
                'title': title,
                'content': content,
                'date': news_date,
                'url': url,
                'content_hash': content_hash
            }
        except Exception as e:
            logger.error(f"خطأ في استخراج الخبر من شبكة أخبار العراق: {str(e)}")
            return None

    def _extract_title(self, soup):
        """استخراج عنوان الخبر"""
        title = None

        # محاولة العثور على العنوان في وسم h1
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            # تجاهل العناوين الفارغة أو القصيرة جدًا
            if h1.text and len(h1.text.strip()) > 10:
                # التحقق من أن العنوان يحتوي على كلمات كافية
                words = re.findall(r'\b\w+\b', h1.text.strip())
                if len(words) >= 3:
                    title = h1.text.strip()
                    break

        if title:
            return title

        # محاولة العثور على العنوان في وسم h2 إذا لم يتم العثور على h1 مناسب
        h2_tags = soup.find_all('h2')
        for h2 in h2_tags:
            # تجاهل العناوين الفارغة أو القصيرة جدًا
            if h2.text and len(h2.text.strip()) > 10:
                # التحقق من أن العنوان يحتوي على كلمات كافية
                words = re.findall(r'\b\w+\b', h2.text.strip())
                if len(words) >= 3:
                    title = h2.text.strip()
                    break

        if title:
            return title

        # محاولة العثور على العنوان في وسم meta
        meta_title_tags = [
            soup.find('meta', property='og:title'),
            soup.find('meta', attrs={'name': 'title'}),
            soup.find('meta', attrs={'name': 'twitter:title'}),
            soup.find('meta', attrs={'itemprop': 'name'})
        ]

        for meta_tag in meta_title_tags:
            if meta_tag and meta_tag.get('content'):
                content = meta_tag.get('content').strip()
                if len(content) > 10:
                    title = content
                    break

        if title:
            return title

        # محاولة العثور على العنوان في وسم title
        title_tag = soup.find('title')
        if title_tag and title_tag.text:
            # إزالة اسم الموقع من العنوان إذا وجد
            title_text = title_tag.text.strip()

            # قائمة بالفواصل الشائعة بين عنوان الخبر واسم الموقع
            separators = [' - ', ' | ', ' :: ', ' » ', ' // ', ' – ', ' — ']

            for separator in separators:
                if separator in title_text:
                    parts = title_text.split(separator)
                    # عادة ما يكون عنوان الخبر هو الجزء الأول (أو الأخير في بعض المواقع العربية)
                    if len(parts[0]) > len(parts[-1]):
                        title = parts[0].strip()
                    else:
                        title = parts[-1].strip()
                    break

            if not title:
                title = title_text

        # التحقق من أن العنوان باللغة العربية
        if title and self._is_arabic_text(title):
            return title

        return title

    def _extract_content(self, soup):
        """استخراج محتوى الخبر"""
        content = None

        # قائمة بالعناصر غير المرغوب فيها
        unwanted_elements = ['script', 'style', 'iframe', 'aside', 'nav', 'header', 'footer', 'form',
                            'button', 'noscript', 'meta', 'link', 'input', 'select', 'option', 'textarea']

        # قائمة بالفئات غير المرغوب فيها
        unwanted_classes = ['comment', 'share', 'social', 'related', 'sidebar', 'menu', 'navigation',
                           'ad', 'advertisement', 'banner', 'promo', 'recommended', 'footer', 'header']

        # إزالة العناصر غير المرغوب فيها من النسخة المستخدمة للاستخراج
        soup_copy = BeautifulSoup(str(soup), 'html.parser')

        # إزالة العناصر غير المرغوب فيها
        for element in soup_copy.find_all(unwanted_elements):
            element.decompose()

        # إزالة العناصر ذات الفئات غير المرغوب فيها
        for element in soup_copy.find_all(class_=lambda c: c and any(cls in c.lower() for cls in unwanted_classes)):
            element.decompose()

        # محاولة العثور على المحتوى في وسوم المقالات الشائعة
        article = soup_copy.find('article')
        if article:
            # الحصول على النص من الفقرات
            paragraphs = article.find_all('p')
            if paragraphs:
                content = '\n\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
                if len(content) > 100:  # التأكد من أن المحتوى كافٍ
                    return content

            # إذا لم يتم العثور على فقرات، استخدم النص الكامل للمقالة
            content = article.get_text(separator='\n\n').strip()
            if len(content) > 100:
                return content

        # محاولة العثور على المحتوى في وسوم div مع فئات محددة
        content_keywords = ['content', 'article', 'story', 'text', 'body', 'entry', 'post',
                           'محتوى', 'مقال', 'نص', 'خبر', 'تفاصيل', 'موضوع', 'تقرير']

        content_divs = soup_copy.find_all(['div', 'section', 'main'],
                                        class_=lambda c: c and any(keyword in c.lower() for keyword in content_keywords))

        if content_divs:
            for div in content_divs:
                # الحصول على النص من الفقرات
                paragraphs = div.find_all('p')
                if paragraphs:
                    content = '\n\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
                    if len(content) > 100:  # التأكد من أن المحتوى كافٍ
                        return content

                # إذا لم يتم العثور على فقرات، استخدم النص الكامل للعنصر
                content = div.get_text(separator='\n\n').strip()
                if len(content) > 100:
                    return content

        # محاولة العثور على المحتوى في وسوم p
        paragraphs = soup_copy.find_all('p')
        if paragraphs:
            # تصفية الفقرات القصيرة جدًا
            valid_paragraphs = [p.text.strip() for p in paragraphs if len(p.text.strip()) > 20]
            if valid_paragraphs:
                content = '\n\n'.join(valid_paragraphs)
                if len(content) > 100:  # التأكد من أن المحتوى كافٍ
                    return content

        # التحقق من أن المحتوى باللغة العربية
        if content and self._is_arabic_text(content):
            return content

        # إذا لم يتم العثور على محتوى، استخدم النص الكامل للصفحة كملاذ أخير
        if not content:
            # استخراج النص من جسم الصفحة
            body = soup_copy.find('body')
            if body:
                content = body.get_text(separator='\n\n').strip()
                # تنظيف المحتوى من الأسطر الفارغة المتكررة
                content = re.sub(r'\n{3,}', '\n\n', content)
                if len(content) > 100 and self._is_arabic_text(content):
                    return content

        return content

    def _extract_date(self, soup):
        """استخراج تاريخ الخبر"""
        try:
            # قاموس أسماء الأشهر بمختلف اللغات والتنسيقات
            month_names = {
                # الأشهر العربية
                'يناير': 1, 'فبراير': 2, 'مارس': 3, 'أبريل': 4, 'مايو': 5, 'يونيو': 6,
                'يوليو': 7, 'أغسطس': 8, 'سبتمبر': 9, 'أكتوبر': 10, 'نوفمبر': 11, 'ديسمبر': 12,
                # الأشهر العربية (الشام)
                'كانون الثاني': 1, 'شباط': 2, 'آذار': 3, 'نيسان': 4, 'أيار': 5, 'حزيران': 6,
                'تموز': 7, 'آب': 8, 'أيلول': 9, 'تشرين الأول': 10, 'تشرين الثاني': 11, 'كانون الأول': 12,
                # الأشهر الإنجليزية
                'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
                # الأشهر الإنجليزية المختصرة
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                # أسماء الأشهر العربية المختصرة
                'ينا': 1, 'فبر': 2, 'مار': 3, 'أبر': 4, 'ماي': 5, 'يون': 6,
                'يول': 7, 'أغس': 8, 'سبت': 9, 'أكت': 10, 'نوف': 11, 'ديس': 12,
                # أسماء الأشهر الهجرية
                'محرم': 1, 'صفر': 2, 'ربيع الأول': 3, 'ربيع الثاني': 4, 'جمادى الأولى': 5, 'جمادى الآخرة': 6,
                'رجب': 7, 'شعبان': 8, 'رمضان': 9, 'شوال': 10, 'ذو القعدة': 11, 'ذو الحجة': 12,
                # صيغ إضافية للأشهر العربية
                'يناير/كانون الثاني': 1, 'فبراير/شباط': 2, 'مارس/آذار': 3, 'أبريل/نيسان': 4,
                'مايو/أيار': 5, 'يونيو/حزيران': 6, 'يوليو/تموز': 7, 'أغسطس/آب': 8,
                'سبتمبر/أيلول': 9, 'أكتوبر/تشرين الأول': 10, 'نوفمبر/تشرين الثاني': 11, 'ديسمبر/كانون الأول': 12,
                # صيغ مختصرة إضافية
                'كانون ثاني': 1, 'كانون أول': 12, 'تشرين أول': 10, 'تشرين ثاني': 11,
                'ك٢': 1, 'شب': 2, 'آذ': 3, 'نيس': 4, 'أي': 5, 'حز': 6, 'تم': 7, 'آ': 8, 'أيل': 9, 'ت١': 10, 'ت٢': 11, 'ك١': 12,
                'ك2': 1, 'ت1': 10, 'ت2': 11, 'ك1': 12
            }

            # 1. محاولة استخدام dateutil.parser لتحليل التواريخ في وسوم meta
            meta_date_properties = [
                'article:published_time', 'og:published_time', 'published_time', 'date', 'pubdate',
                'article:modified_time', 'og:updated_time', 'lastmod', 'created', 'modified'
            ]

            for prop in meta_date_properties:
                meta_date = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
                if meta_date and meta_date.get('content'):
                    try:
                        parsed_date = parser.parse(meta_date.get('content'))
                        return parsed_date.date()
                    except:
                        pass

            # 2. محاولة العثور على التاريخ في وسوم الوقت
            for time_tag in soup.find_all('time'):
                # محاولة استخدام سمة datetime
                if time_tag.get('datetime'):
                    try:
                        parsed_date = parser.parse(time_tag.get('datetime'))
                        return parsed_date.date()
                    except:
                        pass

                # محاولة استخدام نص العنصر
                if time_tag.text.strip():
                    try:
                        parsed_date = parser.parse(time_tag.text.strip(), fuzzy=True)
                        return parsed_date.date()
                    except:
                        pass

            # 3. محاولة العثور على التاريخ في عناصر HTML مع سمات تاريخ
            date_attrs = ['pubdate', 'datetime', 'date-time', 'date', 'data-date', 'data-timestamp']
            for attr in date_attrs:
                for element in soup.find_all(attrs={attr: True}):
                    try:
                        parsed_date = parser.parse(element[attr])
                        return parsed_date.date()
                    except:
                        pass

            # 4. البحث عن عناصر HTML التي قد تحتوي على تاريخ
            date_classes = ['date', 'time', 'datetime', 'published', 'pubdate', 'timestamp',
                           'article-date', 'post-date', 'entry-date', 'meta-date', 'date-published',
                           'publish-date', 'article-info', 'post-meta', 'post-info', 'news-date',
                           'تاريخ', 'وقت', 'نشر']

            date_elements = []

            # البحث عن عناصر بفئات محددة
            for cls in date_classes:
                date_elements.extend(soup.find_all(class_=lambda c: c and cls.lower() in c.lower()))

            # البحث عن عناصر بسمات محددة
            date_elements.extend(soup.find_all(['time', 'span', 'div', 'p', 'small']))

            # 5. أنماط التاريخ المختلفة للبحث في النص
            date_patterns = [
                # أنماط التاريخ العربية
                r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})',  # DD/MM/YYYY
                r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})',  # YYYY/MM/DD
                r'(\d{1,2})[-\s]([ا-ي]+)[-\s](\d{4})',  # DD MonthArabic YYYY
                r'([ا-ي]+)[-\s](\d{1,2})[-\s,](\d{4})',  # MonthArabic DD, YYYY
                # أنماط التاريخ الإنجليزية
                r'(\d{1,2})[-\s]([a-zA-Z]+)[-\s](\d{4})',  # DD Month YYYY
                r'([a-zA-Z]+)[-\s](\d{1,2})[-\s,](\d{4})',  # Month DD, YYYY
                # أنماط التاريخ مع اليوم
                r'(الأحد|الإثنين|الثلاثاء|الأربعاء|الخميس|الجمعة|السبت)[-\s،,][-\s]*(\d{1,2})[-\s]([ا-ي]+)[-\s](\d{4})',  # Day, DD MonthArabic YYYY
                r'(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)[-\s,][-\s]*(\d{1,2})[-\s]([a-zA-Z]+)[-\s](\d{4})',  # Day, DD Month YYYY
                # أنماط التاريخ مع الوقت
                r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})[-\s،,][-\s]*(\d{1,2}):(\d{2})',  # DD/MM/YYYY HH:MM
                r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})[-\s،,][-\s]*(\d{1,2}):(\d{2})',  # YYYY/MM/DD HH:MM
                # أنماط إضافية للتاريخ العربي
                r'(\d{1,2})[-\s/]([ا-ي٠-٩/]+)[-\s/](\d{4})',  # DD MonthArabic/Combined YYYY
                r'(\d{1,2})[-\s]([ا-ي]+)[-\s](\d{2})',  # DD MonthArabic YY (سنة مختصرة)
                r'(\d{1,2})[-\s]([ا-ي]+)',  # DD MonthArabic (السنة الحالية)
                r'اليوم[-\s،,](\d{1,2})[-\s]([ا-ي]+)[-\s](\d{4})',  # "اليوم" DD MonthArabic YYYY
                r'أمس[-\s،,](\d{1,2})[-\s]([ا-ي]+)[-\s](\d{4})',  # "أمس" DD MonthArabic YYYY
                r'منذ (\d{1,2}) ساعة',  # "منذ XX ساعة" (اليوم)
                r'منذ (\d{1,2}) دقيقة',  # "منذ XX دقيقة" (اليوم)
                r'قبل (\d{1,2}) ساعة',  # "قبل XX ساعة" (اليوم)
                r'قبل (\d{1,2}) دقيقة',  # "قبل XX دقيقة" (اليوم)
                # أنماط التاريخ الهجري
                r'(\d{1,2})[-\s]([ا-ي]+)[-\s](\d{4})[-\s]هـ',  # DD MonthArabic YYYY هـ
                r'(\d{1,2})[-\s]([ا-ي]+)[-\s](\d{4})[-\s]هجري',  # DD MonthArabic YYYY هجري
                # أنماط التاريخ بالأرقام العربية
                r'([\u0660-\u0669]{1,2})[/.-]([\u0660-\u0669]{1,2})[/.-]([\u0660-\u0669]{4})',  # DD/MM/YYYY بالأرقام العربية
            ]

            # البحث عن التاريخ في النص
            for element in date_elements:
                text = element.text.strip()

                # محاولة استخدام dateutil.parser
                try:
                    parsed_date = parser.parse(text, fuzzy=True)
                    # التحقق من أن التاريخ معقول (بين 2000 و 2100)
                    if 2000 <= parsed_date.year <= 2100:
                        return parsed_date.date()
                except:
                    pass

                # البحث باستخدام أنماط التاريخ
                for pattern in date_patterns:
                    match = re.search(pattern, text)
                    if match:
                        try:
                            # معالجة التواريخ النسبية
                            if pattern == r'منذ (\d{1,2}) ساعة' or pattern == r'قبل (\d{1,2}) ساعة':
                                # منذ/قبل X ساعة - نحسب التاريخ بناءً على الساعات
                                hours = int(match.group(1))
                                return datetime.now().date() if hours < 24 else datetime.now().date() - timedelta(days=1)

                            elif pattern == r'منذ (\d{1,2}) دقيقة' or pattern == r'قبل (\d{1,2}) دقيقة':
                                # منذ/قبل X دقيقة - نعتبره اليوم
                                return datetime.now().date()

                            elif pattern == r'(\d{1,2})[-\s]([ا-ي]+)' and len(match.groups()) == 2:
                                # DD MonthArabic (بدون سنة) - نفترض السنة الحالية
                                day = int(match.group(1))
                                month_name = match.group(2).lower()
                                year = datetime.now().year

                                # تحويل اسم الشهر إلى رقم
                                if month_name in month_names:
                                    month = month_names[month_name]
                                else:
                                    # محاولة العثور على اسم الشهر في القاموس
                                    for key in month_names:
                                        if key in month_name:
                                            month = month_names[key]
                                            break
                                    else:
                                        continue

                                # التحقق من صحة التاريخ
                                if 1 <= day <= 31 and 1 <= month <= 12:
                                    return date(year, month, day)

                            # معالجة التواريخ بالأرقام العربية
                            elif pattern == r'([\u0660-\u0669]{1,2})[/.-]([\u0660-\u0669]{1,2})[/.-]([\u0660-\u0669]{4})':
                                # تحويل الأرقام العربية إلى أرقام إنجليزية
                                arabic_to_english = {
                                    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
                                    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
                                }

                                day_str = match.group(1)
                                month_str = match.group(2)
                                year_str = match.group(3)

                                for ar, en in arabic_to_english.items():
                                    day_str = day_str.replace(ar, en)
                                    month_str = month_str.replace(ar, en)
                                    year_str = year_str.replace(ar, en)

                                day = int(day_str)
                                month = int(month_str)
                                year = int(year_str)

                                # التحقق من صحة التاريخ
                                if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100:
                                    return date(year, month, day)

                            # تحديد نوع النمط
                            elif 'MonthArabic' in pattern or 'Month' in pattern:
                                # نمط يحتوي على اسم الشهر
                                if pattern.startswith(r'([ا-ي]+)') or pattern.startswith(r'([a-zA-Z]+)'):
                                    # MonthArabic DD, YYYY
                                    month_name = match.group(1).lower()
                                    day = int(match.group(2))
                                    year = int(match.group(3)) if len(match.groups()) >= 3 else datetime.now().year
                                else:
                                    # DD MonthArabic YYYY
                                    day = int(match.group(1))
                                    month_name = match.group(2).lower()
                                    year = int(match.group(3)) if len(match.groups()) >= 3 else datetime.now().year

                                    # إذا كانت السنة مكونة من رقمين فقط (YY)
                                    if year < 100:
                                        year = 2000 + year

                                # تحويل اسم الشهر إلى رقم
                                if month_name in month_names:
                                    month = month_names[month_name]
                                else:
                                    # محاولة العثور على اسم الشهر في القاموس
                                    for key in month_names:
                                        if key in month_name:
                                            month = month_names[key]
                                            break
                                    else:
                                        continue
                            elif pattern.startswith(r'(\d{4})'):
                                # YYYY/MM/DD
                                year = int(match.group(1))
                                month = int(match.group(2))
                                day = int(match.group(3))
                            else:
                                # DD/MM/YYYY
                                day = int(match.group(1))
                                month = int(match.group(2))
                                year = int(match.group(3))

                            # التحقق من صحة التاريخ
                            if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100:
                                return date(year, month, day)
                        except Exception as e:
                            logger.debug(f"خطأ في تحليل التاريخ: {str(e)}")
                            pass

            # 6. البحث عن تاريخ في URL
            url_date_patterns = [
                r'/(\d{4})/(\d{1,2})/(\d{1,2})/',  # /YYYY/MM/DD/
                r'/(\d{4})[-_](\d{1,2})[-_](\d{1,2})/',  # /YYYY-MM-DD/
                r'/(\d{1,2})[-_](\d{1,2})[-_](\d{4})/',  # /DD-MM-YYYY/
            ]

            url = soup.find('meta', property='og:url')
            if url and url.get('content'):
                url_text = url.get('content')
                for pattern in url_date_patterns:
                    match = re.search(pattern, url_text)
                    if match:
                        try:
                            if pattern.startswith(r'/(\d{4})'):
                                # /YYYY/MM/DD/
                                year = int(match.group(1))
                                month = int(match.group(2))
                                day = int(match.group(3))
                            else:
                                # /DD-MM-YYYY/
                                day = int(match.group(1))
                                month = int(match.group(2))
                                year = int(match.group(3))

                            # التحقق من صحة التاريخ
                            if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100:
                                return date(year, month, day)
                        except:
                            pass
        except Exception as e:
            logger.error(f"خطأ في استخراج التاريخ: {str(e)}")

        # إذا لم يتم العثور على تاريخ، استخدم تاريخ اليوم
        return date.today()
