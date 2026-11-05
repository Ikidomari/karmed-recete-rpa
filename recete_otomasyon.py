import json
import os
import re
import sys
import logging
from datetime import datetime
from typing import Union, Optional, Callable, Dict
from dotenv import load_dotenv
from playwright.sync_api import (
    sync_playwright,
    Page,
    Frame,
    FrameLocator,
    Locator,
    BrowserContext,
    Browser,
    expect,
    TimeoutError as PlaywrightTimeoutError,
)

# Loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ReceteRPA")

DEFAULT_KARMED_URL = "http://10.54.136.61:2015/Karmed/Default.aspx"


def get_base_dir() -> str:
    """PyInstaller (.exe) veya normal Python çalışmasına göre ana dizini döndürür."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def reload_env() -> str:
    """.exe veya script yanındaki .env dosyasını yükler ve dosya yolunu döndürür."""
    env_path = os.path.join(get_base_dir(), ".env")
    load_dotenv(dotenv_path=env_path, override=True)
    return env_path


# Başlangıçta .env dosyasını yükle
reload_env()


DEFAULT_SELECTORS: Dict[str, str] = {
    # --- 1. Karmed Hasta Arama Ekranı (ASP.NET / Ext.NET Default.aspx uyumlu) ---
    "SEARCH_CRITERIA_DROPDOWN": "select#aramaKriteri, input[name*='Kriter'], input[id*='cmbArama'], input[id*='AramaKriter'], [aria-label='Arama Kriteri']",
    "SEARCH_CRITERIA_OPTION_TEXT": "Örnek No",
    "SEARCH_INPUT": "input#ornekNoInput, input[id*='txtOrnek'], input[id*='txtArama'], input[placeholder*='Örnek'], input[name*='OrnekNo'], input[name='aramaMetni']",
    "SEARCH_BUTTON": "button:has-text('Ara'), .x-btn:has-text('Ara'), .x-btn-text:has-text('Ara'), button#btnAra, input[value='Ara']",
    "PATIENT_ROW": "div.x-grid3-row:has-text('{ornek_no}'), tr.x-grid-row:has-text('{ornek_no}'), table tbody tr:has-text('{ornek_no}')",
    # --- 2. Sağ Tık (Context Menu) ve Reçete Formu ---
    "CONTEXT_MENU_RECETE_YAZ": ".x-menu-item:has-text('Reçete Yaz'), a.x-menu-item-link:has-text('Reçete Yaz'), text='Reçete Yaz'",
    "BTN_YENI_F2": "button:has-text('Yeni (F2)'), .x-btn:has-text('Yeni (F2)'), .x-btn-text:has-text('Yeni (F2)'), button:has-text('Yeni')",
    "DOKTOR_DROPDOWN": "select#doktorId, input[id*='cmbDoktor'], input[id*='Doktor'], input[name*='doktor'], [placeholder*='Doktor']",
    "SABLONLAR_MENU": "button:has-text('Şablonlar'), .x-btn:has-text('Şablonlar'), .x-btn-text:has-text('Şablonlar'), text='Şablonlar'",
    "ILAC_GRID_ROW": ".ilac-listesi tr, .x-grid-item, .x-grid3-row, .x-grid-row",
    # --- 3. Reçetem Gönderim Menüsü ---
    "RECETEM_TOP_MENU": "button:has-text('Reçetem'), .x-btn:has-text('Reçetem'), .x-btn-text:has-text('Reçetem')",
    "RECETEM_SEND_OPTION": ".x-menu-item:has-text('Reçetem Sistemi Reçete Yaz'), text='Reçetem Sistemi Reçete Yaz(Seçilen Reçete Bilgileriyle)'",
    "RECETEM_IFRAME": "iframe[src*='recetem'], iframe[src*='enabiz'], iframe#recetemFrame",
    # --- 4. Reçetem Portalı (Ek Tanı & E-İmza) ---
    "EK_TANI_INPUT": "input[placeholder*='Tanı'], input#ekTaniInput, input[name*='tani'], .tani-arama-input",
    "EK_TANI_DROPDOWN_ITEM": ".ui-autocomplete li:has-text('{code}'), .dropdown-item:has-text('{code}'), tr:has-text('{code}'), .x-combo-list-item:has-text('{code}'), .x-boundlist-item:has-text('{code}')",
    "EK_TANI_EKLE_BTN": "button:has-text('Ekle'), button#btnTaniEkle, button:has-text('Kaydet')",
    "EIMZA_PANEL": "text='E-İMZA BİLGİLERİ'",
    "PIN_INPUT": "input[type='password'], input[placeholder*='Pin'], input#pinKodu, input[name*='pin']",
    "IMZALA_BTN": "button:has-text('İmzala'), input[type='button'][value='İmzala'], #btnImzala",
    # --- 5. Yükleme Göstergeleri ve Sonuç (Reçete No) ---
    "LOADING_MASK": ".x-mask-loading, .ext-el-mask-msg, .loading-spinner, .blockUI, .swal2-loading",
    "RECETE_NO_CONTAINER": (
        "#receteNo, [data-testid='recete-no'], "
        "td:right-of(:text('Reçete No')), "
        "span:right-of(:text('Reçete Numarası')), "
        ".recete-no-deger, .alert-success"
    ),
}


class Selectors:
    """
    Karmed RBYS ve Sağlık Bakanlığı Reçetem Sistemi DOM Seçicileri.
    .exe yanındaki 'selectors.json' dosyasından dinamik olarak okunur.
    """
    SEARCH_CRITERIA_DROPDOWN = DEFAULT_SELECTORS["SEARCH_CRITERIA_DROPDOWN"]
    SEARCH_CRITERIA_OPTION_TEXT = DEFAULT_SELECTORS["SEARCH_CRITERIA_OPTION_TEXT"]
    SEARCH_INPUT = DEFAULT_SELECTORS["SEARCH_INPUT"]
    SEARCH_BUTTON = DEFAULT_SELECTORS["SEARCH_BUTTON"]
    PATIENT_ROW = DEFAULT_SELECTORS["PATIENT_ROW"]
    CONTEXT_MENU_RECETE_YAZ = DEFAULT_SELECTORS["CONTEXT_MENU_RECETE_YAZ"]
    BTN_YENI_F2 = DEFAULT_SELECTORS["BTN_YENI_F2"]
    DOKTOR_DROPDOWN = DEFAULT_SELECTORS["DOKTOR_DROPDOWN"]
    SABLONLAR_MENU = DEFAULT_SELECTORS["SABLONLAR_MENU"]
    ILAC_GRID_ROW = DEFAULT_SELECTORS["ILAC_GRID_ROW"]
    RECETEM_TOP_MENU = DEFAULT_SELECTORS["RECETEM_TOP_MENU"]
    RECETEM_SEND_OPTION = DEFAULT_SELECTORS["RECETEM_SEND_OPTION"]
    RECETEM_IFRAME = DEFAULT_SELECTORS["RECETEM_IFRAME"]
    EK_TANI_INPUT = DEFAULT_SELECTORS["EK_TANI_INPUT"]
    EK_TANI_DROPDOWN_ITEM = DEFAULT_SELECTORS["EK_TANI_DROPDOWN_ITEM"]
    EK_TANI_EKLE_BTN = DEFAULT_SELECTORS["EK_TANI_EKLE_BTN"]
    EIMZA_PANEL = DEFAULT_SELECTORS["EIMZA_PANEL"]
    PIN_INPUT = DEFAULT_SELECTORS["PIN_INPUT"]
    IMZALA_BTN = DEFAULT_SELECTORS["IMZALA_BTN"]
    LOADING_MASK = DEFAULT_SELECTORS["LOADING_MASK"]
    RECETE_NO_CONTAINER = DEFAULT_SELECTORS["RECETE_NO_CONTAINER"]


def get_selectors_path() -> str:
    return os.path.join(get_base_dir(), "selectors.json")


def reload_selectors() -> Dict[str, str]:
    """selectors.json dosyasını okur (yoksa varsayılanlarla oluşturur) ve Selectors sınıfını günceller."""
    path = get_selectors_path()
    data = dict(DEFAULT_SELECTORS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_data = json.load(f)
                if isinstance(user_data, dict):
                    data.update(user_data)
        except Exception as err:
            logger.warning(f"selectors.json okunamadı, varsayılanlar kullanılıyor: {err}")
    else:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    for key, val in data.items():
        setattr(Selectors, key, val)
    return data


reload_selectors()


def _find_visible_locator(page: Page, selector: str, timeout: int = 15000) -> Locator:
    """
    Karmed Default.aspx (Ext.NET) yapısında modüller hem ana sayfada hem de alt iframe'ler
    içinde açılabildiği için, verilen seçiciyi hem ana sayfada hem de tüm alt frame'lerde arar.
    """
    # Önce hızlıca mevcut tüm frame'lerde görünür olan var mı kontrol et
    for frame in page.frames:
        try:
            loc = frame.locator(selector).first
            if loc.count() > 0 and loc.is_visible():
                return loc
        except Exception:
            continue

    # Henüz yüklenmediyse ana sayfa ve alt frame'ler üzerinde poll-free Playwright wait uygula
    # En son aktif/içerik barındıran frame'lere öncelik ver
    candidate_frames = [page.main_frame] + [f for f in page.frames if f != page.main_frame]
    per_frame_timeout = max(2500, timeout // max(1, len(candidate_frames)))

    for frame in reversed(candidate_frames):
        try:
            loc = frame.locator(selector).first
            loc.wait_for(state="visible", timeout=per_frame_timeout)
            return loc
        except Exception:
            continue

    # Son çare olarak ana sayfa locator'ı üzerinde kalan süreyle bekle (standart hata mesajı üretmesi için)
    fallback_loc = page.locator(selector).first
    expect(fallback_loc).to_be_visible(timeout=3000)
    return fallback_loc


def dump_page_diagnostics(page: Page, step_info: str = "", error_msg: str = "") -> str:
    """
    Hata anında aktif sayfadaki VE Karmed Default.aspx altındaki tüm iframe'lerdeki
    buton, input, select elementlerini 'debug_rapor.txt' dosyasına kaydeder.
    """
    report_path = os.path.join(get_base_dir(), "debug_rapor.txt")
    screenshot_path = os.path.join(get_base_dir(), "hata_ekran_goruntusu.png")

    try:
        page.screenshot(path=screenshot_path, full_page=True)
    except Exception:
        pass

    js_inspect = """
    () => {
        const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim().slice(0, 80);
        const isVis = (el) => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        };
        const items = [];
        document.querySelectorAll('input, select, textarea, button, a, .x-btn, .x-menu-item, [role="button"], iframe').forEach(el => {
            if (!isVis(el)) return;
            items.push({
                tag: el.tagName.toLowerCase(),
                id: el.id || '',
                name: el.getAttribute('name') || '',
                type: el.getAttribute('type') || '',
                cls: clean(el.className),
                placeholder: el.getAttribute('placeholder') || '',
                text: clean(el.innerText || el.value || ''),
                src: el.getAttribute('src') || ''
            });
        });
        return items.slice(0, 120);
    }
    """

    lines = [
        "============================================================",
        "  KARMED (Default.aspx) & REÇETEM - HATA ANALİZ RAPORU",
        "============================================================",
        f"Tarih/Saat : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Adım Bilgisi: {step_info}",
        f"Sayfa URL  : {page.url if page else 'Bilinmiyor'}",
        f"Hata Mesajı: {error_msg}",
        "------------------------------------------------------------",
        "SAYFA VE ALT IFRAME'LERDEKİ GÖRÜNÜR ELEMENTLER:",
        "------------------------------------------------------------",
    ]

    try:
        for f_idx, frame in enumerate(page.frames):
            frame_title = f"[FRAME {f_idx}] url='{frame.url}' name='{frame.name}'"
            lines.append(f"\n--- {frame_title} ---")
            try:
                elements = frame.evaluate(js_inspect)
                if not elements:
                    lines.append("  (Bu frame içinde görünür form/buton elementi yok)")
                for idx, el in enumerate(elements, 1):
                    lines.append(
                        f"  {idx:03d}. <{el['tag']}> "
                        f"id='{el['id']}' name='{el['name']}' type='{el['type']}' "
                        f"placeholder='{el['placeholder']}' text='{el['text']}' "
                        f"class='{el['cls']}' src='{el['src']}'"
                    )
            except Exception as fe:
                lines.append(f"  Frame okunamadı: {fe}")
    except Exception as eval_err:
        lines.append(f"Element listesi alınamadı: {eval_err}")

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        pass

    return report_path


def _wait_until_idle(target: Union[Page, Frame, FrameLocator], timeout: int = 15000) -> None:
    """Karmed veya Reçetem üzerindeki aktif yükleme maskelerinin (spinner/loading) kaybolmasını bekler."""
    mask = target.locator(Selectors.LOADING_MASK)
    try:
        if mask.count() > 0 and mask.first.is_visible():
            mask.first.wait_for(state="hidden", timeout=timeout)
    except PlaywrightTimeoutError:
        logger.debug("Yükleme maskesi bekleme süresi doldu, işleme devam ediliyor.")


def _launch_system_browser(playwright_instance, headless: bool, preferred_channel: str = "chrome") -> Browser:
    """
    Farklı bilgisayarlarda ekstra tarayıcı kurulumuna gerek kalmaması için
    öncelikle bilgisayarda yüklü olan Chrome veya Edge tarayıcısını başlatır.
    """
    channels_to_try = [preferred_channel, "chrome", "msedge"]
    seen = set()
    ordered_channels = [c for c in channels_to_try if c and not (c in seen or seen.add(c))]

    for channel in ordered_channels:
        if channel == "chromium":
            break
        try:
            logger.info(f"Sistem tarayıcısı başlatılıyor ({channel})...")
            return playwright_instance.chromium.launch(headless=headless, channel=channel)
        except Exception as err:
            logger.warning(f"'{channel}' başlatılamadı, alternatif deneniyor: {err}")

    logger.info("Yerleşik Playwright Chromium tarayıcısı başlatılıyor...")
    return playwright_instance.chromium.launch(headless=headless)


def _select_karmed_page(context: BrowserContext, karmed_url: str) -> Page:
    """Açık olan Chrome sekmeleri arasında Karmed (10.54.136.61 / Karmed) sekmesini bulur."""
    for p_tab in context.pages:
        if "10.54.136.61" in p_tab.url or "karmed" in p_tab.url.lower():
            p_tab.bring_to_front()
            return p_tab
    if context.pages:
        return context.pages[0]
    new_p = context.new_page()
    new_p.goto(karmed_url, wait_until="domcontentloaded")
    return new_p


def _capture_recetem_context(
    page: Page, context: BrowserContext, trigger_action
) -> Union[Page, FrameLocator]:
    """
    Karmed'den Reçetem'e geçişte yeni sekme (new tab/popup) VEYA sayfa içi iframe
    durumunu otomatik algılar ve ilgili hedef nesneyi (Page veya FrameLocator) döndürür.
    """
    logger.info("Reçetem sistemine geçiş tetikleniyor (Yeni sekme veya iframe bekleniyor)...")

    try:
        # 1. Senaryo: Yeni sekme / popup penceresi açılması
        with context.expect_page(timeout=8000) as new_page_info:
            trigger_action()

        recetem_page = new_page_info.value
        recetem_page.wait_for_load_state("domcontentloaded")
        logger.info(f"Reçetem yeni sekmede yakalandı: {recetem_page.url}")
        return recetem_page

    except PlaywrightTimeoutError:
        # 2. Senaryo: Yeni sekme açılmadıysa mevcut sayfada veya alt frame'lerde Reçetem iframe kontrolü
        logger.info("Yeni sekme açılmadı; mevcut sayfa içi iframe veya yönlendirme kontrol ediliyor...")
        for frame in page.frames:
            if "recetem" in frame.url.lower() or "enabiz" in frame.url.lower():
                logger.info(f"Reçetem alt frame olarak yakalandı: {frame.url}")
                return page

        iframe_loc = page.locator(Selectors.RECETEM_IFRAME)
        if iframe_loc.count() > 0:
            iframe_loc.first.wait_for(state="visible", timeout=15000)
            logger.info("Reçetem ekranı sayfa içi iframe olarak yakalandı.")
            return page.frame_locator(Selectors.RECETEM_IFRAME).first

        page.wait_for_load_state("domcontentloaded")
        logger.info("Reçetem ekranı mevcut sekme üzerinde yakalandı.")
        return page


def _add_icd_diagnosis(target: Union[Page, FrameLocator], icd_code: str) -> None:
    """Reçetem ekranında 'Ek Tanı' alanına belirtilen ICD-10 kodunu girer ve kaydeder."""
    logger.info(f"Ek tanı ekleniyor: {icd_code}")
    tani_input = (
        _find_visible_locator(target, Selectors.EK_TANI_INPUT, timeout=15000)
        if isinstance(target, Page)
        else target.locator(Selectors.EK_TANI_INPUT).first
    )
    expect(tani_input).to_be_visible(timeout=15000)
    expect(tani_input).to_be_enabled(timeout=10000)

    tani_input.click()
    tani_input.fill(icd_code)

    dropdown_selector = Selectors.EK_TANI_DROPDOWN_ITEM.format(code=icd_code)
    dropdown_item = target.locator(dropdown_selector).first
    try:
        dropdown_item.wait_for(state="visible", timeout=5000)
        dropdown_item.click()
    except PlaywrightTimeoutError:
        tani_input.press("Enter")

    ekle_btn = target.locator(Selectors.EK_TANI_EKLE_BTN).first
    if ekle_btn.count() > 0 and ekle_btn.is_visible():
        ekle_btn.click()

    expect(target.locator(f"text={icd_code}").first).to_be_visible(timeout=10000)
    _wait_until_idle(target)


def _extract_prescription_number(target: Union[Page, FrameLocator], timeout: int = 45000) -> str:
    """
    İmzalama sonrasında ekrana düşen Reçete Numarasını akıllı bekleme (explicit wait) ile yakalar.
    """
    logger.info("İmzalama sonrası Reçete Numarasının oluşması bekleniyor...")
    _wait_until_idle(target, timeout=timeout)

    recete_loc = (
        _find_visible_locator(target, Selectors.RECETE_NO_CONTAINER, timeout=timeout)
        if isinstance(target, Page)
        else target.locator(Selectors.RECETE_NO_CONTAINER).first
    )
    expect(recete_loc).to_be_visible(timeout=timeout)
    expect(recete_loc).not_to_be_empty(timeout=timeout)

    raw_text = recete_loc.inner_text().strip()
    logger.info(f"Okunan ham Reçete No alanı metni: '{raw_text}'")

    match = re.search(r"(?:Reçete\s*(?:No|Numarası)\s*[:\-]?\s*)?([A-Z0-9]{6,20})\b", raw_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return raw_text


def create_allergy_prescription(
    ornek_no: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Verilen Hasta Örnek Numarası ile Karmed RBYS (http://10.54.136.61:2015/Karmed/Default.aspx)
    üzerinden allerji reçetesi oluşturur, Sağlık Bakanlığı Reçetem sistemine aktarır,
    T78.4 ve K30 ek tanılarını girer, e-imza ile imzalar ve üretilen Reçete Numarasını döndürür.

    :param ornek_no: Hastanın örnek numarası (str)
    :param status_callback: Arayüz (GUI) için opsiyonel durum bildirim fonksiyonu
    :return: Üretilen nihai Reçete Numarası (str)
    """
    current_step = "Başlangıç"

    def notify(msg: str) -> None:
        nonlocal current_step
        current_step = msg
        logger.info(msg)
        if status_callback:
            status_callback(msg)

    reload_env()
    reload_selectors()

    if not ornek_no or not str(ornek_no).strip():
        raise ValueError("Geçerli bir 'ornek_no' (Hasta Örnek Numarası) girilmelidir.")

    ornek_no = str(ornek_no).strip()

    eimza_pin = os.getenv("EIMZA_PIN")
    if not eimza_pin:
        raise EnvironmentError(
            "E-İmza PIN kodu bulunamadı! Lütfen Ayarlar (.env) içinde 'EIMZA_PIN' değişkenini tanımlayın."
        )

    karmed_url = os.getenv("KARMED_URL", DEFAULT_KARMED_URL)
    doktor_adi = os.getenv("DOKTOR_ADI", "Dr. Ad Soyad")
    sablon_adi = os.getenv("SABLON_ADI", "allerjiiii")
    browser_channel = os.getenv("BROWSER_CHANNEL", "chrome").strip()
    cdp_endpoint = os.getenv("CDP_ENDPOINT", "").strip()
    headless = os.getenv("HEADLESS", "false").lower() == "true"

    with sync_playwright() as p:
        if cdp_endpoint:
            notify(f"Açık tarayıcı oturumuna bağlanılıyor ({cdp_endpoint})...")
            browser = p.chromium.connect_over_cdp(cdp_endpoint)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = _select_karmed_page(context, karmed_url)
            notify(f"Karmed sekmesi yakalandı: {page.url}")
        else:
            notify(f"Tarayıcı başlatılıyor ve '{karmed_url}' açılıyor...")
            browser = _launch_system_browser(p, headless=headless, preferred_channel=browser_channel)
            context = browser.new_context(viewport={"width": 1600, "height": 900})
            page = context.new_page()
            page.goto(karmed_url, wait_until="domcontentloaded")

        active_page_for_debug: Page = page

        try:
            # =========================================================================
            # ADIM 1: Karmed'de Arama Kriterini "Örnek No" Seç ve Hastayı Arat
            # =========================================================================
            notify(f"Adım 1/8: Örnek No '{ornek_no}' ile hasta aranıyor...")
            _wait_until_idle(page)

            criteria_el = _find_visible_locator(page, Selectors.SEARCH_CRITERIA_DROPDOWN, timeout=15000)
            tag_name = criteria_el.evaluate("el => el.tagName.toLowerCase()")
            if tag_name == "select":
                criteria_el.select_option(label=Selectors.SEARCH_CRITERIA_OPTION_TEXT)
            else:
                criteria_el.click()
                opt_loc = _find_visible_locator(
                    page,
                    f".x-combo-list-item:has-text('{Selectors.SEARCH_CRITERIA_OPTION_TEXT}'), "
                    f".x-boundlist-item:has-text('{Selectors.SEARCH_CRITERIA_OPTION_TEXT}'), "
                    f"li:has-text('{Selectors.SEARCH_CRITERIA_OPTION_TEXT}')",
                    timeout=8000,
                )
                opt_loc.click()

            search_input = _find_visible_locator(page, Selectors.SEARCH_INPUT, timeout=10000)
            search_input.click()
            search_input.fill(ornek_no)
            search_input.press("Enter")

            try:
                search_btn = _find_visible_locator(page, Selectors.SEARCH_BUTTON, timeout=3000)
                if search_btn.is_visible():
                    search_btn.click()
            except Exception:
                pass

            _wait_until_idle(page)

            # =========================================================================
            # ADIM 2: Hasta Satırına Sağ Tıkla (Context Click) -> "Reçete Yaz"
            # =========================================================================
            notify("Adım 2/8: Hasta kaydına sağ tıklanıyor -> 'Reçete Yaz'...")
            row_selector = Selectors.PATIENT_ROW.format(ornek_no=ornek_no)
            patient_row = _find_visible_locator(page, row_selector, timeout=15000)
            patient_row.click(button="right")

            recete_yaz_opt = _find_visible_locator(page, Selectors.CONTEXT_MENU_RECETE_YAZ, timeout=10000)
            recete_yaz_opt.click()
            _wait_until_idle(page)

            # =========================================================================
            # ADIM 3: Reçete Formunda Sol Üstteki "Yeni (F2)" Butonuna Tıkla
            # =========================================================================
            notify("Adım 3/8: 'Yeni (F2)' butonuna tıklanıyor...")
            yeni_btn = _find_visible_locator(page, Selectors.BTN_YENI_F2, timeout=15000)
            expect(yeni_btn).to_be_enabled()
            yeni_btn.click()
            _wait_until_idle(page)

            # =========================================================================
            # ADIM 4: Doktor Seçimi ve "Şablonlar"dan Allerji Şablonunun Aktarılması
            # =========================================================================
            notify(f"Adım 4/8: Doktor ('{doktor_adi}') ve Şablon ('{sablon_adi}') seçiliyor...")
            doktor_el = _find_visible_locator(page, Selectors.DOKTOR_DROPDOWN, timeout=10000)

            if doktor_el.evaluate("el => el.tagName.toLowerCase()") == "select":
                doktor_el.select_option(label=doktor_adi)
            else:
                doktor_el.click()
                doktor_opt = _find_visible_locator(page, f"text='{doktor_adi}'", timeout=8000)
                doktor_opt.click()

            sablon_menu = _find_visible_locator(page, Selectors.SABLONLAR_MENU, timeout=10000)
            sablon_menu.click()

            sablon_item = _find_visible_locator(page, f"text='{sablon_adi}'", timeout=10000)
            sablon_item.click()

            _find_visible_locator(page, Selectors.ILAC_GRID_ROW, timeout=15000)
            _wait_until_idle(page)

            # =========================================================================
            # ADIM 5 & 6: "Reçetem" -> "Reçetem Sistemi Reçete Yaz(...)" ve Sekme Yakalama
            # =========================================================================
            notify("Adım 5/8: Reçetem portalına aktarılıyor ve yeni sekme yakalanıyor...")
            recetem_menu = _find_visible_locator(page, Selectors.RECETEM_TOP_MENU, timeout=10000)
            recetem_menu.click()

            send_option = _find_visible_locator(page, Selectors.RECETEM_SEND_OPTION, timeout=10000)

            recetem_ctx = _capture_recetem_context(
                page=page,
                context=context,
                trigger_action=lambda: send_option.click(),
            )
            if isinstance(recetem_ctx, Page):
                active_page_for_debug = recetem_ctx
            _wait_until_idle(recetem_ctx)

            # =========================================================================
            # ADIM 7: Reçetem Ekranında Ek Tanı Alanına T78.4 ve K30 Girilmesi
            # =========================================================================
            notify("Adım 6/8: Reçetem ekranında T78.4 ve K30 ICD tanıları giriliyor...")
            for icd_code in ["T78.4", "K30"]:
                _add_icd_diagnosis(recetem_ctx, icd_code)

            # =========================================================================
            # ADIM 8: E-İMZA BİLGİLERİ Panelinde PIN Girilmesi ve İmzalanması
            # =========================================================================
            notify("Adım 7/8: E-İmza PIN kodu giriliyor ve imzalanıyor...")
            pin_input = (
                _find_visible_locator(recetem_ctx, Selectors.PIN_INPUT, timeout=15000)
                if isinstance(recetem_ctx, Page)
                else recetem_ctx.locator(Selectors.PIN_INPUT).first
            )
            expect(pin_input).to_be_visible(timeout=15000)
            expect(pin_input).to_be_enabled()
            pin_input.fill(eimza_pin)

            imzala_btn = (
                _find_visible_locator(recetem_ctx, Selectors.IMZALA_BTN, timeout=10000)
                if isinstance(recetem_ctx, Page)
                else recetem_ctx.locator(Selectors.IMZALA_BTN).first
            )
            expect(imzala_btn).to_be_enabled(timeout=10000)
            imzala_btn.click()

            # =========================================================================
            # ADIM 9 & 10: Reçete Numarasının Ekrana Düşmesini Bekle ve Döndür
            # =========================================================================
            notify("Adım 8/8: E-İmza onayı ve Reçete Numarası bekleniyor...")
            recete_no = _extract_prescription_number(recetem_ctx, timeout=45000)
            notify(f"Tamamlandı! Üretilen Reçete No: {recete_no}")
            return recete_no

        except Exception as err:
            report_file = dump_page_diagnostics(
                active_page_for_debug, step_info=current_step, error_msg=str(err)
            )
            notify(f"⚠️ Hata Analiz Raporu oluşturuldu: {report_file}")
            raise
        finally:
            if not cdp_endpoint:
                browser.close()


if __name__ == "__main__":
    ornek_numarasi = "20261105001"
    recete_numarasi = create_allergy_prescription(ornek_numarasi)
    print(f"Reçete No: {recete_numarasi}")
