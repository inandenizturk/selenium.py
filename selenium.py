import asyncio
import csv
import io
import re
import socket
import threading
import time
import webbrowser
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

app = FastAPI(title="PricePulse | Selenium E-Commerce Scraper")
LAST_RESULTS = []


def build_driver(headless: bool = False) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    else:
        opts.add_experimental_option("detach", True)  # Pencere kendiliğinden kapanmaz
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(15)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def parse_price(raw: str) -> float:
    cleaned = re.sub(r"[^\d.,]", "", raw)
    if not cleaned:
        return 0.0
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def scrape_products(query: str, site: str, headless: bool = False) -> list[dict]:
    driver = build_driver(headless=headless)
    items = []

    try:
        if site == "amazon":
            driver.get(f"https://www.amazon.com.tr/s?k={query.replace(' ', '+')}")
            time.sleep(3.5)
            driver.execute_script("window.scrollBy(0, 700);")
            time.sleep(1.0)

            cards = driver.find_elements(By.CSS_SELECTOR, "div[data-asin]")
            for c in cards:
                asin = (c.get_attribute("data-asin") or "").strip()
                if not asin:
                    continue
                try:
                    h2s = c.find_elements(By.TAG_NAME, "h2")
                    wholes = c.find_elements(By.CSS_SELECTOR, "span.a-price-whole")
                    if not h2s or not wholes:
                        continue
                    title = h2s[0].text.strip()
                    whole = wholes[0].text.replace(".", "").strip()
                    fracs = c.find_elements(By.CSS_SELECTOR, "span.a-price-fraction")
                    frac = fracs[0].text.strip() if fracs else "00"
                    links = c.find_elements(By.CSS_SELECTOR, "a.a-link-normal")
                    link = links[0].get_attribute("href") if links else f"https://www.amazon.com.tr/dp/{asin}"

                    raw_price = f"{whole},{frac} TL"
                    val = parse_price(raw_price)
                    if title and val > 0:
                        items.append({"site": "Amazon TR", "title": title, "price_str": raw_price, "price_val": val, "url": link})
                except Exception:
                    continue

        elif site == "trendyol":
            driver.get(f"https://www.trendyol.com/sr?q={query.replace(' ', '%20')}")
            time.sleep(4.0)
            driver.execute_script("window.scrollBy(0, 700);")
            time.sleep(1.0)

            cards = driver.find_elements(By.CSS_SELECTOR, "div.p-card-wrppr, div[data-id]")
            for c in cards[:25]:
                try:
                    text_lines = [line.strip() for line in c.text.split("\n") if line.strip()]
                    price_line = next((l for l in text_lines if "TL" in l), "")
                    if not price_line or len(text_lines) < 2:
                        continue
                    title = " ".join(text_lines[:2])
                    link = c.find_element(By.TAG_NAME, "a").get_attribute("href")
                    val = parse_price(price_line)
                    if title and val > 0:
                        items.append({"site": "Trendyol", "title": title, "price_str": price_line, "price_val": val, "url": link})
                except Exception:
                    continue

        else:
            for page in (1, 2):
                driver.get(f"https://books.toscrape.com/catalogue/page-{page}.html")
                time.sleep(0.8)
                cards = driver.find_elements(By.CSS_SELECTOR, "article.product_pod")
                q_low = query.lower().strip()
                for c in cards:
                    title = c.find_element(By.CSS_SELECTOR, "h3 a").get_attribute("title")
                    if q_low and q_low not in title.lower():
                        continue
                    raw_price = c.find_element(By.CSS_SELECTOR, "p.price_color").text.strip()
                    link = c.find_element(By.CSS_SELECTOR, "h3 a").get_attribute("href")
                    val = parse_price(raw_price)
                    items.append({"site": "BooksToScrape", "title": title, "price_str": raw_price, "price_val": val, "url": link})

        if not items:
            page_title = driver.title or "Başlıksız Sayfa"
            raise RuntimeError(
                f"Bot koruması veya boş sonuç (Açılan sayfa: '{page_title}'). "
                "Chrome penceresini açık bıraktım, ekrandan kontrol edebilirsin."
            )

        items.sort(key=lambda x: x["price_val"])
        if headless:
            driver.quit()
        return items
    except Exception:
        if headless:
            driver.quit()
        raise


