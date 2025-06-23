import tkinter as tk
from views.profile_view import ProfileFeed
from views.upload_view import open_upload_dialog
import api_utils as api

SIDEBAR_BG   = "#fff"
CONTENT_BG   = "#f9f9f9"
HIGHLIGHT_FG = "black"
INACTIVE_FG  = "#888"
HOVER_FG     = "#333"
LOGOUT_FG    = "#d00"

class MainView(tk.Frame):
    def __init__(self, master, on_logout):
        super().__init__(master, bg=SIDEBAR_BG)
        self.on_logout = on_logout
        self.content_frame = None
        self.active_label = None
        self.nav_items = {}

        self.sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=160)
        self.sidebar.pack(side="left", fill="y")

        self.content = tk.Frame(self, bg=CONTENT_BG)
        self.content.pack(side="right", fill="both", expand=True)

        self._build_sidebar()
        self.show_profile()

    def _build_sidebar(self):
        self._add_nav("🏠 Home", self.show_profile)
        self._add_nav("📤 Upload", self.show_upload)
        self._add_nav("👤 Profile", self.show_profile)
        self._add_nav("🚪 Logout", self.logout, is_logout=True)

        tk.Label(self.sidebar, text=f"Logged in: {api.CURRENT_USER_EMAIL or ''}",
                 fg="black", bg=SIDEBAR_BG, font=("Arial", 9, "bold")
                 ).pack(side="bottom", pady=10)

    def _add_nav(self, text, command, is_logout=False):
        fg = LOGOUT_FG if is_logout else INACTIVE_FG
        label = tk.Label(self.sidebar, text=text, fg=fg,
                         bg=SIDEBAR_BG, font=("Arial", 12, "bold"),
                         anchor="w", cursor="hand2", padx=20, pady=10)
        label.pack(fill="x")

        if not is_logout:
            label.bind("<Enter>", lambda e, l=label: self._on_hover(l))
            label.bind("<Leave>", lambda e, l=label: self._on_leave(l))

        label.bind("<Button-1>", lambda e: command())
        self.nav_items[text] = label

    def _on_hover(self, label):
        if label != self.active_label:
            label.config(fg=HOVER_FG, font=("Arial", 12, "bold", "underline"))

    def _on_leave(self, label):
        if label != self.active_label:
            label.config(fg=INACTIVE_FG, font=("Arial", 12, "bold"))

    def _highlight(self, text):
        for lbl_text, label in self.nav_items.items():
            if lbl_text == text:
                label.config(fg=HIGHLIGHT_FG, font=("Arial", 12, "bold"))
                self.active_label = label
            elif "Logout" not in lbl_text:
                label.config(fg=INACTIVE_FG, font=("Arial", 12, "bold"))

    def _switch_content(self, new_frame):
        if self.content_frame:
            self.content_frame.destroy()
        self.content_frame = new_frame
        self.content_frame.pack(fill="both", expand=True)

    def show_profile(self):
        self._highlight("👤 Profile")
        self._switch_content(ProfileFeed(self.content))

    def show_upload(self):
        self._highlight("📤 Upload")
        frame = tk.Frame(self.content, bg=CONTENT_BG)
        tk.Label(frame, text="Pick a photo & add a description", fg="black", bg=CONTENT_BG).pack(pady=10)
        tk.Button(frame, text="🖼️ Upload", width=20, bg="#0095f6", fg="black",
                  relief="flat", command=lambda: open_upload_dialog(self, self.show_profile)).pack(pady=10)
        self._switch_content(frame)

    def logout(self):
        api.clear_token()
        self.on_logout()
