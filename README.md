# PricePulse | Selenium E-Commerce Price Scraper

**PricePulse**, Python, **FastAPI**, **Selenium WebDriver** ve **Tailwind CSS** kullanılarak geliştirilmiş, çoklu kaynak destekli dinamik bir e-ticaret fiyat toplama ve karşılaştırma uygulamasıdır.

## Özellikler
- **Çoklu Kaynak Desteği:** Çok sayfalı katalog (`BooksToScrape`) ile birlikte `Amazon TR` ve `Trendyol` arama sayfalarından ürün ve fiyat verisi çeker.
- **Akıllı Fiyat Ayrıştırma ve Sıralama:** Farklı para birimi ve yerel formatlardaki (`14.299,90 TL`, `£51.77`) fiyat metinlerini sayısal değerlere dönüştürerek en ucuzdan pahalıya sıralar.
- **Tek Tıkla CSV Dışa Aktarma:** Toplanan ürün listesini `fiyat_raporu.csv` formatında indirmenizi sağlar.
- **Esnek Tarayıcı Kontrolü:** Otomasyonu arka planda (`Headless`) veya canlı Chrome penceresinde gözlemleyerek çalıştırma imkânı sunar.
- **Modern Web Arayüzü:** FastAPI REST uç noktaları ve Tailwind CSS ile hazırlanmış duyarlı kontrol paneli üzerinden yönetilir.

## Teknoloji Yığını
- **Backend:** Python 3, FastAPI, Uvicorn
- **Web Otomasyonu:** Selenium WebDriver, WebDriver Manager
- **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript (Fetch API)

## Kurulum ve Çalıştırma

1. Depoyu klonlayın:
   ```bash
   git clone [https://github.com/inandenizturk/selenium.py.git](https://github.com/inandenizturk/selenium.py.git)
   cd selenium.py
