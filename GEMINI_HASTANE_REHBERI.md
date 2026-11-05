# 🏥 Hastanede Kurulum, Ayar ve Gemini ile Canlı Hata Ayıklama (Debugging) Rehberi

## 1. Karmed Adresiniz (`http://10.54.136.61:2015/Karmed/Default.aspx`) Tanımlandı!
- `.env`, `recete_otomasyon.py` ve `gui_app.py` dosyalarına hastanenizin gerçek Karmed adresi olan **`http://10.54.136.61:2015/Karmed/Default.aspx`** varsayılan olarak işlendi.
- Ayrıca adresin **`Default.aspx` (ASP.NET / Ext.NET)** yapısında olduğu görüldüğü için koda **Çoklu Iframe Tarama (`_find_visible_locator`)** özelliği eklendi. Karmed içinde açılan alt modül pencereleri (Poliklinik, Hasta Arama, Reçete Formu) ayrı bir `iframe` içinde açılsa bile script tüm alt `iframe`'leri otomatik tarayıp bulacaktır.

---

## 2. Yarın Hastaneye Gittiğinizde Yapacağınız Adımlar

> **ÖNEMLİ:** Evden çıkmadan önce `build_exe.bat` dosyasına bir kez çift tıklayıp çalıştırın ki `dist\ReceteOtomasyon.exe` son güncellemelerle yeniden derlensin.

Hastanede:
1. **`ReceteOtomasyon.exe`**'yi açın.
2. Sağ üstteki **`⚙ Ayarlar`** butonuna tıklayın:
   - **Karmed Lokal IP / URL:** `http://10.54.136.61:2015/Karmed/Default.aspx` (Hazır gelecektir)
   - **E-İmza PIN Kodu:** E-imza şifrenizi yazın.
   - **Doktor Adı:** Karmed'de doktor listesinde görünen tam adınızı yazın.
   - **Şablon Adı:** Allerji şablonunuzun Karmed'deki tam adını yazın.
   - **Açık Chrome (CDP) Adresi:** `http://localhost:9222` (Hazır gelecektir) -> **💾 Kaydet**'e basın.
3. Üst çubuktaki **`🌐 Karmed Chrome`** butonuna tıklayın.
   - Açılan Chrome penceresinde `http://10.54.136.61:2015/Karmed/Default.aspx` otomatik açılacaktır.
   - Karmed kullanıcı adı ve şifrenizle giriş yapın ve **Hasta Arama** ekranını açın.
4. Uygulamaya **Hasta Örnek No** girip **`▶ Reçete Oluştur`** butonuna basın.

---

## 3. Hastanede Bir Buton/Kutu Bulunamazsa Nasıl Değiştireceksiniz?

1. Uygulamanın altındaki **`🐞 Gemini İçin Debug Raporunu Kopyala`** butonuna tıklayın.
2. Tarayıcıdan **Gemini**'yi açın, aşağıdaki **Bölüm 4'teki Başlangıç Promptunu** ve ardından kopyaladığınız raporu (`Ctrl+V`) yapıştırın.
3. Gemini'nin söylediği seçiciyi uygulamadaki **`🧩 Seçicileri Düzenle (selectors.json)`** butonuna tıklayarak Not Defteri'nde ilgili satıra yapıştırıp `Ctrl+S` ile kaydedin ve tekrar **`▶ Reçete Oluştur`**'a basın! **(`.exe` dosyasını yeniden derlemenize gerek yoktur!)**

---

## 4. 🤖 Yarın Hastanede Gemini'ye Yapıştıracağınız Hazır Bağlam (Context) Promptu

Yarın hastanede Gemini'yi açtığınızda **ilk mesaj olarak aşağıdaki kutunun içindeki metni kopyalayıp Gemini'ye gönderin**:

