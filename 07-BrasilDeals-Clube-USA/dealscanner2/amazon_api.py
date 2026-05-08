# ============================================================
#  amazon_api.py — Cliente PA-API sem SDK externo
#  Assina requisicoes com AWS Signature Version 4
#  Nao precisa instalar nada alem de 'requests'
# ============================================================

import hmac
import hashlib
import json
import datetime
import requests

HOST      = "webservices.amazon.com"
REGION    = "us-east-1"
SERVICE   = "ProductAdvertisingAPI"
ENDPOINT  = f"https://{HOST}/paapi5/searchitems"


# ============================================================
#  AWS4 SIGNING
# ============================================================

def _sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def _get_signature_key(secret_key, date_stamp, region, service):
    k_date    = _sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region  = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing

def _sha256_hex(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def build_signed_request(access_key, secret_key, partner_tag, payload_dict):
    """Constroi e assina uma requisicao PA-API."""

    payload    = json.dumps(payload_dict, separators=(",", ":"))
    now        = datetime.datetime.utcnow()
    amz_date   = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    # Headers obrigatorios
    headers_to_sign = {
        "content-encoding": "amz-1.0",
        "content-type":     "application/json; charset=utf-8",
        "host":             HOST,
        "x-amz-date":       amz_date,
        "x-amz-target":     "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
    }

    # Canonical request
    canonical_headers = "".join(
        f"{k}:{v}\n" for k, v in sorted(headers_to_sign.items())
    )
    signed_headers = ";".join(sorted(headers_to_sign.keys()))

    canonical_request = "\n".join([
        "POST",
        "/paapi5/searchitems",
        "",
        canonical_headers,
        signed_headers,
        _sha256_hex(payload),
    ])

    # String to sign
    credential_scope = f"{date_stamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign   = "\n".join([
        "AWS4-HMAC-SHA256",
        amz_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    # Signature
    signing_key = _get_signature_key(secret_key, date_stamp, REGION, SERVICE)
    signature   = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    # Authorization header
    auth = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    final_headers = {**headers_to_sign, "Authorization": auth}
    return payload, final_headers


def search_items(access_key, secret_key, partner_tag, keywords,
                 search_index="All", item_count=10):
    """
    Busca produtos na Amazon PA-API.
    Retorna lista de dicts com dados dos produtos.
    """

    payload_dict = {
        "Keywords":     keywords,
        "PartnerTag":   partner_tag,
        "PartnerType":  "Associates",
        "Marketplace":  "www.amazon.com",
        "SearchIndex":  search_index,
        "ItemCount":    item_count,
        "Resources": [
            "ItemInfo.Title",
            "ItemInfo.ByLineInfo",
            "Offers.Listings.Price",
            "Offers.Listings.SavingBasis",
            "Offers.Listings.Availability.Type",
            "Offers.Summaries.LowestPrice",
            "CustomerReviews.StarRating",
            "CustomerReviews.Count",
            "Images.Primary.Medium",
            "BrowseNodeInfo.BrowseNodes",
        ],
    }

    payload, headers = build_signed_request(
        access_key, secret_key, partner_tag, payload_dict
    )

    try:
        resp = requests.post(ENDPOINT, data=payload, headers=headers, timeout=15)
    except requests.RequestException as e:
        return None, f"Erro de rede: {e}"

    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("Errors", [{}])[0].get("Message", resp.text[:200])
        except Exception:
            msg = resp.text[:200]
        return None, f"API erro {resp.status_code}: {msg}"

    try:
        data = resp.json()
    except Exception:
        return None, "Resposta invalida da API"

    items = data.get("SearchResult", {}).get("Items", [])
    return items, None
