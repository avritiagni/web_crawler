from web_crawler import crawler
import concurrent.futures
from config import DOMAIN_TO_RUN


def run_web_crawler_for_domain(domain: str):
    """
    Run the web crawler for a given domain.

    Args:
        domain (str): The domain to crawl.

    Returns:
        None
    """
    web_crawler = crawler.WebCrawler(domain)
    web_crawler.crawl_site_for_products()

def crawl_ecommerce_domains(domains: list):
    threadpool = concurrent.futures.ThreadPoolExecutor()
    for domain in domains:
        futures = []
        futures.append(threadpool.submit(run_web_crawler_for_domain, domain))
    for future in concurrent.futures.as_completed(futures):
        future.result()


# Run the crawler
if __name__ == '__main__':
    crawl_ecommerce_domains(DOMAIN_TO_RUN)
