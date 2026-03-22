import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import threading

# ---------------------------------------------------------------------------
# Path setup so imports work when bundled with PyInstaller
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, application_path)

try:
    from udf_to_docx import udf_to_docx
    from main import main as docx_to_udf
    from udf_to_pdf import udf_to_pdf
    from scanned_pdf_to_udf import pdf_to_udf as scanned_pdf_to_udf
except ImportError as e:
    print(f"Modüller yüklenirken hata: {e}")

# ---------------------------------------------------------------------------
# Color palette & constants
# ---------------------------------------------------------------------------
BG_DARK       = "#1a1a2e"
BG_MID        = "#16213e"
BG_CARD       = "#0f3460"
ACCENT        = "#e94560"
ACCENT_HOVER  = "#ff6b81"
TEXT_WHITE     = "#eaeaea"
TEXT_DIM       = "#a0a0b8"
SUCCESS_GREEN  = "#2ecc71"
ERROR_RED      = "#e74c3c"
BORDER_COLOR   = "#2a2a4a"

FONT_FAMILY    = "Segoe UI"
FONT_FAMILY_FB = "Helvetica"  # fallback for macOS

OPERATIONS = [
    {
        "id": "udf_to_docx",
        "title": "UDF → DOCX",
        "desc": "UDF dosyasını Word belgesine çevir",
        "icon": "📄",
        "ext_in": [("UDF Dosyaları", "*.udf")],
        "ext_out": ".docx",
    },
    {
        "id": "docx_to_udf",
        "title": "DOCX → UDF",
        "desc": "Word belgesini UDF formatına çevir",
        "icon": "📝",
        "ext_in": [("Word Dosyaları", "*.docx")],
        "ext_out": ".udf",
    },
    {
        "id": "udf_to_pdf",
        "title": "UDF → PDF",
        "desc": "UDF dosyasını PDF belgesine çevir",
        "icon": "📕",
        "ext_in": [("UDF Dosyaları", "*.udf")],
        "ext_out": ".pdf",
    },
    {
        "id": "scanned_pdf_to_udf",
        "title": "PDF → UDF",
        "desc": "Taranmış PDF'yi UDF formatına çevir",
        "icon": "🖨️",
        "ext_in": [("PDF Dosyaları", "*.pdf")],
        "ext_out": ".udf",
    },
]


