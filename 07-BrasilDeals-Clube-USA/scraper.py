import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

from database import save_deal
from deal_processor import extract_asin_from_amazon_url, generate_amazon_affiliate_link
from config import SLICKDEALS_RSS_FEED, AMAZON_PARTNER_TAG
from logging import logger

async def fetch_slickdeals_rss(feed_url: str) -> str | None:
    """Fetches the content of an RSS feed."""
    try:
        logger.info(f"Fetching RSS feed from: {feed_url}")
        response = requests.get(feed_url, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors
        logger.info("RSS feed fetched successfully.")
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching RSS feed {feed_url}: {e}")
        return None

def parse_rss_item(item_xml) -> dict | None:
    """
    Parses a single RSS item (deal) from BeautifulSoup XML object
    and extracts relevant information.
    """
    title = item_xml.find('title').text if item_xml.find('title') else 'No Title'
    link = item_xml.find('link').text if item_xml.find('link') else '#'
    description_full = item_xml.find('description').text if item_xml.find('description') else ''

    # Clean HTML from description
    soup = BeautifulSoup(description_full, 'lxml')
    description_text = soup.get_text(separator=' ', strip=True)

    pub_date_str = item_xml.find('pubDate').text if item_xml.find('pubDate') else None
    pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z') if pub_date_str else datetime.utcnow()

    # Extract discount percentage (example for Slickdeals format)
    # This might need to be adjusted for other RSS feeds
    discount_match = re.search(r'(\d+)% off', title, re.IGNORECASE)
    discount_percentage = float(discount_match.group(1)) if discount_match else 0.0

    # Category detection (simple heuristic, can be improved)
    category = 'General'
    if 'electronics' in title.lower() or 'tv' in title.lower() or 'laptop' in title.lower():
        category = 'Electronics'
    elif 'home' in title.lower() or 'kitchen' in title.lower():
        category = 'Home'
    elif 'clothing' in title.lower() or 'apparel' in title.lower():
        category = 'Clothing'
    elif 'game' in title.lower() or 'console' in title.lower():
        category = 'Games'
    elif 'food' in title.lower() or 'grocery' in title.lower():
        category = 'Food'

    logger.debug(f"Parsed RSS item: Title='{title}', Link='{link}', Discount={discount_percentage}%")

    return {
        'title': title,
        'description': description_text,
        'link': link,
        'discount_percentage': discount_percentage,
        'category': category,
        'posted_at': pub_date
    }

async def scrape_slickdeals_rss() -> list[dict]:
    """
    Scrapes the Slickdeals RSS feed, parses items,
    generates affiliate links, and attempts to save deals to the DB.
    Returns a list of parsed deal dictionaries (including affiliate link and ASIN).
    """
    xml_content = await fetch_slickdeals_rss(SLICKDEALS_RSS_FEED)
    if not xml_content:
        return []

    soup = BeautifulSoup(xml_content, 'lxml')
    items = soup.find_all('item')
    logger.info(f"Found {len(items)} items in RSS feed.")

    processed_deals = []
    for item in items:
        deal_data = parse_rss_item(item)
        if deal_data:
            # Extract ASIN and generate affiliate link for Amazon deals
            if "amazon.com" in deal_data['link'].lower():
                asin = extract_asin_from_amazon_url(deal_data['link'])
                deal_data['asin'] = asin
                if AMAZON_PARTNER_TAG:
                    deal_data['affiliate_link'] = generate_amazon_affiliate_link(
                        deal_data['link'], AMAZON_PARTNER_TAG
                    )
                else:
                    logger.warning("AMAZON_PARTNER_TAG not configured. Affiliate link will not be generated.")
                    deal_data['affiliate_link'] = deal_data['link']
            else:
                deal_data['affiliate_link'] = deal_data['link'] # Use original link if not Amazon or no tag

            # Save to DB and get the ID
            deal_id = save_deal(deal_data)
            if deal_id:
                deal_data['id'] = deal_id
                processed_deals.append(deal_data)

    logger.info(f"Scraped and processed {len(processed_deals)} new or existing deals from RSS.")
    return processed_deals