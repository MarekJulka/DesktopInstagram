# views/profile_view.py
import os
import io
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw, ExifTags, UnidentifiedImageError
import api_utils as api
import requests
from datetime import datetime, timedelta

THUMB_SIZE = 180
COLS = 3
GAP = 4
UTC_OFFSET_HOURS = 2  # Europe/Warsaw
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "YourApp/1.0 (you@example.com)"

class ProfileFeed(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        self.thumbs = []
        self.tab_selected = "POSTS"
        self.user_data = {}
        self.grid_frame = None
        self.albums_frame = None
        self.post_count_label = None

        # fetch device coords once
        try:
            js = requests.get("http://ip-api.com/json", timeout=2).json()
            self.device_lat = js.get("lat")
            self.device_lon = js.get("lon")
        except:
            self.device_lat = self.device_lon = None

        self._fetch_profile()
        self._build_profile_header()
        self._build_tab_buttons()
        self._build_image_grid("/api/images")

    def _reverse_to_city(self, lat, lon):
        """Use Nominatim to get the city from coordinates."""
        if lat is None or lon is None:
            return ""
        try:
            r = requests.get(
                NOMINATIM_URL,
                params={"format": "json", "lat": lat, "lon": lon, "zoom": 10},
                headers={"User-Agent": USER_AGENT},
                timeout=3
            ).json()
            addr = r.get("address", {})
            return addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county","")
        except:
            return ""

    def _loc_to_city(self, loc):
        """
        If loc is 'lat,lon' try reverse-geocode to city,
        otherwise return loc as-is.
        """
        try:
            lat_str, lon_str = loc.split(",", 1)
            lat, lon = float(lat_str), float(lon_str)
            city = self._reverse_to_city(lat, lon)
            return city or loc
        except:
            return loc

    def _fetch_profile(self):
        try:
            resp = api.api_get("/api/profile", auth=True)
            if resp.ok:
                self.user_data = resp.json()
        except:
            self.user_data = {}

    def _build_profile_header(self):
        header = tk.Frame(self, bg="white")
        header.pack(pady=20, fill="x")

        left = tk.Frame(header, bg="white")
        left.pack(side="left", padx=30)

        profile_pic = self._load_profile_picture()
        self.profile_label = tk.Label(left, image=profile_pic, bg="white", cursor="hand2")
        self.profile_label.image = profile_pic
        self.profile_label.pack()
        self.profile_label.bind("<Button-1>", self._change_profile_picture)

        right = tk.Frame(header, bg="white")
        right.pack(side="left", padx=40, anchor="n")

        username = self.user_data.get("username", api.CURRENT_USER_EMAIL or "user@example.com")
        tk.Label(right, text=username, fg="black", bg="white",
                 font=("Arial", 16, "bold")).pack(anchor="w")

        tk.Button(right, text="Edit Profile", command=self._edit_profile,
                  font=("Arial", 10), relief="raised", bd=1).pack(anchor="w", pady=5)

        post_resp = api.api_get("/api/images", auth=True)
        post_count = len(post_resp.json()) if post_resp.ok else 0

        stats = tk.Frame(right, bg="white"); stats.pack(anchor="w", pady=(10,0))
        for label, value in [("Posts", post_count), ("Followers", 0), ("Following", 0)]:
            stat = tk.Frame(stats, bg="white"); stat.pack(side="left", padx=10)
            val_lbl = tk.Label(stat, text=str(value), fg="black", bg="white",
                               font=("Arial", 12, "bold"))
            val_lbl.pack()
            if label == "Posts":
                self.post_count_label = val_lbl
            tk.Label(stat, text=label, fg="gray", bg="white",
                     font=("Arial", 10)).pack()

        bio_text = self.user_data.get("bio", "Your bio goes here...\nAdd something about you.")
        self.bio_label = tk.Label(right, text=bio_text, fg="black", bg="white",
                                  font=("Arial", 10), justify="left", wraplength=300)
        self.bio_label.pack(anchor="w", pady=10)

    def _refresh_post_count(self):
        resp = api.api_get("/api/images", auth=True)
        count = len(resp.json()) if resp.ok else 0
        if self.post_count_label:
            self.post_count_label.config(text=str(count))

    def _change_profile_picture(self, _event=None):
        path = filedialog.askopenfilename(
            title="Choose new profile picture",
            filetypes=[("Image files", "*.jpg *.jpeg *.png")]
        )
        if not path:
            return
        if not path.lower().endswith((".jpg", ".jpeg", ".png")):
            messagebox.showerror("Invalid Format", "Please select a JPEG or PNG image.")
            return

        with open(path, "rb") as f:
            resp = requests.post(
                f"{api.API_URL}/api/profile-picture",
                files={"file": f},
                headers={"Authorization": f"Bearer {api.TOKEN}"}
            )
        if resp.ok:
            new_pic = self._load_profile_picture()
            self.profile_label.config(image=new_pic)
            self.profile_label.image = new_pic
        else:
            try:
                err = resp.json().get("error", resp.text)
            except:
                err = resp.text or f"Status {resp.status_code}"
            messagebox.showerror("Upload Failed", err)

    def _edit_profile(self):
        popup = tk.Toplevel(self)
        popup.title("Edit Profile")
        popup.config(bg="white")

        tk.Label(popup, text="Bio", bg="white", fg="black",
                 font=("Arial", 10, "bold")).pack(pady=(15, 5))

        bio_entry = tk.Text(popup, height=4, width=40, bg="white",
                            fg="black", insertbackground="black", relief="solid")
        bio_entry.insert("1.0", self.user_data.get("bio", ""))
        bio_entry.pack(pady=(0, 10))

        def save():
            new_bio = bio_entry.get("1.0", "end").strip()
            payload = {"username": self.user_data.get("username", ""), "bio": new_bio}
            resp = requests.post(
                f"{api.API_URL}/api/profile-edit",
                json=payload,
                headers={"Authorization": f"Bearer {api.TOKEN}"}
            )
            if resp.ok:
                self.user_data["bio"] = new_bio
                self.bio_label.config(text=new_bio)
                popup.destroy()
            else:
                try:
                    err = resp.json().get("error", resp.text)
                except:
                    err = resp.text or f"Status {resp.status_code}"
                messagebox.showerror("Error", err)

        tk.Button(popup, text="Save", command=save,
                  font=("Arial", 10), relief="raised", bd=1).pack(pady=10)

        popup.transient(self)
        popup.grab_set()
        popup.focus_set()

    def _load_profile_picture(self, size=90):
        try:
            user_id = self.user_data.get("id")
            if user_id:
                resp = requests.get(f"{api.API_URL}/uploads/profile_{user_id}.jpg")
                if resp.status_code == 200:
                    pil = Image.open(io.BytesIO(resp.content))
                    pil = pil.resize((size, size), Image.LANCZOS)
                    return ImageTk.PhotoImage(self._make_circle(pil))
        except:
            pass
        pil = Image.new("RGB", (size, size), "#bbb")
        return ImageTk.PhotoImage(self._make_circle(pil))

    def _make_circle(self, img):
        size = img.size[0]
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0,0,size,size), fill=255)
        result = Image.new("RGB", (size,size), (255,255,255))
        result.paste(img, (0,0), mask)
        return result

    def _build_tab_buttons(self):
        self.tabs = tk.Frame(self, bg="white")
        self.tabs.pack(pady=(10,5), anchor="w", padx=40)

        self.tab_labels = {}
        for name in ["POSTS", "ALBUMS"]:
            lbl = tk.Label(self.tabs, text=name,
                           fg="black" if name == self.tab_selected else "gray",
                           bg="white", font=("Arial",10,"bold"), padx=20, cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, n=name: self._change_tab(n))
            self.tab_labels[name] = lbl

    def _change_tab(self, name):
        self.tab_selected = name
        for n, lbl in self.tab_labels.items():
            lbl.config(fg="black" if n == name else "gray")

        if name == "POSTS":
            if self.albums_frame:
                self.albums_frame.destroy()
                self.albums_frame = None
            self._build_image_grid("/api/images")
        else:
            if self.grid_frame:
                self.grid_frame.destroy()
                self.grid_frame = None
            self._build_album_view()

    def _build_image_grid(self, endpoint):
        if self.grid_frame:
            self.grid_frame.destroy()
        self.grid_frame = tk.Frame(self, bg="white")
        self.grid_frame.pack(pady=10, anchor="w", padx=40)

        resp = api.api_get(endpoint, auth=True)
        images = resp.json() if resp.ok else []
        if not images:
            tk.Label(self.grid_frame, text="No photos yet.", fg="gray", bg="white")\
              .pack(pady=20)
            return

        row = col = 0
        for img_data in images:
            tr = api.api_get(f"/uploads/{img_data['filename']}")
            if tr.status_code != 200:
                continue
            try:
                pil = Image.open(io.BytesIO(tr.content))
            except UnidentifiedImageError:
                continue

            w, h = pil.size
            s = min(w, h)
            pil = pil.crop(((w-s)//2,(h-s)//2,(w+s)//2,(h+s)//2))
            pil = pil.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)

            tk_img = ImageTk.PhotoImage(pil)
            self.thumbs.append(tk_img)

            ctr = tk.Frame(self.grid_frame, bg="white")
            ctr.grid(row=row, column=col, padx=GAP, pady=GAP)

            lbl = tk.Label(ctr, image=tk_img, bg="white", cursor="hand2")
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, d=img_data: self._open_image_detail(d))

            # Only show description, not date/location
            tk.Label(ctr, text=img_data.get("description","No description"),
                     fg="black", bg="white", font=("Arial",9)).pack(pady=(2,0))

            col += 1
            if col == COLS:
                col = 0
                row += 1


    def _open_image_detail(self, img_data):
        popup = tk.Toplevel(self)
        popup.title("Photo Details")
        popup.config(bg="white")

        tr = api.api_get(f"/uploads/{img_data['filename']}")
        if tr.status_code == 200:
            try:
                pil = Image.open(io.BytesIO(tr.content))
            except UnidentifiedImageError:
                pil = Image.new("RGB", (300,300), "#ccc")
        else:
            pil = Image.new("RGB", (300,300), "#ccc")

        max_w = int(popup.winfo_screenwidth()*0.6)
        max_h = int(popup.winfo_screenheight()*0.6)
        pil.thumbnail((max_w, max_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(pil)

        img_lbl = tk.Label(popup, image=photo, bg="white")
        img_lbl.image = photo
        img_lbl.pack(padx=10, pady=10)

        tk.Label(popup, text=img_data.get("description",""),
                 fg="black", bg="white", font=("Arial",12), wraplength=500)\
          .pack(padx=10, pady=(0,5))

        raw_ts = img_data.get("taken_at") or img_data.get("uploaded_at","")
        try:
            fmt = "%Y-%m-%d %H:%M:%S" if len(raw_ts)>16 else "%Y-%m-%d %H:%M"
            dt = datetime.strptime(raw_ts, fmt) + timedelta(hours=UTC_OFFSET_HOURS)
            taken_str = dt.strftime("%d %b %Y %H:%M")
        except:
            taken_str = "Unknown"
        tk.Label(popup, text=f"Taken at: {taken_str}", fg="gray", bg="white", font=("Arial",10))\
          .pack(padx=10, pady=(0,2))

        raw_loc = img_data.get("location","")
        if not raw_loc and self.device_lat is not None:
            raw_loc = f"{self.device_lat},{self.device_lon}"
        city = self._loc_to_city(raw_loc)
        tk.Label(popup, text=f"Location: {city}", fg="gray", bg="white", font=("Arial",10))\
          .pack(padx=10, pady=(0,5))

        def delete_photo():
            if not messagebox.askyesno("Delete Photo", "Are you sure you want to delete this photo?"):
                return
            r = requests.delete(
                f"{api.API_URL}/api/images/{img_data['filename']}",
                headers={"Authorization": f"Bearer {api.TOKEN}"}
            )
            if r.ok:
                popup.destroy()
                self._build_image_grid("/api/images")
                self._refresh_post_count()
            else:
                try:
                    err = r.json().get("error", r.text)
                except:
                    err = r.text or f"Status {r.status_code}"
                messagebox.showerror("Delete Failed", err)

        tk.Button(popup, text="Delete Photo", fg="black", bg="#d00",
                  relief="raised", bd=1, command=delete_photo)\
          .pack(pady=(10,15))

        popup.transient(self)
        popup.grab_set()
        popup.focus_set()

    def _build_album_view(self):
        self.albums_frame = tk.Frame(self, bg="white")
        self.albums_frame.pack(fill="both", expand=True, pady=10, padx=40)

        tk.Button(self.albums_frame, text="+ New Album",
                  font=("Arial",10,"bold"), relief="raised", bd=1,
                  command=self._create_album_dialog)\
          .pack(anchor="w", pady=(0,10))

        resp = api.api_get("/api/albums", auth=True)
        albums = resp.json() if resp.ok else []
        if not albums:
            tk.Label(self.albums_frame, text="No albums yet.", fg="gray", bg="white")\
              .pack(pady=20)
            return

        for alb in albums:
            fr = tk.Frame(self.albums_frame, bg="white", bd=1, relief="solid",
                          padx=10, pady=6)
            fr.pack(fill="x", pady=4)

            try:
                dt = datetime.fromisoformat(alb['created_at'])
                created = dt.strftime("%d %b %Y")
            except:
                created = ""
            tk.Label(fr, text=alb['name'], fg="black", bg="white",
                     font=("Arial",12,"bold")).grid(row=0, column=0, sticky="w")
            tk.Label(fr, text=created, fg="gray", bg="white",
                     font=("Arial",10)).grid(row=1, column=0, sticky="w")

            tk.Button(fr, text="Open", relief="raised", bd=1,
                      command=lambda a=alb: self._open_album(a))\
              .grid(row=0, column=1, rowspan=2, padx=10)

    def _create_album_dialog(self):
        popup = tk.Toplevel(self)
        popup.title("New Album")
        popup.config(bg="white")

        tk.Label(popup, text="Album Name:", bg="white", fg="black").pack(pady=(10,0))
        name_ent = tk.Entry(popup, width=30); name_ent.pack(pady=5)

        tk.Label(popup, text="Description:", bg="white", fg="black").pack(pady=(10,0))
        desc_ent = tk.Text(popup, width=30, height=3); desc_ent.pack(pady=5)

        def save():
            name = name_ent.get().strip()
            if not name:
                return messagebox.showwarning("Create Album", "Please enter a name for your album.")

            resp = requests.post(
                f"{api.API_URL}/api/albums",
                json={"name": name, "description": desc_ent.get("1.0","end").strip()},
                headers={"Authorization": f"Bearer {api.TOKEN}"}
            )
            if resp.ok:
                popup.destroy()
                self._build_album_view()
            else:
                try:
                    err = resp.json().get("error","")
                except:
                    err = resp.text or ""
                messagebox.showerror("Create Album Failed", err or "Could not create album.")

        tk.Button(popup, text="Create", command=save,
                  font=("Arial",10), relief="raised", bd=1).pack(pady=10)

        popup.transient(self)
        popup.grab_set()
        popup.focus_set()

    def _open_album(self, album):
        popup = tk.Toplevel(self)
        popup.title(album['name'])
        popup.config(bg="white")

        tk.Label(popup, text=album['name'], fg="black", bg="white",
                 font=("Arial",14,"bold")).pack(pady=(10,0))
        tk.Label(popup, text=album.get('description',''), fg="gray", bg="white",
                 wraplength=400, justify="left").pack(pady=(0,10))

        tk.Button(popup, text="+ Add Photo", relief="raised", bd=1,
                  command=lambda a=album, p=popup: self._add_photo_to_album(a, p))\
          .pack()

        frame = tk.Frame(popup, bg="white"); frame.pack(pady=10, padx=10)
        resp = api.api_get(f"/api/albums/{album['id']}/images", auth=True)
        photos = resp.json() if resp.ok else []
        if not photos:
            tk.Label(frame, text="No photos yet.", fg="gray", bg="white")\
              .pack(pady=20)
        else:
            r = c = 0
            for p in photos:
                tr = api.api_get(f"/uploads/{p['filename']}")
                if tr.status_code != 200:
                    continue
                try:
                    pil = Image.open(io.BytesIO(tr.content))
                except UnidentifiedImageError:
                    continue

                w, h = pil.size
                s = min(w, h)
                pil = pil.crop(((w-s)//2,(h-s)//2,(w+s)//2,(h+s)//2))
                pil = pil.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(pil)
                self.thumbs.append(tk_img)

                cont = tk.Frame(frame, bg="white")
                cont.grid(row=r, column=c, padx=GAP, pady=GAP)

                lbl = tk.Label(cont, image=tk_img, bg="white", cursor="hand2")
                lbl.pack()
                lbl.bind("<Button-1>", lambda e, data=p: self._open_image_detail(data))

                tk.Label(cont, text=p.get("description",""),
                         fg="black", bg="white", font=("Arial",9)).pack(pady=(2,0))

                ds = p.get("taken_at") or p["uploaded_at"]
                try:
                    fmt = "%Y-%m-%d %H:%M:%S" if len(ds)>16 else "%Y-%m-%d %H:%M"
                    dt = datetime.strptime(ds, fmt) + timedelta(hours=UTC_OFFSET_HOURS)
                    ds_fmt = dt.strftime("%d %b %Y %H:%M")
                except:
                    ds_fmt = "Unknown date"
                tk.Label(cont, text=ds_fmt, fg="gray", bg="white", font=("Arial",8)).pack()

                loc = p.get("location","")
                if not loc and self.device_lat is not None:
                    loc = f"{self.device_lat},{self.device_lon}"
                city = self._loc_to_city(loc)
                tk.Label(cont, text=f"Location: {city}", fg="gray", bg="white", font=("Arial",8))\
                  .pack()

                c += 1
                if c == COLS:
                    c = 0
                    r += 1

        popup.transient(self)
        popup.grab_set()
        popup.focus_set()

    def _add_photo_to_album(self, album, parent_popup):
        path = filedialog.askopenfilename(
            title="Choose image",
            filetypes=[("Images","*.jpg *.jpeg *.png")]
        )
        if not path:
            return

        pil = Image.open(path)
        raw = pil._getexif() or {}
        exif = {}
        for tag, val in raw.items():
            name = ExifTags.TAGS.get(tag, tag)
            exif[name] = val
        gps = {}
        if "GPSInfo" in exif:
            for t, v in exif["GPSInfo"].items():
                sub = ExifTags.GPSTAGS.get(t, t)
                gps[sub] = v

        dt_orig = exif.get("DateTimeOriginal")
        if dt_orig:
            taken_at = dt_orig.replace(":", "-", 2)
        else:
            taken_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "GPSLatitude" in gps and "GPSLongitude" in gps:
            def to_deg(vals):
                d, m, s = vals
                return d[0]/d[1] + m[0]/(m[1]*60) + s[0]/(s[1]*3600)
            lat = to_deg(gps["GPSLatitude"])
            if gps.get("GPSLatitudeRef","N")!="N": lat = -lat
            lon = to_deg(gps["GPSLongitude"])
            if gps.get("GPSLongitudeRef","E")!="E": lon = -lon
            location = f"{lat:.6f},{lon:.6f}"
        else:
            if self.device_lat is not None:
                location = f"{self.device_lat},{self.device_lon}"
            else:
                location = simpledialog.askstring(
                    "Location", "Enter location for this photo:", parent=parent_popup
                ) or ""

        desc = simpledialog.askstring("Description", "Photo description:", parent=parent_popup)
        if desc is None:
            return

        with open(path, "rb") as f:
            resp = requests.post(
                f"{api.API_URL}/api/albums/{album['id']}/images",
                files={"file": (os.path.basename(path), f)},
                data={
                    "description": desc,
                    "taken_at": taken_at,
                    "location": location
                },
                headers={"Authorization": f"Bearer {api.TOKEN}"}
            )

        if resp.status_code in (200, 201):
            parent_popup.destroy()
            self._open_album(album)
            self._refresh_post_count()
        else:
            try:
                err = resp.json().get("error", resp.text)
            except:
                err = resp.text or f"Status {resp.status_code}"
            messagebox.showerror("Error", err)