```text
Merhaba Gemini, dün Antigravity üzerinde Python Playwright ve Tkinter kullanarak Karmed RBYS (http://10.54.136.61:2015/Karmed/Default.aspx - ASP.NET / Ext.NET tabanlı) ve Sağlık Bakanlığı Reçetem sistemi için otomatik allerji reçetesi yazan bir RPA uygulaması geliştirdik ve PyInstaller ile ReceteOtomasyon.exe haline getirdik. Şu an hastanedeyim ve lokal Karmed sistemi üzerinde canlı test ve debugging yapıyorum.

Projemizin çalışma mantığı ve mimarisi şöyledir:
1. Uygulama Chrome'a CDP (http://localhost:9222) üzerinden bağlanır ve `10.54.136.61:2015/Karmed/Default.aspx` sekmesini yakalar.
2. Karmed Default.aspx alt modülleri iframe içinde açabildiği için `_find_visible_locator(page, selector)` fonksiyonumuz verilen seçiciyi hem ana sayfada hem de tüm `page.frames` (alt iframe'ler) içinde otomatik arar.
3. İş akışı 8 adımdan oluşur:
   - Adım 1: Karmed'de arama kriteri "Örnek No" seçilir (SEARCH_CRITERIA_DROPDOWN / SEARCH_CRITERIA_OPTION_TEXT), hasta örnek numarası girilir (SEARCH_INPUT) ve aratılır (SEARCH_BUTTON).
   - Adım 2: Listelenen hasta satırına (PATIENT_ROW) sağ tıklanır ve "Reçete Yaz" (CONTEXT_MENU_RECETE_YAZ) tıklanır.
   - Adım 3: Açılan reçete formunda sol üstteki "Yeni (F2)" (BTN_YENI_F2) butonuna tıklanır.
   - Adım 4: Doktor seçilir (DOKTOR_DROPDOWN), sağdaki "Şablonlar" (SABLONLAR_MENU) menüsünden allerji şablonu seçilir ve ilaçların listeye (ILAC_GRID_ROW) düşmesi beklenir.
   - Adım 5 & 6: Üstteki "Reçetem" (RECETEM_TOP_MENU) -> "Reçetem Sistemi Reçete Yaz(Seçilen Reçete Bilgileriyle)" (RECETEM_SEND_OPTION) tıklanır. Açılan yeni sekme (context.expect_page) VEYA sayfa içi iframe (RECETEM_IFRAME) otomatik yakalanır.
   - Adım 7: Reçetem ekranında Ek Tanı alanına (EK_TANI_INPUT) sırasıyla "T78.4" ve "K30" ICD tanı kodları girilir (EK_TANI_DROPDOWN_ITEM / EK_TANI_EKLE_BTN).
   - Adım 8: Sağdaki "E-İMZA BİLGİLERİ" (EIMZA_PANEL) altında PIN girilir (PIN_INPUT) ve "İmzala" (IMZALA_BTN) butonuna basılır.
   - Adım 9: Ekrana düşen nihai "Reçete No" (RECETE_NO_CONTAINER) okunur ve döndürülür.

4. ÖNEMLİ: Hastanedeki bilgisayarda .exe'yi yeniden derlememek için tüm Playwright seçicileri .exe'nin yanındaki `selectors.json` dosyasından dinamik olarak okunmaktadır. Ayrıca uygulama hata aldığında ana sayfadaki ve tüm alt iframe'lerdeki (`[FRAME 0]`, `[FRAME 1]`...) görünür <input>, <select>, <button>, <a>, <iframe> elementlerini otomatik olarak `debug_rapor.txt` olarak çıkartmaktadır.

Mevcut `selectors.json` dosyamızın içeriği şudur:
{
  "SEARCH_CRITERIA_DROPDOWN": "select#aramaKriteri, input[name*='Kriter'], input[id*='cmbArama'], input[id*='AramaKriter'], [aria-label='Arama Kriteri']",
  "SEARCH_CRITERIA_OPTION_TEXT": "Örnek No",
  "SEARCH_INPUT": "input#ornekNoInput, input[id*='txtOrnek'], input[id*='txtArama'], input[placeholder*='Örnek'], input[name*='OrnekNo'], input[name='aramaMetni']",
  "SEARCH_BUTTON": "button:has-text('Ara'), .x-btn:has-text('Ara'), .x-btn-text:has-text('Ara'), button#btnAra, input[value='Ara']",
  "PATIENT_ROW": "div.x-grid3-row:has-text('{ornek_no}'), tr.x-grid-row:has-text('{ornek_no}'), table tbody tr:has-text('{ornek_no}')",
  "CONTEXT_MENU_RECETE_YAZ": ".x-menu-item:has-text('Reçete Yaz'), a.x-menu-item-link:has-text('Reçete Yaz'), text='Reçete Yaz'",
  "BTN_YENI_F2": "button:has-text('Yeni (F2)'), .x-btn:has-text('Yeni (F2)'), .x-btn-text:has-text('Yeni (F2)'), button:has-text('Yeni')",
  "DOKTOR_DROPDOWN": "select#doktorId, input[id*='cmbDoktor'], input[id*='Doktor'], input[name*='doktor'], [placeholder*='Doktor']",
  "SABLONLAR_MENU": "button:has-text('Şablonlar'), .x-btn:has-text('Şablonlar'), .x-btn-text:has-text('Şablonlar'), text='Şablonlar'",
  "ILAC_GRID_ROW": ".ilac-listesi tr, .x-grid-item, .x-grid3-row, .x-grid-row",
  "RECETEM_TOP_MENU": "button:has-text('Reçetem'), .x-btn:has-text('Reçetem'), .x-btn-text:has-text('Reçetem')",
  "RECETEM_SEND_OPTION": ".x-menu-item:has-text('Reçetem Sistemi Reçete Yaz'), text='Reçetem Sistemi Reçete Yaz(Seçilen Reçete Bilgileriyle)'",
  "RECETEM_IFRAME": "iframe[src*='recetem'], iframe[src*='enabiz'], iframe#recetemFrame",
  "EK_TANI_INPUT": "input[placeholder*='Tanı'], input#ekTaniInput, input[name*='tani'], .tani-arama-input",
  "EK_TANI_DROPDOWN_ITEM": ".ui-autocomplete li:has-text('{code}'), .dropdown-item:has-text('{code}'), tr:has-text('{code}'), .x-combo-list-item:has-text('{code}'), .x-boundlist-item:has-text('{code}')",
  "EK_TANI_EKLE_BTN": "button:has-text('Ekle'), button#btnTaniEkle, button:has-text('Kaydet')",
  "EIMZA_PANEL": "text='E-İMZA BİLGİLERİ'",
  "PIN_INPUT": "input[type='password'], input[placeholder*='Pin'], input#pinKodu, input[name*='pin']",
  "IMZALA_BTN": "button:has-text('İmzala'), input[type='button'][value='İmzala'], #btnImzala",
  "LOADING_MASK": ".x-mask-loading, .ext-el-mask-msg, .loading-spinner, .blockUI, .swal2-loading",
  "RECETE_NO_CONTAINER": "#receteNo, [data-testid='recete-no'], td:right-of(:text('Reçete No')), span:right-of(:text('Reçete Numarası')), .recete-no-deger, .alert-success"
}

Şimdi sana hastanede aldığım `debug_rapor.txt` çıktısını (veya ekran görüntüsünü) göndereceğim. Lütfen rapordaki HTML elementlerine bakarak `selectors.json` içinde hangi anahtarı neyle değiştirmem gerektiğini doğrudan söyle. Hazır mısın?
```