HTML_UI = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>PricePulse | Selenium Fiyat Toplayıcı</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
<div class="w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-5">
  <div class="flex flex-wrap justify-between items-center gap-2 border-b border-slate-800 pb-4">
    <div>
      <h1 class="text-lg font-bold text-cyan-400">PricePulse <span class="text-xs font-normal text-slate-400">| Selenium E-Ticaret Fiyat Botu</span></h1>
      <p class="text-xs text-slate-400 mt-0.5">Çoklu Kaynak Tarama, Anti-Detection Bayrakları & CSV Raporlama</p>
    </div>
    <div class="flex items-center gap-2">
      <a href="/export" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition">CSV İndir</a>
      <span id="badge" class="text-xs px-2.5 py-1.5 rounded-lg bg-slate-800 text-slate-300 border border-slate-700">Hazır</span>
    </div>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-12 gap-2.5">
    <select id="site" class="sm:col-span-3 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:border-cyan-400 focus:outline-none">
      <option value="sandbox">BooksToScrape (Çok Sayfalı)</option>
      <option value="amazon">Amazon TR</option>
      <option value="trendyol">Trendyol</option>
    </select>
    <input id="query" type="text" value="" placeholder="Ürün adı (tümü için boş bırak)" class="sm:col-span-5 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:border-cyan-400 focus:outline-none" />
    <label class="sm:col-span-2 flex items-center justify-center gap-1.5 bg-slate-950 border border-slate-800 rounded-xl px-2 text-xs text-slate-300 cursor-pointer">
      <input id="headless" type="checkbox" class="accent-cyan-400"> Headless
    </label>
    <button onclick="runScrape()" id="btn" class="sm:col-span-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold rounded-xl py-2.5 text-sm transition">Tara</button>
  </div>

  <div id="err" class="hidden bg-rose-950/70 border border-rose-500/60 text-rose-200 text-xs p-3 rounded-xl"></div>

  <div class="overflow-x-auto border border-slate-800 rounded-xl max-h-96 overflow-y-auto">
    <table class="w-full text-left text-xs">
      <thead class="bg-slate-950 text-slate-400 border-b border-slate-800 sticky top-0">
        <tr>
          <th class="p-3">Kaynak</th>
          <th class="p-3">Ürün Adı</th>
          <th class="p-3 text-right">Fiyat (Artan)</th>
          <th class="p-3 text-center">Bağlantı</th>
        </tr>
      </thead>
      <tbody id="tbody" class="divide-y divide-slate-800/70">
        <tr><td colspan="4" class="p-6 text-center text-slate-500">Arama başlatmak için Tara butonuna basın.</td></tr>
      </tbody>
    </table>
  </div>
</div>

<script>
async function runScrape(){
  const site = document.getElementById('site').value;
  const query = document.getElementById('query').value.trim();
  const headless = document.getElementById('headless').checked;
  const err = document.getElementById('err');
  const badge = document.getElementById('badge');
  const btn = document.getElementById('btn');
  const tbody = document.getElementById('tbody');

  err.classList.add('hidden');
  badge.innerText = 'Tarayıcı Çalışıyor...';
  badge.className = 'text-xs px-2.5 py-1.5 rounded-lg bg-amber-950 text-amber-300 border border-amber-700';
  btn.disabled = true;

  try {
    const r = await fetch(`/scrape?site=${site}&query=${encodeURIComponent(query)}&headless=${headless}`);
    const d = await r.json();
    if(!r.ok) throw new Error(d.detail || 'Tarama başarısız.');

    tbody.innerHTML = d.items.map((it, idx) => `
      <tr class="hover:bg-slate-800/40 ${idx === 0 ? 'bg-emerald-950/20' : ''}">
        <td class="p-3 font-medium text-cyan-300 whitespace-nowrap">${it.site}</td>
        <td class="p-3 text-slate-200">${it.title} ${idx === 0 ? '<span class="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-emerald-900 text-emerald-300">En Ucuz</span>' : ''}</td>
        <td class="p-3 text-right font-mono font-bold text-emerald-400 whitespace-nowrap">${it.price_str}</td>
        <td class="p-3 text-center"><a href="${it.url}" target="_blank" class="text-cyan-400 hover:underline">Aç ↗</a></td>
      </tr>
    `).join('');

    badge.innerText = d.items.length + ' Ürün Bulundu ✓';
    badge.className = 'text-xs px-2.5 py-1.5 rounded-lg bg-emerald-950 text-emerald-300 border border-emerald-700';
  } catch (e) {
    err.innerText = e.message;
    err.classList.remove('hidden');
    badge.innerText = 'Hata';
    badge.className = 'text-xs px-2.5 py-1.5 rounded-lg bg-rose-950 text-rose-300 border border-rose-700';
  } finally {
    btn.disabled = false;
  }
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_UI


@app.get("/scrape")
def scrape_endpoint(site: str = "sandbox", query: str = "", headless: bool = False):
    global LAST_RESULTS
    try:
        LAST_RESULTS = scrape_products(query=query, site=site, headless=headless)
        return {"count": len(LAST_RESULTS), "items": LAST_RESULTS}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/export")
def export_csv():
    if not LAST_RESULTS:
        raise HTTPException(status_code=400, detail="Dışa aktarılacak veri yok.")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["site", "title", "price_str", "price_val", "url"])
    writer.writeheader()
    writer.writerows(LAST_RESULTS)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="fiyat_raporu.csv"'},
    )


def find_free_port(default_port: int = 8000) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", default_port)) != 0:
            return default_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


if __name__ == "__main__":
    port = find_free_port(8000)
    threading.Thread(
        target=lambda: (time.sleep(1.0), webbrowser.open(f"http://127.0.0.1:{port}")),
        daemon=True,
    ).start()
    try:
        asyncio.get_running_loop()
        threading.Thread(
            target=lambda: uvicorn.run(app, host="127.0.0.1", port=port, log_level="error"),
            daemon=True,
        ).start()
    except RuntimeError:
        uvicorn.run(app, host="127.0.0.1", port=port)
