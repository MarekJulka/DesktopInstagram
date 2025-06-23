import tkinter as tk
import os
import requests
from tkinter import filedialog, messagebox
import api_utils as api

def open_upload_dialog(root, refresh_cb):
    if not api.TOKEN:
        messagebox.showerror("Session", "Log in again.")
        return

    path = filedialog.askopenfilename(
        title="Choose image",
        filetypes=[("Images", "*.jpg *.jpeg *.png")]
    )
    if not path:
        return

    win = tk.Toplevel(root)
    win.title("Add description")
    win.configure(bg="white")

    # Label
    tk.Label(win, text="Description:", bg="white", fg="black", font=("Arial", 11, "bold")).pack(pady=5)

    # Entry
    entry = tk.Entry(win, width=40, bg="white", fg="black", insertbackground="black")
    entry.pack(pady=5)

    # Send logic
    def send():
        with open(path, "rb") as f:
            resp = requests.post(f"{api.API_URL}/api/upload",
                files={"file": (os.path.basename(path), f)},
                data={"description": entry.get()},
                headers={"Authorization": f"Bearer {api.TOKEN}"})
        if resp.status_code == 200:
            messagebox.showinfo("OK", "Uploaded")
            win.destroy()
            refresh_cb()
        elif resp.status_code == 401:
            api.clear_token()
            messagebox.showerror("Session", "Token expired. Log in again.")
            win.destroy()
            refresh_cb()
        else:
            messagebox.showerror("Error", resp.text)

    # Button
    tk.Button(win, text="Upload", bg="white", fg="black", font=("Arial", 10, "bold"),
              width=15, relief="flat", command=send).pack(pady=10)
