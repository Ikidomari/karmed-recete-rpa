import os
import sys
import json
import zipfile
import threading
import subprocess
import tkinter as tk
from tkinter import ttk
import requests


# =====================================================================
# YAPILANDIRMA AYARLARI
# =====================================================================
# Sunucunuzdaki version.json adresi (.env içinde UPDATE_URL varsa oradan da okur)
DEFAULT_VERSION_URL = "http://sunucum/version.json"

# Güncelleme sonrası başlatılacak ana RPA çalıştırılabilir dosyası
# (Projenizde ReceteOtomasyon.exe veya main.exe hangisi mevcutsa onu çalıştırır)
MAIN_EXE_CANDIDATES = ["ReceteOtomasyon.exe", "main.exe"]

LOCAL_VERSION_FILE = "local_version.txt"
TEMP_ZIP_FILE = "app_update_temp.zip"
REQUEST_TIMEOUT = 6  # Saniye


def get_base_dir() -> str:
    """Updater .exe veya .py olarak çalıştığında bulunduğu klasörü döndürür."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def parse_version(v_str: str) -> tuple:
    """'1.0.5' gibi sürüm metinlerini karşılaştırılabilir (1, 0, 5) demetine çevirir."""
    cleaned = "".join(ch if (ch.isdigit() or ch == ".") else "" for ch in v_str.strip())
    parts = [int(p) for p in cleaned.split(".") if p.isdigit()]
    return tuple(parts) if parts else (0, 0, 0)


class AutoUpdaterGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.base_dir = get_base_dir()
        self._drag_x = 0
        self._drag_y = 0

        self._setup_window()
        self._build_widgets()

        # Pencere çizildikten hemen sonra arka plan thread'ini başlat
        self.root.after(150, self._start_update_thread)

    def _setup_window(self) -> None:
        """Ekranın tam ortasında, çerçevesiz (frameless) ve modern koyu temalı pencere."""
        width, height = 420, 155
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = (screen_w - width) // 2
        pos_y = (screen_h - height) // 2

        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.root.overrideredirect(True)  # Çerçevesiz modern splash görünümü
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0f172a")

        # Fare ile sürükleyebilme desteği
        self.root.bind("<ButtonPress-1>", self._on_drag_start)
        self.root.bind("<B1-Motion>", self._on_drag_motion)

    def _on_drag_start(self, event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag_motion(self, event) -> None:
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _build_widgets(self) -> None:
        # Dış çerçeve (İnce kenarlık efekti için)
        container = tk.Frame(
            self.root,
            bg="#1e293b",
            highlightbackground="#334155",
            highlightthickness=1,
            padx=24,
            pady=20,
        )
        container.pack(fill="both", expand=True)

        # Başlık ve Sürüm Etiketi
        top_row = tk.Frame(container, bg="#1e293b")
        top_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            top_row,
            text="⚡ Karmed & Reçetem RPA",
            font=("Segoe UI", 11, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        ).pack(side="left")

        local_ver = self._read_local_version()
        self.lbl_version = tk.Label(
            top_row,
            text=f"v{local_ver}",
            font=("Consolas", 9, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
            padx=6,
            pady=2,
        )
        self.lbl_version.pack(side="right")

        # Durum Metni (Label)
        self.status_var = tk.StringVar(value="Güncelleme kontrol ediliyor...")
        self.lbl_status = tk.Label(
            container,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg="#cbd5e1",
            bg="#1e293b",
            anchor="w",
        )
        self.lbl_status.pack(fill="x", pady=(0, 10))

        # İlerleme Çubuğu (Progress Bar) Stili
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Updater.Horizontal.TProgressbar",
            troughcolor="#0f172a",
            bordercolor="#0f172a",
            background="#3b82f6",
            lightcolor="#60a5fa",
            darkcolor="#2563eb",
            thickness=10,
        )

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            container,
            variable=self.progress_var,
            maximum=100.0,
            mode="determinate",
            style="Updater.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill="x", pady=(0, 6))

        # Yüzde Etiketi
        self.percent_var = tk.StringVar(value="")
        self.lbl_percent = tk.Label(
            container,
            textvariable=self.percent_var,
            font=("Consolas", 8),
            fg="#94a3b8",
            bg="#1e293b",
            anchor="e",
        )
        self.lbl_percent.pack(fill="x")

    # =====================================================================
    # THREAD-SAFE GUI GÜNCELLEME YARDIMCILARI
    # =====================================================================
    def set_status(self, text: str, color: str = "#cbd5e1") -> None:
        self.root.after(0, lambda: (self.status_var.set(text), self.lbl_status.configure(fg=color)))

    def set_progress(self, value: float, percent_text: str = "") -> None:
        self.root.after(
            0,
            lambda: (
                self.progress_var.set(value),
                self.percent_var.set(percent_text),
            ),
        )

    # =====================================================================
    # SÜRÜM OKUMA / YAZMA İŞLEMLERİ
    # =====================================================================
    def _get_version_url(self) -> str:
        """Varsa .env içindeki UPDATE_URL değerini, yoksa DEFAULT_VERSION_URL'i döndürür."""
        env_path = os.path.join(self.base_dir, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("UPDATE_URL="):
                            val = line.strip().split("=", 1)[1].strip()
                            if val:
                                return val
            except Exception:
                pass
        return DEFAULT_VERSION_URL

    def _read_local_version(self) -> str:
        path = os.path.join(self.base_dir, LOCAL_VERSION_FILE)
        if not os.path.exists(path):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("1.0.0")
            except Exception:
                pass
            return "1.0.0"
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip() or "1.0.0"
        except Exception:
            return "1.0.0"

    def _write_local_version(self, new_version: str) -> None:
        path = os.path.join(self.base_dir, LOCAL_VERSION_FILE)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_version.strip())

    # =====================================================================
    # GÜNCELLEME VE İNDİRME İŞ PARÇACIĞI (WORKER THREAD)
    # =====================================================================
    def _start_update_thread(self) -> None:
        worker = threading.Thread(target=self._update_workflow, daemon=True)
        worker.start()

    def _update_workflow(self) -> None:
        zip_path = os.path.join(self.base_dir, TEMP_ZIP_FILE)

        try:
            self.set_status("Güncelleme kontrol ediliyor...")
            self.set_progress(10, "")

            local_ver = self._read_local_version()
            version_url = self._get_version_url()

            # 1. Sunucudaki version.json dosyasını çek
            resp = requests.get(version_url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            remote_data = resp.json()

            remote_ver = str(remote_data.get("version", "")).strip()
            download_url = str(remote_data.get("url", "")).strip()

            if not remote_ver or not download_url:
                raise ValueError("Sunucudaki version.json formatı geçersiz.")

            # 2. Sürüm karşılaştırması yap
            if parse_version(remote_ver) <= parse_version(local_ver):
                # Güncelleme yok -> doğrudan ana uygulamayı başlat
                self.set_progress(100, "Güncel")
                self.root.after(100, self._launch_main_and_exit)
                return

            # 3. Güncelleme var -> ZIP dosyasını chunks halinde indir
            self.set_status("Uygulama Güncelleniyor... Lütfen bekleyin", color="#38bdf8")
            self.set_progress(0, "0%")

            with requests.get(download_url, stream=True, timeout=REQUEST_TIMEOUT) as dl_resp:
                dl_resp.raise_for_status()
                total_bytes = int(dl_resp.headers.get("content-length", 0))
                downloaded_bytes = 0

                with open(zip_path, "wb") as zip_file:
                    for chunk in dl_resp.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        zip_file.write(chunk)
                        downloaded_bytes += len(chunk)

                        if total_bytes > 0:
                            pct = (downloaded_bytes / total_bytes) * 100
                            mb_done = downloaded_bytes / (1024 * 1024)
                            mb_total = total_bytes / (1024 * 1024)
                            self.set_progress(pct, f"%{pct:.0f} ({mb_done:.1f} / {mb_total:.1f} MB)")
                        else:
                            # Content-Length başlığı yoksa dinamik ilerleme göster
                            kb_done = downloaded_bytes / 1024
                            self.set_progress(50, f"{kb_done:.0f} KB indirildi")

            # 4. İndirilen ZIP dosyasını mevcut klasörün (dist) içine çıkart
            self.set_status("Dosyalar çıkartılıyor...", color="#fbbf24")
            self.set_progress(100, "%100")

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(self.base_dir)

            # 5. local_version.txt güncelle ve geçici ZIP dosyasını sil
            self._write_local_version(remote_ver)
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except OSError:
                    pass

            self.set_status("Güncelleme tamamlandı! Başlatılıyor...", color="#4ade80")
            self.root.after(400, self._launch_main_and_exit)

        except Exception:
            # Yarım kalan geçici ZIP varsa temizle
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except OSError:
                    pass

            # Sunucuya ulaşılamadıysa 2 saniye uyarı gösterip mevcut sürümü başlat
            self.set_status(
                "Sunucuya ulaşılamadı, mevcut sürüm başlatılıyor...",
                color="#f87171",
            )
            self.set_progress(100, "Çevrimdışı Başlatma")
            self.root.after(2000, self._launch_main_and_exit)

    # =====================================================================
    # ANA UYGULAMAYI BAŞLATMA VE KAPANMA
    # =====================================================================
    def _launch_main_and_exit(self) -> None:
        """Ana RPA .exe dosyasını subprocess ile başlatır ve güncelleyiciyi kapatır."""
        target_exe = None
        for candidate in MAIN_EXE_CANDIDATES:
            full_path = os.path.join(self.base_dir, candidate)
            if os.path.exists(full_path):
                target_exe = full_path
                break

        if target_exe:
            try:
                subprocess.Popen(
                    [target_exe],
                    cwd=self.base_dir,
                    creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0,
                )
            except Exception:
                pass
        else:
            # Eğer geliştirme ortamındaysak (.exe henüz derlenmediyse) gui_app.py'yi başlat
            gui_script = os.path.join(self.base_dir, "gui_app.py")
            if os.path.exists(gui_script):
                subprocess.Popen([sys.executable, gui_script], cwd=self.base_dir)

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoUpdaterGUI(root)
    root.mainloop()