# ---------------------------------------------------------------------------
# Rounded-rectangle helper for Canvas
# ---------------------------------------------------------------------------
def rounded_rect(canvas, x1, y1, x2, y2, radius=20, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1, x2, y1 + radius,
        x2, y2 - radius,
        x2, y2, x2 - radius, y2,
        x1 + radius, y2,
        x1, y2, x1, y2 - radius,
        x1, y1 + radius,
        x1, y1, x1 + radius, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------
class UDFConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UDF Çevirici")
        self.root.geometry("660x620")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        # Try to set icon (won't crash if missing)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.selected_file = None
        self.selected_op = None
        self.card_widgets = []
        self.is_converting = False

        self._build_ui()

    # -----------------------------------------------------------------------
    # UI Construction
    # -----------------------------------------------------------------------
    def _build_ui(self):
        # --- Header ---
        header = tk.Frame(self.root, bg=BG_DARK)
        header.pack(fill=tk.X, padx=30, pady=(25, 5))

        tk.Label(
            header, text="⚖️  UDF Çevirici", font=(FONT_FAMILY, 22, "bold"),
            bg=BG_DARK, fg=TEXT_WHITE,
        ).pack(side=tk.LEFT)

        tk.Label(
            header, text="v1.0", font=(FONT_FAMILY, 10),
            bg=BG_DARK, fg=TEXT_DIM,
        ).pack(side=tk.LEFT, padx=(8, 0), pady=(10, 0))

        # Separator line
        sep = tk.Frame(self.root, bg=ACCENT, height=2)
        sep.pack(fill=tk.X, padx=30, pady=(8, 18))

        # --- Operation cards ---
        cards_label = tk.Label(
            self.root, text="Dönüştürme Türünü Seçin",
            font=(FONT_FAMILY, 11), bg=BG_DARK, fg=TEXT_DIM,
        )
        cards_label.pack(anchor=tk.W, padx=32)

        cards_frame = tk.Frame(self.root, bg=BG_DARK)
        cards_frame.pack(fill=tk.X, padx=28, pady=(8, 0))

        for i, op in enumerate(OPERATIONS):
            row, col = divmod(i, 2)
            card = self._create_card(cards_frame, op)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(1, weight=1)

        # --- Drop zone / file selection ---
        self.drop_frame = tk.Frame(self.root, bg=BG_DARK)
        self.drop_frame.pack(fill=tk.X, padx=30, pady=(20, 0))

        self.drop_canvas = tk.Canvas(
            self.drop_frame, height=90, bg=BG_MID,
            highlightthickness=1, highlightbackground=BORDER_COLOR,
        )
        self.drop_canvas.pack(fill=tk.X)
        self.drop_canvas.bind("<Configure>", self._draw_drop_zone)
        self.drop_canvas.bind("<Button-1>", lambda e: self._select_file())

        # --- Status bar ---
        status_frame = tk.Frame(self.root, bg=BG_DARK)
        status_frame.pack(fill=tk.X, padx=30, pady=(12, 0))

        self.status_icon = tk.Label(
            status_frame, text="💡", font=(FONT_FAMILY, 11),
            bg=BG_DARK, fg=TEXT_DIM,
        )
        self.status_icon.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Bir dönüştürme türü seçin, ardından dosyanızı yükleyin.")
        self.status_label = tk.Label(
            status_frame, textvariable=self.status_var,
            font=(FONT_FAMILY, 10), bg=BG_DARK, fg=TEXT_DIM,
            anchor=tk.W,
        )
        self.status_label.pack(side=tk.LEFT, padx=(6, 0))

        # --- Progress bar ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=BG_MID, background=ACCENT,
            thickness=6, borderwidth=0,
        )
        self.progress = ttk.Progressbar(
            self.root, style="Custom.Horizontal.TProgressbar",
            orient=tk.HORIZONTAL, mode="indeterminate", length=100,
        )
        self.progress.pack(fill=tk.X, padx=30, pady=(8, 0))

        # --- Convert button ---
        self.btn_frame = tk.Frame(self.root, bg=BG_DARK)
        self.btn_frame.pack(fill=tk.X, padx=30, pady=(16, 25))

        self.convert_btn = tk.Button(
            self.btn_frame,
            text="DÖNÜŞTÜR",
            font=(FONT_FAMILY, 13, "bold"),
            bg=ACCENT, fg=TEXT_WHITE,
            activebackground=ACCENT_HOVER, activeforeground=TEXT_WHITE,
            relief=tk.FLAT, cursor="hand2",
            disabledforeground="#666", state=tk.DISABLED,
            command=self._on_convert_click,
        )
        self.convert_btn.pack(fill=tk.X, ipady=10)
        self.convert_btn.bind("<Enter>", lambda e: self.convert_btn.config(bg=ACCENT_HOVER) if self.convert_btn["state"] != "disabled" else None)
        self.convert_btn.bind("<Leave>", lambda e: self.convert_btn.config(bg=ACCENT) if self.convert_btn["state"] != "disabled" else None)

    # -----------------------------------------------------------------------
    # Card widget creation
    # -----------------------------------------------------------------------
    def _create_card(self, parent, op):
        is_selected = False

        card = tk.Frame(parent, bg=BG_CARD, cursor="hand2", padx=14, pady=10)
        card.configure(highlightbackground=BORDER_COLOR, highlightthickness=1)

        icon_lbl = tk.Label(
            card, text=op["icon"], font=(FONT_FAMILY, 20),
            bg=BG_CARD, fg=TEXT_WHITE,
        )
        icon_lbl.pack(anchor=tk.W)

        title_lbl = tk.Label(
            card, text=op["title"], font=(FONT_FAMILY, 12, "bold"),
            bg=BG_CARD, fg=TEXT_WHITE, anchor=tk.W,
        )
        title_lbl.pack(anchor=tk.W, pady=(2, 0))

        desc_lbl = tk.Label(
            card, text=op["desc"], font=(FONT_FAMILY, 9),
            bg=BG_CARD, fg=TEXT_DIM, anchor=tk.W, wraplength=240,
        )
        desc_lbl.pack(anchor=tk.W)

        def on_enter(e):
            if self.selected_op != op["id"]:
                card.configure(highlightbackground=ACCENT, highlightthickness=2)

        def on_leave(e):
            if self.selected_op != op["id"]:
                card.configure(highlightbackground=BORDER_COLOR, highlightthickness=1)

        def on_click(e):
            self._select_operation(op, card)

        for w in (card, icon_lbl, title_lbl, desc_lbl):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        self.card_widgets.append((op["id"], card, [icon_lbl, title_lbl, desc_lbl]))
        return card

    def _select_operation(self, op, card):
        self.selected_op = op["id"]
        self.selected_file = None

        # Reset all cards
        for cid, cframe, labels in self.card_widgets:
            if cid == op["id"]:
                cframe.configure(highlightbackground=ACCENT, highlightthickness=2, bg="#1a4a7a")
                for lbl in labels:
                    lbl.configure(bg="#1a4a7a")
            else:
                cframe.configure(highlightbackground=BORDER_COLOR, highlightthickness=1, bg=BG_CARD)
                for lbl in labels:
                    lbl.configure(bg=BG_CARD)

        self._draw_drop_zone()
        self._set_status("info", "Şimdi dosyanızı seçin veya kutunun üzerine tıklayın.")
        self.convert_btn.config(state=tk.DISABLED)

    # -----------------------------------------------------------------------
    # Drop zone
    # -----------------------------------------------------------------------
    def _draw_drop_zone(self, event=None):
        c = self.drop_canvas
        c.delete("all")
        w = c.winfo_width() or 600
        h = c.winfo_height() or 90

        rounded_rect(c, 4, 4, w - 4, h - 4, radius=14, fill=BG_MID, outline=BORDER_COLOR, width=1)

        if self.selected_file:
            fname = os.path.basename(self.selected_file)
            c.create_text(w // 2, h // 2 - 10, text="✅  " + fname,
                          font=(FONT_FAMILY, 11, "bold"), fill=SUCCESS_GREEN)
            c.create_text(w // 2, h // 2 + 14, text="Dosya seçildi – Dönüştürmek için butona basın",
                          font=(FONT_FAMILY, 9), fill=TEXT_DIM)
        elif self.selected_op:
            c.create_text(w // 2, h // 2 - 10, text="📂  Dosya seçmek için tıklayın",
                          font=(FONT_FAMILY, 12), fill=TEXT_WHITE)
            op_obj = next((o for o in OPERATIONS if o["id"] == self.selected_op), None)
            hint = ""
            if op_obj:
                exts = ", ".join([e[1] for e in op_obj["ext_in"]])
                hint = f"Desteklenen format: {exts}"
            c.create_text(w // 2, h // 2 + 14, text=hint,
                          font=(FONT_FAMILY, 9), fill=TEXT_DIM)
        else:
            c.create_text(w // 2, h // 2 - 6, text="Önce yukarıdan bir dönüştürme türü seçin",
                          font=(FONT_FAMILY, 11), fill=TEXT_DIM)

    # -----------------------------------------------------------------------
    # File selection
    # -----------------------------------------------------------------------
    def _select_file(self):
        if not self.selected_op:
            self._set_status("warn", "Önce bir dönüştürme türü seçmelisiniz.")
            return

        op_obj = next((o for o in OPERATIONS if o["id"] == self.selected_op), None)
        if not op_obj:
            return

        filename = filedialog.askopenfilename(title="Dosya Seç", filetypes=op_obj["ext_in"])
        if filename:
            self.selected_file = filename
            self._draw_drop_zone()
            self.convert_btn.config(state=tk.NORMAL)
            size_kb = os.path.getsize(filename) / 1024
            self._set_status("ok", f"Dosya yüklendi ({size_kb:,.0f} KB). Dönüştürmeye hazır.")

    # -----------------------------------------------------------------------
    # Status management
    # -----------------------------------------------------------------------
    def _set_status(self, kind, text):
        icons = {"info": "💡", "ok": "✅", "warn": "⚠️", "error": "❌", "working": "⏳"}
        colors = {"info": TEXT_DIM, "ok": SUCCESS_GREEN, "warn": "#f1c40f", "error": ERROR_RED, "working": ACCENT}
        self.status_icon.config(text=icons.get(kind, "💡"))
        self.status_var.set(text)
        self.status_label.config(fg=colors.get(kind, TEXT_DIM))

    # -----------------------------------------------------------------------
    # Conversion
    # -----------------------------------------------------------------------
    def _on_convert_click(self):
        if self.is_converting or not self.selected_file or not self.selected_op:
            return

        self.is_converting = True
        self.convert_btn.config(state=tk.DISABLED, text="DÖNÜŞTÜRÜLÜYOR…")
        self._set_status("working", "Dosya dönüştürülüyor, lütfen bekleyin…")
        self.progress.start(12)
        self.root.update()

        # Run conversion in a thread so GUI stays responsive
        threading.Thread(target=self._do_convert, daemon=True).start()

    def _do_convert(self):
        op = self.selected_op
        input_file = os.path.normpath(self.selected_file)
        filename, _ = os.path.splitext(input_file)
        op_obj = next((o for o in OPERATIONS if o["id"] == op), None)
        out_file = filename + (op_obj["ext_out"] if op_obj else ".out")

        try:
            # Pre-validate file
            if not os.path.isfile(input_file):
                raise FileNotFoundError(f"Dosya bulunamadi: {input_file}")

            # Try to read the file to verify access
            with open(input_file, 'rb') as f:
                header = f.read(4)

            if op == "udf_to_docx":
                udf_to_docx(input_file, out_file)
            elif op == "docx_to_udf":
                docx_to_udf(input_file, out_file)
            elif op == "udf_to_pdf":
                udf_to_pdf(input_file, out_file)
            elif op == "scanned_pdf_to_udf":
                scanned_pdf_to_udf(input_file, out_file)

            self.root.after(0, self._on_success, out_file)
        except Exception as e:
            import traceback
            error_detail = f"{e}\n\nDetay:\n{traceback.format_exc()}"
            self.root.after(0, self._on_error, error_detail)

    def _on_success(self, out_file):
        self.progress.stop()
        self.is_converting = False
        self.convert_btn.config(state=tk.NORMAL, text="DÖNÜŞTÜR")

        size_kb = os.path.getsize(out_file) / 1024
        self._set_status("ok", f"Başarılı! Çıktı: {os.path.basename(out_file)} ({size_kb:,.0f} KB)")
        messagebox.showinfo(
            "Dönüştürme Başarılı ✅",
            f"Dosya başarıyla dönüştürüldü!\n\n"
            f"📁 Kayıt yeri:\n{out_file}\n\n"
            f"📦 Boyut: {size_kb:,.0f} KB",
        )

    def _on_error(self, error_msg):
        self.progress.stop()
        self.is_converting = False
        self.convert_btn.config(state=tk.NORMAL, text="DÖNÜŞTÜR")

        self._set_status("error", "Dönüştürme sırasında bir hata oluştu.")
        messagebox.showerror(
            "Hata ❌",
            f"Dönüştürme işlemi sırasında bir hata oluştu:\n\n{error_msg}",
        )

