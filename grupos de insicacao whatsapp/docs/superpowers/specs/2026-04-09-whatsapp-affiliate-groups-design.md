# WhatsApp Affiliate Groups Bot — Design Spec

**Date:** 2026-04-09
**Status:** Approved
**Author:** Brainstorming session with user

---

## Overview

A fully autonomous bot that runs 24/7 on a cloud server, automatically finds the best deals from Amazon and other US affiliate programs, and posts 10 messages per day across multiple WhatsApp groups — split by language (Portuguese and Spanish). The user requires zero technical intervention after initial setup.

---

## Goals

- Post 10 affiliate-linked deals/services per day across all active WhatsApp groups
- Support multiple groups simultaneously, each tagged with a language (PT or ES)
- Rank products by a score combining discount percentage × log(number of reviews)
- Rotate daily service promotions (Wise, Remitly, Policygenius, insurance, etc.)
- Format messages attractively with emojis, price comparison, ratings, and affiliate link
- Provide a simple web dashboard for non-technical operation
- Alert the user by email if any component fails

---

## Non-Goals

- Users cannot reply in groups (read-only broadcast groups)
- No e-commerce checkout or payment processing
- No customer support chat automation
- No mobile app — web dashboard only
- No Telegram support in v1

---

## Constraints

- **Bot number must be group admin.** The dedicated WhatsApp number must be added as an administrator in every group. This means new groups must be created with the bot as admin — existing groups where the user is not admin cannot be used.
- **Amazon PA-API requires prior sales.** Amazon's Product Advertising API is only granted after an active affiliate account makes 3 qualifying sales within 180 days. At launch, product data will be fetched via alternative sources (see Product Scraper section) until PA-API access is unlocked.
- **SQLite concurrency limit.** SQLite is used in v1. It handles low-concurrency writes well but is not suited for high-volume simultaneous writes. Upgrade to PostgreSQL is recommended when posting to more than 20 groups simultaneously.

---

## Platform Risk Disclosure

**Evolution API uses an unofficial WhatsApp connection method.** It works by emulating a WhatsApp Web session and is not sanctioned by Meta. Using it for automated posting violates WhatsApp's Terms of Service. Risks include:

- Temporary or permanent ban of the dedicated phone number
- No official support or appeal process from WhatsApp/Meta

**Mitigation strategy included in this design:**
- Use a number dedicated exclusively to this bot (never personal use)
- Post no more than 10 messages/day per group
- Add human-like random delays between messages
- Never message individual users — only post to groups where bot is admin

**The user has been informed of this risk and accepts it.** If Meta cracks down, the fallback plan is to migrate to Telegram channels (official API, zero ban risk).

---

## Affiliate Programs

| Program | Category | Commission |
|---|---|---|
| Amazon Associates | Products | 1–10% per sale |
| Walmart Affiliates | Products | ~1–4% per sale |
| Wise | Remittance | ~$10–30 per signup |
| Remitly | Remittance | ~$10–30 per signup |
| Policygenius | Insurance | ~$20–100 per lead |
| Lemonade | Insurance | Per lead |
| Credit Karma / NerdWallet | Finance | Per lead |

---

## Architecture

### Components

**1. VPS Server**
- Provider: DigitalOcean or Vultr (~$6–12/month)
- OS: Ubuntu 22.04
- All services run via Docker Compose
- Deployed via a single install script that prompts for environment variables (affiliate tags, passwords, timezone) and starts all containers

**2. WhatsApp Connector (Evolution API)**
- Self-hosted Evolution API instance running in Docker
- One dedicated phone number (eSIM or physical SIM)
- User scans QR code once to link the number
- If session expires, the dashboard shows a "Re-scan QR" alert and sends an email notification
- Sends messages to all active groups

**3. Product Scraper**

*Phase 1 (launch — before PA-API access):*
- Scrapes publicly available deal aggregators (e.g., CamelCamelCamel, Slickdeals RSS, DealNews RSS) to source Amazon product URLs with verified discounts
- No API key required

*Phase 2 (after PA-API access unlocked):*
- Connects directly to Amazon Product Advertising API
- Optional: RapidAPI connectors for Walmart and other stores

**Ranking formula (both phases):**
```
score = discount_percent × log10(review_count)
```
Minimum thresholds: ≥4.0 stars, ≥50 reviews, ≥15% discount.

Runs daily at midnight. Stores top 9 products in the day's schedule.

**4. Service Rotation Calendar**
- Predefined list of affiliate services
- Rotates one service per day in a fixed cycle
- 1 service post per day, 9 product posts per day
- Example cycle: Wise → Remitly → Policygenius → Lemonade → Credit Karma → repeat

**5. Message Formatter**
- Generates formatted WhatsApp message per language (PT or ES)
- Portuguese template:
  ```
  🔥 OFERTA DO DIA 🔥

  📦 [Nome do Produto]
  ⭐ 4.8/5 (2.847 avaliações)

  💰 Era: ~~$89.99~~
  ✅ Agora: $34.99 (-61% OFF)

  🛒 Compre aqui 👇
  [short link]

  #Amazon #Oferta #Promoção
  ```
- Spanish version uses equivalent template with ES copy

