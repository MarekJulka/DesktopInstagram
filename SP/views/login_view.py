# views/login_view.py
import tkinter as tk
from tkinter import messagebox
import api_utils as api

BG_ROOT = "#f5f5f5"
BG_INPUT = "#ffffff"
FG_HINT = "#999999"
BTN_BG = "#e0e0e0"
BTN_HOVER = "#d0d0d0"
BTN_TXT = "#222222"

class LoginView(tk.Frame):
    def __init__(self, master, on_success):
        super().__init__(master, bg=BG_ROOT)
        self.on_success = on_success
        self.mode = tk.StringVar(value="login")
        self._build()

    def _build(self):
        tk.Label(self, text="Insta", fg="#222", bg=BG_ROOT,
                 font=("Brush Script MT", 40, "bold")).pack(pady=(40, 30))

        self.email = self._make_entry("Email or login")
        self.password = self._make_entry("Password", show="*")

        # Show/Hide password toggle
        self.show_pw = False
        toggle_btn = tk.Button(self, text="👁", bg=BG_ROOT, fg="#666",
                               font=("Arial", 10), relief="flat", bd=0, cursor="hand2",
                               command=self._toggle_password)
        toggle_btn.place(in_=self.password, relx=1.0, x=-25, rely=0.5, anchor="e")
        self._pw_toggle_btn = toggle_btn

        self.action_btn = self._make_btn("Log in", self.handle_auth)
        self.action_btn.pack(pady=(0, 15))

        switch = tk.Frame(self, bg=BG_ROOT)
        switch.pack()
        self.switch_btn = tk.Button(
            switch, text="Don't have an account? Register",
            font=("Arial", 10, "bold"), fg="#0077cc", bg=BG_ROOT,
            relief="flat", bd=0, cursor="hand2", activeforeground="#005fa3",
            command=self.switch_mode)
        self.switch_btn.pack()

    def _make_entry(self, ph, show=""):
        e = tk.Entry(self, width=30, font=("Arial", 12),
                     bg=BG_INPUT, fg=FG_HINT, insertbackground="black",
                     relief="flat", highlightthickness=1,
                     highlightbackground="#ccc", highlightcolor="#999")
        e.insert(0, ph)
        e.bind("<FocusIn>", lambda _e: self._clear_ph(e, ph, show))
        e.bind("<FocusOut>", lambda _e: self._restore_ph(e, ph))
        e.pack(pady=6, ipady=6)
        return e

    def _make_btn(self, txt, cmd):
        return tk.Button(self, text=txt, command=cmd,
                         cursor="hand2", width=24, font=("Arial", 11, "bold"),
                         bg=BTN_BG, fg=BTN_TXT,
                         activebackground=BTN_HOVER,
                         activeforeground=BTN_TXT, relief="flat", bd=0)

    def _clear_ph(self, ent, ph, show):
        if ent.get() == ph:
            ent.delete(0, tk.END)
            ent.config(fg="black", show=show)

    def _restore_ph(self, ent, ph):
        if not ent.get():
            ent.insert(0, ph)
            ent.config(fg=FG_HINT, show="")

    def _toggle_password(self):
        self.show_pw = not self.show_pw
        if self.show_pw:
            self.password.config(show="")
            self._pw_toggle_btn.config(text="🚫")
        else:
            self.password.config(show="*")
            self._pw_toggle_btn.config(text="👁")

    def handle_auth(self):
        email = self.email.get().strip()
        pwd   = self.password.get().strip()
        if not email or not pwd or email == "Email or login" or pwd == "Password":
            messagebox.showwarning("Empty", "Provide email & password")
            return

        route = "/api/login" if self.mode.get() == "login" else "/api/register"
        resp  = api.api_post(route, json={"email": email, "password": pwd})

        if resp.status_code in (200, 201):
            data = resp.json()
            if self.mode.get() == "login":
                api.save_token(data["token"])
                api.load_token()
                api.CURRENT_USER_EMAIL = data["email"]
                self.on_success()
            else:
                messagebox.showinfo("Done", "Registered – now log in.")
                self.switch_mode()
        else:
            # Safely try to parse JSON; if it fails, show plain text
            try:
                err = resp.json().get("error", resp.text or "Auth failed")
            except ValueError:
                err = resp.text or "Auth failed"
            messagebox.showerror("Error", err)

    def switch_mode(self):
        if self.mode.get() == "login":
            self.mode.set("register")
            self.action_btn.config(text="Register")
            self.switch_btn.config(text="Already have an account? Log in")
        else:
            self.mode.set("login")
            self.action_btn.config(text="Log in")
            self.switch_btn.config(text="Don't have an account? Register")
