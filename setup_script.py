import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

def create_shortcut_vbs(target, shortcut_path, icon_path):
    vbs_content = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target}"
oLink.IconLocation = "{icon_path}"
oLink.Save
"""
    vbs_path = os.path.join(os.environ['TEMP'], "createshortcut.vbs")
    with open(vbs_path, "w") as f:
        f.write(vbs_content)
    os.system(f'cscript //nologo "{vbs_path}"')

def install():
    install_dir = entry.get()
    if not install_dir:
        messagebox.showerror("Hata", "Lütfen geçerli bir konum seçin.")
        return
        
    if not os.path.exists(install_dir):
        try:
            os.makedirs(install_dir)
        except Exception as e:
            messagebox.showerror("Hata", f"Klasör oluşturulamadı!\n{e}")
            return
            
    # _MEIPASS holds the bundled files (OnlineXoX.exe and icon.ico)
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    src_exe = os.path.join(base_path, "OnlineXoX.exe")
    src_icon = os.path.join(base_path, "icon.ico")
    
    dest_exe = os.path.join(install_dir, "OnlineXoX.exe")
    dest_icon = os.path.join(install_dir, "icon.ico")
    
    try:
        if not os.path.exists(src_exe):
            messagebox.showerror("Hata", "Kurulum dosyaları (OnlineXoX.exe) bulunamadı!")
            return
            
        shutil.copy2(src_exe, dest_exe)
        if os.path.exists(src_icon):
            shutil.copy2(src_icon, dest_icon)
            
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop, "Online XOX.lnk")
        create_shortcut_vbs(dest_exe, shortcut_path, dest_icon if os.path.exists(dest_icon) else dest_exe)
        
        messagebox.showinfo("Başarılı", "Kurulum başarıyla tamamlandı! Masaüstündeki kısayoldan oyuna girebilirsiniz.")
        root.destroy()
    except Exception as e:
        messagebox.showerror("Hata", f"Kurulum sırasında bir hata oluştu:\n{e}")

root = tk.Tk()
root.title("Online XOX Kurulumu")
root.geometry("450x180")
root.configure(bg="#2E3440")

# Setup UI Styling
title_label = tk.Label(root, text="Online XOX Oyunu Kurulumu", font=("Arial", 14, "bold"), bg="#2E3440", fg="white")
title_label.pack(pady=10)

frame = tk.Frame(root, bg="#2E3440")
frame.pack(pady=5)

entry = tk.Entry(frame, width=45, font=("Arial", 10))
entry.insert(0, os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), "OnlineXoX"))
entry.pack(side=tk.LEFT, padx=5)

def browse():
    d = filedialog.askdirectory()
    if d:
        entry.delete(0, tk.END)
        entry.insert(0, os.path.join(d, "OnlineXoX"))

tk.Button(frame, text="Gözat...", command=browse, bg="#4C566A", fg="white").pack(side=tk.LEFT)
tk.Button(root, text="ŞİMDİ KUR", bg="#A3BE8C", fg="black", font=("Arial", 12, "bold"), width=20, command=install).pack(pady=10)

root.mainloop()