**6. Link Shortener / Click Tracker**
- Self-hosted redirect service (e.g., YOURLS running in Docker)
- All affiliate links are wrapped: `https://yourdomain.com/xyz` → redirects to Amazon with affiliate tag
- Captures click count before forwarding
- Amazon affiliate tag is preserved in the redirect destination
- This is the only reliable way to track clicks on Amazon links, as Amazon strips external UTM parameters

**7. Scheduler**
- Distributes 10 posts across the day
- Default posting times (US Eastern): 7h, 9h, 11h, 13h, 15h, 17h, 19h, 20h, 21h, 22h
- All active groups receive the same post at each scheduled time
- Random 5–15 second delay between sending to different groups
- Times configurable via dashboard
- On send failure: retries once after 60 seconds, then logs error and sends email alert

**8. Group Manager**
- Stores list of active groups with metadata: group ID, language (PT/ES), display name, status
- User adds groups by pasting the WhatsApp group ID into the dashboard
- Each group tagged as PT or ES — receives posts in respective language
- Groups can be individually paused without stopping the bot
- No limit on number of groups

**9. Web Dashboard**
- Simple Flask web app, HTTPS, password protected
- Features:
  - View today's scheduled posts with status (pending / sent / failed)
  - View post history (last 30 days)
  - Add / remove / pause groups
  - Adjust posting schedule
  - View click stats (clicks per post via link shortener)
  - QR code re-scan panel (shown when session expires)
  - Pause/resume the entire bot
  - Email alert configuration

**10. Alert System**
- Sends email notification on: Evolution API session expiry, message send failure, scraper returning zero results, VPS disk >80%
- Email via SMTP (Gmail app password or SendGrid free tier)

**11. Database**
- SQLite in v1 (file-based, zero configuration)
- Tables: `products`, `services`, `posts`, `groups`, `post_history`, `clicks`
- Upgrade path to PostgreSQL documented; recommended threshold: >20 active groups

---

## Data Flow

```
[midnight]
  Scraper → fetch top deals from deal aggregators (or PA-API)
  Score & rank → select top 9 products
  Service calendar → select 1 service for today
  Link shortener → generate short tracked URLs for each item
  Store 10 scheduled posts in database

[throughout day — per scheduled time]
  Scheduler triggers post
  Message Formatter generates PT version and ES version
  For each active PT group: Evolution API sends PT message (with delay)
  For each active ES group: Evolution API sends ES message (with delay)
  Log result to post_history

[on failure]
  Retry once after 60s
  Log failure
  Send email alert to user
```

---

## Setup Steps for User (one-time)

1. Create affiliate accounts: Amazon Associates, Wise, Remitly, Policygenius
2. Purchase VPS (DigitalOcean $6 droplet) and eSIM phone number
3. Register a cheap domain (~$10/year) for the dashboard and link shortener
4. SSH into VPS and run one install command (install script provided):
   ```
   curl -s https://raw.githubusercontent.com/.../install.sh | bash
   ```
   Script prompts for: affiliate tags, email for alerts, dashboard password, timezone
5. Open dashboard URL in browser, scan WhatsApp QR code
6. Create WhatsApp groups, add bot number as admin
7. In dashboard: add group IDs and assign language (PT or ES)
8. Bot starts running automatically on schedule

---

## Cost Estimate

| Item | Monthly Cost |
|---|---|
| VPS (DigitalOcean Droplet 1GB) | $6 |
| Phone number (eSIM — e.g., Airalo) | $5–15 |
| Domain (~$10/year) | ~$1 |
| RapidAPI (optional, Phase 2) | $0–25 |
| SendGrid email alerts (free tier) | $0 |
| **Total** | **~$12–47/month** |

---

## Revenue Potential

Estimated based on: 2% CTR on posted links, 3% purchase conversion on clicks, average $40 order value, Amazon 4% commission rate. Service leads estimated at 1 conversion per 500 group members per month.

| Scenario | Active Members | Est. Monthly Revenue |
|---|---|---|
| Starting | 100–500 | $20–150 |
| Growing | 500–2,000 | $150–600 |
| Scaled | 2,000+ | $600–2,000+ |

*Note: actual results depend heavily on group engagement, niche relevance, and affiliate program performance.*

---

## Failure Recovery Playbook

| Failure | Detection | Recovery |
|---|---|---|
| WhatsApp session expired | Dashboard alert + email | User re-scans QR in dashboard |
| Amazon scraper returns 0 results | Email alert | Bot uses previous day's top products as fallback |
| Message send fails | Logged + email after retry | User checks dashboard; bot continues with next post |
| VPS goes down | No posts sent | User restarts VPS from DigitalOcean panel; Docker auto-restarts containers |
| Phone number banned by WhatsApp | Posts stop | Get new eSIM, re-scan QR |

---

## Future Enhancements (out of scope for v1)

- Telegram parallel channels (official API, zero ban risk — recommended fallback)
- Image/thumbnail in posts (WhatsApp media messages)
- Price drop alerts (monitor specific products)
- Subscriber growth tracking
- A/B testing message formats
- Multi-language support beyond PT/ES
- Upgrade to PostgreSQL for high group count
