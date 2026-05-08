import os
import httpx
from dotenv import load_dotenv

load_dotenv()

_client = None


class _QueryBuilder:
    def __init__(self, base_url, headers, table):
        self._base_url = base_url
        self._table = table
        self._headers = dict(headers)
        self._method = "GET"
        self._select = "*"
        self._filters = {}
        self._body = None
        self._order = None
        self._limit = None
        self._range_start = None
        self._range_end = None
        self._single = False

    def select(self, fields="*", count=None):
        self._select = fields
        self._method = "GET"
        if count:
            self._headers["Prefer"] = f"count={count}"
        return self

    def insert(self, data):
        self._method = "POST"
        self._body = data
        self._headers["Prefer"] = "return=representation"
        return self

    def upsert(self, data, on_conflict=None):
        self._method = "POST"
        self._body = data
        pref = "return=representation,resolution=merge-duplicates"
        if on_conflict:
            pref += f",on_conflict={on_conflict}"
        self._headers["Prefer"] = pref
        return self

    def update(self, data):
        self._method = "PATCH"
        self._body = data
        self._headers["Prefer"] = "return=representation"
        return self

    def delete(self):
        self._method = "DELETE"
        self._headers["Prefer"] = "return=representation"
        return self

    def eq(self, col, val):
        self._filters[col] = f"eq.{val}"
        return self

    def neq(self, col, val):
        self._filters[col] = f"neq.{val}"
        return self

    def gte(self, col, val):
        self._filters[col] = f"gte.{val}"
        return self

    def lte(self, col, val):
        self._filters[col] = f"lte.{val}"
        return self

    def gt(self, col, val):
        self._filters[col] = f"gt.{val}"
        return self

    def in_(self, col, vals):
        self._filters[col] = f"in.({','.join(str(v) for v in vals)})"
        return self

    def is_(self, col, val):
        self._filters[col] = f"is.{val}"
        return self

    def order(self, col, desc=False):
        self._order = f"{col}.{'desc' if desc else 'asc'}"
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, start, end):
        self._range_start = start
        self._range_end = end
        return self

    def single(self):
        self._single = True
        self._headers["Accept"] = "application/vnd.pgrst.object+json"
        return self

    def execute(self):
        url = f"{self._base_url}/{self._table}"
        params = dict(self._filters)

        if self._method == "GET":
            params["select"] = self._select
        if self._order:
            params["order"] = self._order
        if self._limit:
            params["limit"] = str(self._limit)
        if self._range_start is not None:
            self._headers["Range"] = f"{self._range_start}-{self._range_end}"
            self._headers["Range-Unit"] = "items"

        with httpx.Client(timeout=30) as client:
            if self._method == "GET":
                resp = client.get(url, headers=self._headers, params=params)
            elif self._method == "POST":
                resp = client.post(url, headers=self._headers, params=params, json=self._body)
            elif self._method == "PATCH":
                resp = client.patch(url, headers=self._headers, params=params, json=self._body)
            elif self._method == "DELETE":
                resp = client.delete(url, headers=self._headers, params=params)

        if resp.status_code >= 400:
            raise Exception(f"Supabase error {resp.status_code}: {resp.text}")

        data = resp.json() if resp.content else ([] if not self._single else None)
        count = None
        cr = resp.headers.get("content-range", "")
        if "/" in cr:
            total = cr.split("/")[1]
            count = int(total) if total.isdigit() else None

        return type("Result", (), {"data": data, "count": count})()


class _SupabaseClient:
    def __init__(self, url: str, key: str):
        self._base = f"{url}/rest/v1"
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def table(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(self._base, self._headers, name)

    def from_(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(self._base, self._headers, name)


def get_client() -> _SupabaseClient:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = _SupabaseClient(url, key)
    return _client
