import ctypes
import os
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from recete_otomasyon import (
    create_allergy_prescription,
    get_base_dir,
    get_selectors_path,
    reload_env,
    reload_selectors,
)


THEMES = {
    "dark": {
        "bg": "#0f172a",
        "header_bg": "#1e293b",
        "header_fg": "#f8fafc",
        "card_bg": "#1e293b",
        "card_fg": "#94a3b8",
        "text_fg": "#e2e8f0",
        "input_bg": "#0f172a",
        "input_fg": "#f8fafc",
        "input_border": "#334155",
        "readonly_bg": "#090d16",
        "readonly_fg": "#38bdf8",
        "copy_bg": "#334155",
        "copy_fg": "#f1f5f9",
        "copy_active": "#475569",
        "log_bg": "#090d16",
        "log_fg": "#cbd5e1",
        "theme_btn_bg": "#334155",
        "theme_btn_fg": "#f8fafc",
        "theme_btn_text": "☀️ Açık Mod",
    },
    "light": {
        "bg": "#f4f6f9",
        "header_bg": "#1e3a8a",
        "header_fg": "#ffffff",
        "card_bg": "#ffffff",
        "card_fg": "#1e293b",
        "text_fg": "#334155",
        "input_bg": "#ffffff",
        "input_fg": "#0f172a",
        "input_border": "#cbd5e1",
        "readonly_bg": "#f8fafc",
        "readonly_fg": "#0f172a",
        "copy_bg": "#e2e8f0",
        "copy_fg": "#1e293b",
        "copy_active": "#cbd5e1",
        "log_bg": "#0f172a",
        "log_fg": "#e2e8f0",
        "theme_btn_bg": "#1e40af",
        "theme_btn_fg": "#ffffff",
        "theme_btn_text": "🌙 Koyu Mod",
    },
}


class ReceteApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Karmed & Reçetem - Otomatik Allerji Reçetesi")
        self.root.geometry("640x510")
        self.root.resizable(False, False)

        reload_env()
        reload_selectors()
        default_dark = os.getenv("DARK_MODE", "true").lower() != "false"
        self.current_theme = "dark" if default_dark else "light"

        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        # Üst Başlık Çubuğu
        self.header = tk.Frame(self.root, height=56)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.lbl_title = tk.Label(
            self.header,
            text="Karmed & Reçetem Otomasyonu",
            font=("Segoe UI", 12, "bold"),
        )
        self.lbl_title.pack(side="left", padx=14)

        self.btn_settings = tk.Button(
            self.header,
            text="⚙ Ayarlar",
            font=("Segoe UI", 9, "bold"),
            bg="#3b82f6",
            fg="white",
            activebackground="#2563eb",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._open_settings_dialog,
        )
        self.btn_settings.pack(side="right", padx=(4, 12))

        self.btn_chrome = tk.Button(
            self.header,
            text="🌐 Karmed Chrome",
            font=("Segoe UI", 9),
            bg="#0f766e",
            fg="white",
            activebackground="#115e59",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._launch_debug_chrome,
        )
        self.btn_chrome.pack(side="right", padx=4)

        self.btn_theme = tk.Button(
            self.header,
            text="☀️ Açık Mod",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._toggle_theme,
        )
        self.btn_theme.pack(side="right", padx=4)

        # Ana İçerik Alanı
        self.body = tk.Frame(self.root, padx=20, pady=14)
        self.body.pack(fill="both", expand=True)

        # 1. Hasta Örnek No Giriş Kartı
        self.input_card = tk.LabelFrame(
            self.body,
            text=" 1. Hasta Bilgisi ",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=12,
            bd=1,
            relief="solid",
        )
        self.input_card.pack(fill="x", pady=(0, 12))

        self.lbl_ornek = tk.Label(
            self.input_card,
            text="Hasta Örnek No:",
            font=("Segoe UI", 10),
        )
        self.lbl_ornek.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.ornek_no_var = tk.StringVar()
        self.entry_ornek = tk.Entry(
            self.input_card,
            textvariable=self.ornek_no_var,
            font=("Segoe UI", 12),
            width=22,
            relief="solid",
            bd=1,
        )
        self.entry_ornek.grid(row=0, column=1, sticky="we", padx=(0, 10), ipady=4)
        self.entry_ornek.bind("<Return>", lambda _: self._start_process())
        self.entry_ornek.focus_set()

        self.btn_run = tk.Button(
            self.input_card,
            text="▶ Reçete Oluştur",
            font=("Segoe UI", 10, "bold"),
            bg="#16a34a",
            fg="white",
            activebackground="#15803d",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._start_process,
        )
        self.btn_run.grid(row=0, column=2)
        self.input_card.columnconfigure(1, weight=1)

        # 2. Sonuç (Reçete Numarası) Kartı
        self.result_card = tk.LabelFrame(
            self.body,
            text=" 2. Üretilen Reçete Numarası ",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=12,
            bd=1,
            relief="solid",
        )
        self.result_card.pack(fill="x", pady=(0, 12))

        self.recete_no_var = tk.StringVar(value="—")
        self.lbl_recete_no = tk.Entry(
            self.result_card,
            textvariable=self.recete_no_var,
            font=("Consolas", 15, "bold"),
            state="readonly",
            justify="center",
            relief="solid",
            bd=1,
        )
        self.lbl_recete_no.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=4)

        self.btn_copy = tk.Button(
            self.result_card,
            text="📋 Kopyala",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._copy_recete_no,
        )
        self.btn_copy.pack(side="right")

        # 3. Canlı İşlem Günlüğü (Log) ve Debug Araçları
        self.log_card = tk.LabelFrame(
            self.body,
            text=" İşlem Durumu ve Hata Ayıklama (Debug) ",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=8,
            bd=1,
            relief="solid",
        )
        self.log_card.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            self.log_card,
            height=7,
            font=("Consolas", 9),
            state="disabled",
            wrap="word",
            relief="flat",
        )
        self.log_text.pack(fill="both", expand=True, pady=(0, 6))

        debug_bar = tk.Frame(self.log_card, bg=THEMES[self.current_theme]["card_bg"])
        debug_bar.pack(fill="x")
        self.debug_bar = debug_bar

        self.btn_copy_debug = tk.Button(
            debug_bar,
            text="🐞 Gemini İçin Debug Raporunu Kopyala",
            font=("Segoe UI", 8, "bold"),
            bg="#d97706",
            fg="white",
            activebackground="#b45309",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._copy_debug_report,
        )
        self.btn_copy_debug.pack(side="left")

        self.btn_open_selectors = tk.Button(
            debug_bar,
            text="🧩 Seçicileri Düzenle (selectors.json)",
            font=("Segoe UI", 8, "bold"),
            bg="#4f46e5",
            fg="white",
            activebackground="#4338ca",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._open_selectors_file,
        )
        self.btn_open_selectors.pack(side="right")

        self._append_log("Hazır. Hasta Örnek Numarasını girip 'Reçete Oluştur' butonuna basın.")

    def _set_window_titlebar_dark(self, win: tk.Misc, is_dark: bool) -> None:
        """Windows 10/11 pencere üst çubuğunu (title bar) koyu veya açık moda geçirir."""
        try:
            win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            value = ctypes.c_int(1 if is_dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:
            pass

    def _toggle_theme(self) -> None:
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme()

    def _apply_theme(self) -> None:
        t = THEMES[self.current_theme]
        self._set_window_titlebar_dark(self.root, self.current_theme == "dark")

        self.root.configure(bg=t["bg"])
        self.header.configure(bg=t["header_bg"])
        self.lbl_title.configure(bg=t["header_bg"], fg=t["header_fg"])
        self.btn_theme.configure(
            bg=t["theme_btn_bg"],
            fg=t["theme_btn_fg"],
            activebackground=t["copy_active"],
            activeforeground=t["theme_btn_fg"],
            text=t["theme_btn_text"],
        )

        self.body.configure(bg=t["bg"])

        for card in (self.input_card, self.result_card, self.log_card):
            card.configure(bg=t["card_bg"], fg=t["card_fg"])

        self.debug_bar.configure(bg=t["card_bg"])
        self.lbl_ornek.configure(bg=t["card_bg"], fg=t["text_fg"])
        self.entry_ornek.configure(
            bg=t["input_bg"],
            fg=t["input_fg"],
            insertbackground=t["input_fg"],
            highlightbackground=t["input_border"],
            highlightcolor="#3b82f6",
            highlightthickness=1,
            bd=0,
        )

        self.lbl_recete_no.configure(
            readonlybackground=t["readonly_bg"],
            fg=t["readonly_fg"],
            highlightbackground=t["input_border"],
            highlightthickness=1,
            bd=0,
        )

        self.btn_copy.configure(
            bg=t["copy_bg"],
            fg=t["copy_fg"],
            activebackground=t["copy_active"],
            activeforeground=t["copy_fg"],
        )

        self.log_text.configure(bg=t["log_bg"], fg=t["log_fg"])

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _copy_recete_no(self) -> None:
        val = self.recete_no_var.get().strip()
        if val and val != "—":
            self.root.clipboard_clear()
            self.root.clipboard_append(val)
            self._append_log(f"Reçete No panoya kopyalandı: {val}")

    def _copy_debug_report(self) -> None:
        """Oluşan debug_rapor.txt ve işlem günlüğünü Gemini'ye yapıştırmak üzere panoya kopyalar."""
        report_path = os.path.join(get_base_dir(), "debug_rapor.txt")
        log_content = self.log_text.get("1.0", "end").strip()

        combined = ["=== UYGULAMA LOG KAYITLARI ===", log_content]
        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    combined.append("\n" + f.read())
            except Exception:
                pass

        full_text = "\n".join(combined)
        self.root.clipboard_clear()
        self.root.clipboard_append(full_text)
        self._append_log("📋 Debug raporu panoya kopyalandı! Doğrudan Gemini'ye yapıştırabilirsiniz (Ctrl+V).")
        messagebox.showinfo(
            "Rapor Kopyalandı",
            "Hata raporu ve sayfadaki element listesi panoya kopyalandı.\n\n"
            "Şimdi Gemini ekranına gidip Ctrl+V ile yapıştırabilirsiniz.",
        )

    def _open_selectors_file(self) -> None:
        """selectors.json dosyasını Not Defteri ile açar."""
        reload_selectors()
        path = get_selectors_path()
        try:
            os.startfile(path)
            self._append_log("selectors.json açıldı. Değişiklik yapıp kaydettiğinizde anında geçerli olur.")
        except Exception as err:
            messagebox.showerror("Hata", f"selectors.json açılamadı:\n{err}")

    def _launch_debug_chrome(self) -> None:
        """Bilgisayardaki Chrome'u 9222 portundan Karmed için açar."""
        reload_env()
        karmed_url = os.getenv("KARMED_URL", "http://10.54.136.61:2015/Karmed/Default.aspx")
        profile_dir = r"C:\chrome_karmed_profil"

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), "chrome.exe")

        try:
            subprocess.Popen(
                [
                    chrome_exe,
                    "--remote-debugging-port=9222",
                    f"--user-data-dir={profile_dir}",
                    karmed_url,
                ]
            )
            self._append_log(
                "Chrome Debug modunda (Port 9222) başlatıldı. "
                "Açılan pencerede Karmed'e giriş yapıp Ayarlar'da CDP_ENDPOINT=http://localhost:9222 yapabilirsiniz."
            )
        except Exception as err:
            messagebox.showerror("Hata", f"Chrome başlatılamadı:\n{err}")

    def _start_process(self) -> None:
        ornek_no = self.ornek_no_var.get().strip()
        if not ornek_no:
            messagebox.showwarning("Uyarı", "Lütfen Hasta Örnek Numarasını girin.")
            return

        self.btn_run.configure(state="disabled", text="⏳ İşleniyor...", bg="#64748b")
        self.recete_no_var.set("Bekleniyor...")
        self._append_log(f"--- Yeni İşlem Başlatıldı (Örnek No: {ornek_no}) ---")

        thread = threading.Thread(target=self._worker, args=(ornek_no,), daemon=True)
        thread.start()

    def _worker(self, ornek_no: str) -> None:
        try:
            recete_no = create_allergy_prescription(
                ornek_no=ornek_no,
                status_callback=lambda msg: self.root.after(0, self._append_log, msg),
            )
            self.root.after(0, self._on_success, recete_no)
        except Exception as err:
            self.root.after(0, self._on_error, str(err))

    def _on_success(self, recete_no: str) -> None:
        self.recete_no_var.set(recete_no)
        self.root.clipboard_clear()
        self.root.clipboard_append(recete_no)
        self._append_log(f"✅ BAŞARILI! Reçete No ({recete_no}) otomatik olarak panoya kopyalandı.")
        self.btn_run.configure(state="normal", text="▶ Reçete Oluştur", bg="#16a34a")
        self.entry_ornek.selection_range(0, "end")
        self.entry_ornek.focus_set()

    def _on_error(self, error_msg: str) -> None:
        self.recete_no_var.set("HATA")
        self._append_log(f"❌ HATA: {error_msg}")
        self._append_log("💡 '🐞 Gemini İçin Debug Raporunu Kopyala' butonuna basıp raporu Gemini'ye yapıştırabilirsiniz.")
        self.btn_run.configure(state="normal", text="▶ Reçete Oluştur", bg="#16a34a")
        messagebox.showerror(
            "İşlem Hatası",
            f"Reçete oluşturulurken hata meydana geldi:\n\n{error_msg}\n\n"
            "Ana ekrandaki '🐞 Gemini İçin Debug Raporunu Kopyala' butonuna basarak "
            "detaylı sayfa analizini Gemini'ye gönderebilirsiniz.",
        )

    def _open_settings_dialog(self) -> None:
        """Kullanıcının .env dosyasını not defteri açmadan düzenleyebileceği ayar penceresi."""
        reload_env()
        t = THEMES[self.current_theme]

        win = tk.Toplevel(self.root)
        win.title("Ayarlar (.env Yapılandırması)")
        win.geometry("480x360")
        win.resizable(False, False)
        win.configure(bg=t["card_bg"], padx=18, pady=16)
        win.transient(self.root)
        win.grab_set()
        self._set_window_titlebar_dark(win, self.current_theme == "dark")

        fields = [
            ("Karmed Lokal IP / URL:", "KARMED_URL", os.getenv("KARMED_URL", "http://10.54.136.61:2015/Karmed/Default.aspx"), False),
            ("E-İmza PIN Kodu:", "EIMZA_PIN", os.getenv("EIMZA_PIN", ""), True),
            ("Doktor Adı:", "DOKTOR_ADI", os.getenv("DOKTOR_ADI", "Dr. Ad Soyad"), False),
            ("Şablon Adı:", "SABLON_ADI", os.getenv("SABLON_ADI", "allerjiiii"), False),
            ("Tarayıcı (chrome / msedge):", "BROWSER_CHANNEL", os.getenv("BROWSER_CHANNEL", "chrome"), False),
            ("Açık Chrome (CDP) Adresi:", "CDP_ENDPOINT", os.getenv("CDP_ENDPOINT", "http://localhost:9222"), False),
        ]

        entries = {}
        for idx, (label_text, key, default_val, is_secret) in enumerate(fields):
            tk.Label(
                win,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                bg=t["card_bg"],
                fg=t["text_fg"],
            ).grid(row=idx, column=0, sticky="w", pady=6, padx=(0, 10))

            var = tk.StringVar(value=default_val)
            ent = tk.Entry(
                win,
                textvariable=var,
                font=("Segoe UI", 10),
                show="*" if is_secret else "",
                bg=t["input_bg"],
                fg=t["input_fg"],
                insertbackground=t["input_fg"],
                highlightbackground=t["input_border"],
                highlightcolor="#3b82f6",
                highlightthickness=1,
                bd=0,
            )
            ent.grid(row=idx, column=1, sticky="we", pady=6, ipady=3)
            entries[key] = var

        win.columnconfigure(1, weight=1)

        def save_settings() -> None:
            env_path = os.path.join(get_base_dir(), ".env")
            lines = [
                "# Karmed RBYS & E-İmza Yapılandırması\n",
                f"KARMED_URL={entries['KARMED_URL'].get().strip()}\n",
                f"EIMZA_PIN={entries['EIMZA_PIN'].get().strip()}\n",
                f"DOKTOR_ADI={entries['DOKTOR_ADI'].get().strip()}\n",
                f"SABLON_ADI={entries['SABLON_ADI'].get().strip()}\n",
                f"BROWSER_CHANNEL={entries['BROWSER_CHANNEL'].get().strip() or 'chrome'}\n",
                f"CDP_ENDPOINT={entries['CDP_ENDPOINT'].get().strip()}\n",
                f"DARK_MODE={'true' if self.current_theme == 'dark' else 'false'}\n",
                "HEADLESS=false\n",
            ]
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            reload_env()
            self._append_log("Ayarlar (.env) kaydedildi ve güncellendi.")
            win.destroy()

        btn_save = tk.Button(
            win,
            text="💾 Kaydet",
            font=("Segoe UI", 10, "bold"),
            bg="#3b82f6",
            fg="white",
            activebackground="#2563eb",
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=save_settings,
        )
        btn_save.grid(row=len(fields), column=0, columnspan=2, pady=(16, 0))


if __name__ == "__main__":
    root = tk.Tk()
    app = ReceteApp(root)
    root.mainloop()