# ---------------------------------------------------------------------------
# Splash screen
# ---------------------------------------------------------------------------
def show_splash(on_done):
    splash = tk.Toplevel()
    splash.overrideredirect(True)

    sw, sh = 480, 260
    x = (splash.winfo_screenwidth() - sw) // 2
    y = (splash.winfo_screenheight() - sh) // 2
    splash.geometry(f"{sw}x{sh}+{x}+{y}")
    splash.configure(bg=BG_DARK)

    tk.Label(
        splash, text="⚖️", font=(FONT_FAMILY, 40),
        bg=BG_DARK, fg=ACCENT,
    ).pack(pady=(30, 0))

    tk.Label(
        splash, text="UDF Çevirici", font=(FONT_FAMILY, 22, "bold"),
        bg=BG_DARK, fg=TEXT_WHITE,
    ).pack(pady=(6, 4))

    sep = tk.Frame(splash, bg=ACCENT, height=2, width=200)
    sep.pack(pady=6)

    tk.Label(
        splash,
        text="Bu UDF dönüştürücü programı\nOnur Çelebi tarafından geliştirilmiştir",
        font=(FONT_FAMILY, 11),
        bg=BG_DARK, fg=TEXT_DIM, justify=tk.CENTER,
    ).pack(pady=(8, 0))

    splash.after(3000, lambda: [splash.destroy(), on_done()])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window during splash

    def open_main():
        root.deiconify()
        UDFConverterApp(root)

    show_splash(open_main)
    root.mainloop()
