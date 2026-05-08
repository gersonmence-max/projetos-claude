import re
from datetime import datetime
from config import AMAZON_PARTNER_TAG
from logging import logger

# Emoji mapping for categories
CATEGORY_EMOJIS = {
    "electronics": "📱",
    "home": "🏠",
    "clothing": "👕",
    "food": "🍔",
    "games": "🎮",
    "books": "📚",
    "health": "💊",
    "beauty": "💄",
    "auto": "🚗",
    "travel": "✈️",
    "services": "💻",
    "default": "✨"
}

def filter_deals(deals: list[dict], min_discount_percentage: float = 50.0) -> list[dict]:
    """
    Filters a list of deals, keeping only those with a discount percentage
    greater than or equal to the specified minimum.
    """
    filtered_deals = [
        deal for deal in deals
        if deal.get('discount_percentage', 0) >= min_discount_percentage
    ]
    logger.info(f"Filtered {len(deals)} deals to {len(filtered_deals)} deals with >= {min_discount_percentage}% discount.")
    return filtered_deals

def get_category_emoji(category: str | None) -> str:
    """Returns an emoji based on the deal's category."""
    if category:
        normalized_category = category.lower().strip()
        for key, emoji in CATEGORY_EMOJIS.items():
            if key in normalized_category:
                return emoji
    return CATEGORY_EMOJIS["default"]

def format_deal_message(deal: dict) -> str:
    """
    Formats a deal into a human-readable message for Telegram/WhatsApp.
    Includes affiliate link, emoji, and timestamp.
    """
    title = deal.get('title', 'Oferta Imperdível!')
    description = deal.get('description', '')
    original_link = deal.get('link', '#')
    affiliate_link = deal.get('affiliate_link', original_link)
    discount = deal.get('discount_percentage')
    category = deal.get('category')
    posted_at = deal.get('posted_at', datetime.now())

    emoji = get_category_emoji(category)

    discount_str = f" 🔥 {discount:.0f}% OFF" if discount else ""
    category_str = f" #{category.replace(' ', '')}" if category else ""

    message = (
        f"{emoji} {title}{discount_str}\n\n"
        f"{description}\n\n"
        f"🔗 <a href='{affiliate_link}'>Ver Oferta Agora!</a>\n\n"
        f"📅 {posted_at.strftime('%d/%m %H:%M')}{category_str}\n"
        f"#ClubeUSA #Oferta"
    )
    return message

def extract_asin_from_amazon_url(url: str) -> str | None:
    """
    Extracts the ASIN (Amazon Standard Identification Number) from an Amazon product URL.
    ASINs are typically 10 characters, either alphanumeric (for books) or just numeric.
    """
    # Regex for common Amazon product URL patterns
    match = re.search(r'(?:/dp/|/gp/product/|/exec/obidos/ASIN/)([A-Z0-9]{10})', url)
    if match:
        return match.group(1)
    return None

def generate_amazon_affiliate_link(original_url: str, partner_tag: str) -> str:
    """
    Generates an Amazon affiliate link from an original Amazon URL.
    This function primarily focuses on adding or updating the 'tag' parameter.
    """
    if not partner_tag or "amazon." not in original_url:
        return original_url

    # Check if a tag already exists
    if 'tag=' in original_url:
        # Replace existing tag
        affiliate_url = re.sub(r'tag=[^&]*', f'tag={partner_tag}', original_url)
    else:
        # Add tag
        if '?' in original_url:
            affiliate_url = f"{original_url}&tag={partner_tag}"
        else:
            affiliate_url = f"{original_url}?tag={partner_tag}"

    return affiliate_url