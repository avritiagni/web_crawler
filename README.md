# Web Crawler

## Description

This webcrawler extracts the product links from the websites using following steps:

1. Looks for {domain}/robots.txt and fetches all the sitemap urls available.
2. Using sitemap xml crawler navigrates through the website and checks for product urls along the way.
3. It have specific patterns which are commonly used in product links across websites using which it identifies product url.
4. Checks for MAX_PRODUCTS and stops once reached the max product count.
5. Once done it saves the product links inside {domain}/product_links.txt file.

## Run the crawler

1. Create and activate virtual env
    ```
    conda create -n venv python=3.X
    conda activate venv
    ```

2. Install requirements.txt
    ```
    pip install -r requirements.txt
    ```

3. Run app.py: Before running the application change the DOMAIN_TO_RUN and MAX_PRODUCTS in config.py to have the new domains 
    ```
    python app.py
    ```

