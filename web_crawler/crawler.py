import requests
import xml.etree.ElementTree as ET
import gzip
import os
from io import BytesIO
import queue
from bs4 import BeautifulSoup
from config import MAX_PRODUCT_COUNT
from web_crawler.exceptions import MaxProductLimitReached


class WebCrawler:

    def __init__(self, domain: str):
        self.domain = domain
        self.domain_folder_name = domain.split("//")[-1]
        self.product_links = set()
        self.sitemap_queue = queue.Queue()
        self.already_processed_sitemaps = set()
        self.requests_session = requests.Session()
        self.product_link_contains = ['/p/', '/product/', '/dp/', '/item/', '/pd/', '/t/', '/products/']
        self.product_count = 0
        self.max_products = MAX_PRODUCT_COUNT
        

    def get_sitemap_urls_for_domain(self):
        """
        Retrieves the sitemap URLs for a given domain by parsing the domain's robots.txt file.

        Returns:
            list: A list of sitemap URLs found in the domain's robots.txt file.
        """
        sitemap_urls = []
        res = self.requests_session.get(url = f'{self.domain}/robots.txt')
        robots_content = res.content.decode()
        robots_content_lines = [line.strip() for line in robots_content.split("\n")]
        for line in robots_content_lines:
            if line.lower().startswith("sitemap:"):
                sitemap_url = ':'.join(line.split(':')[:0:-1][::-1]).strip()
                sitemap_urls.append(sitemap_url)
        return sitemap_urls
    

    def is_product_url(self, url: str):
        """
        Check if a given URL is a product URL.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL contains any of the patterns specified in 
                  self.product_link_contains, indicating it is a product URL. 
                  False otherwise.
        """
        for pattern in  self.product_link_contains:
            if pattern in url:
                return True
            # else:
            #     try:
            #         res = self.requests_session.get(url)
            #         if res.status_code == 200:
            #             if '"@type": "product"' in res.text.lower():
            #                 return True
            #     except Exception as e:
            #         print(f"Error checking product URL {url}: {e}")
        return False


    def fetch_product_url_from_given_url(self, url: str):
        """
        Fetches product URLs from a given URL.

        This method checks if the given URL is a product URL. If it is, the URL is added to the product links set.
        If the URL is not a product URL, it fetches the page content and extracts all product URLs from the page.

        Args:
            url (str): The URL to check and fetch product URLs from.

        Returns:
            None
        """
        if self.product_count >= self.max_products:
            raise MaxProductLimitReached("Max products limit reached")
        # Check if the given URL is a product URL
        if self.is_product_url(url):
            self.product_links.add(url)
            self.product_count +=1
            print("Product found: ", url)
            return
        res = self.requests_session.get(url)
        if res.status_code == 200:
            if '"@type": "product"' in res.text.lower():
                self.product_links.add(url)
                self.product_count +=1
                print("Product found: ", url)
                return

        # If not a product URL, extract product URLs from the page
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        urls = [link['href'] for link in links]
        urls = [url for url in urls if self.is_product_url(url)]
        urls = [url if self.domain in url else f"{self.domain}{url}" for url in urls]
        self.product_links.update(urls)
        self.product_count += len(urls)
        print("Product found: ", urls)
        return 
    
    def is_static_url(self, url: str):
        """
        Check if a given URL is a static URL.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL ends with any of the patterns specified in 
                  self.static_link_ends, indicating it is a static URL. 
                  False otherwise.
        """
        static_link_ends = ['.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.webp']
        for pattern in static_link_ends:
            if pattern in url:
                return True
        return False

    def get_urls_from_sitemap_content(self, sitemap_url: str):
        """
        Retrieves URLs from the content of a sitemap.
        This method fetches the sitemap content from the given URL, parses it, and extracts URLs.
        If the sitemap URL has already been processed, it will be skipped. If the sitemap content
        is compressed (ends with .gz), it will be decompressed before parsing.
        Args:
            sitemap_url (str): The URL of the sitemap to process.
        Raises:
            requests.RequestException: If there is an issue with the HTTP request.
            gzip.BadGzipFile: If there is an issue with decompressing the gzip file.
            Exception: For any other exceptions that may occur during processing.
        Notes:
            - URLs ending with .xml or .gz are added to the sitemap queue for further processing.
            - Other URLs are processed as product links.
            - Errors encountered during processing are printed to the console.
        """
        if sitemap_url in self.already_processed_sitemaps:
            return
        try:
            sitemap_resp = self.requests_session.get(sitemap_url, timeout=10, stream=True)
            sitemap_resp.raise_for_status()
            sitemap_content = sitemap_resp.content
            if sitemap_url.endswith('.gz'):
                sitemap_content = gzip.decompress(sitemap_content)
            for event, elem in ET.iterparse(BytesIO(sitemap_content), events=('end',)):
                if 'loc' in elem.tag.split('}')[-1]:
                    if elem.text and elem.text.strip():
                        url = elem.text.strip()
                        if self.domain not in url:
                            url = f"{self.domain}{url}"
                        if url.endswith('.xml') or url.endswith('.gz'):
                            self.sitemap_queue.put(url)
                        elif self.is_static_url(url):
                            continue
                        else:
                            try:
                                if self.domain not in url:
                                    url = f"{self.domain}{url}"
                                self.fetch_product_url_from_given_url(url)
                            except MaxProductLimitReached as e:
                                print(f"Max products limit of {self.max_products} reached: {e}")
                                return
                            except requests.RequestException as e:
                                print(f"Error processing product link {url}: {e}")
                elem.clear()
        except (requests.RequestException, gzip.BadGzipFile, Exception) as e:
            print(f"Error processing sitemap url {sitemap_url}: {e}")
        self.already_processed_sitemaps.add(sitemap_url)
        return


    def save_products_to_file(self):
        """
        Saves the product links to a file.
        The product links are saved to a file named 'product_links.txt' in the domain folder.
        Returns:
            None
        """
        if not self.product_links:
            return
        if not os.path.exists(self.domain_folder_name):
            os.makedirs(self.domain_folder_name)
        with open(f'{self.domain_folder_name}/product_links.txt', 'a') as f:
            f.write('\n'.join(self.product_links))
        if self.product_count >= self.max_products:
            raise MaxProductLimitReached("Max products reached")
        self.product_links = set()
        return
    

    def crawl_site_for_products(self):
        """
        Extracts product links from a given sitemap URL.
        Returns:
            list: A list of product links found in the sitemap.
        """
        site_map_urls = self.get_sitemap_urls_for_domain()
        for site_map_url in site_map_urls:
            self.sitemap_queue.put(site_map_url)
        while not self.sitemap_queue.empty():
            self.get_urls_from_sitemap_content(self.sitemap_queue.get())
            try:
                self.save_products_to_file()
            except MaxProductLimitReached as e:
                print(f"Max products limit of {self.max_products} reached: {e}")
                return
        return
