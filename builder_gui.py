import sys
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import builder_logic

# Try to import CustomTkinter for modern UI
try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False
    import tkinter.ttk as ttk

class App:
    def __init__(self):
        self.builder = builder_logic.CordovaWrapperBuilder(
            progress_callback=self.on_progress,
            log_callback=self.on_log
        )
        self.is_wrapping = False

        if HAS_CTK:
            self.setup_ctk()
        else:
            self.setup_tk()

    def setup_ctk(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Cordova App Wrapper")
        self.root.geometry("600x700")

        # Main Container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        self.lbl_header = ctk.CTkLabel(self.main_frame, text="Cordova App Wrapper", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_header.pack(pady=(10, 20))

        # Target Folder
        self.frame_target = ctk.CTkFrame(self.main_frame)
        self.frame_target.pack(fill="x", pady=5)

        self.lbl_target = ctk.CTkLabel(self.frame_target, text="Website Folder (Source):")
        self.lbl_target.pack(anchor="w", padx=10, pady=(5, 0))

        self.entry_target = ctk.CTkEntry(self.frame_target, placeholder_text="Select folder containing index.html")
        self.entry_target.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=5)

        self.btn_target = ctk.CTkButton(self.frame_target, text="Browse", width=80, command=self.browse_target)
        self.btn_target.pack(side="right", padx=(5, 10), pady=5)

        # Destination Folder
        self.frame_dest = ctk.CTkFrame(self.main_frame)
        self.frame_dest.pack(fill="x", pady=5)

        self.lbl_dest = ctk.CTkLabel(self.frame_dest, text="Output Folder:")
        self.lbl_dest.pack(anchor="w", padx=10, pady=(5, 0))

        self.entry_dest = ctk.CTkEntry(self.frame_dest, placeholder_text="Auto-generated based on source")
        self.entry_dest.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=5)

        self.btn_dest = ctk.CTkButton(self.frame_dest, text="Browse", width=80, command=self.browse_dest)
        self.btn_dest.pack(side="right", padx=(5, 10), pady=5)

        # Settings
        self.frame_settings = ctk.CTkFrame(self.main_frame)
        self.frame_settings.pack(fill="x", pady=10)

        self.lbl_settings = ctk.CTkLabel(self.frame_settings, text="App Settings", font=ctk.CTkFont(weight="bold"))
        self.lbl_settings.pack(anchor="w", padx=10, pady=5)

        # Grid for settings
        self.frame_settings_grid = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        self.frame_settings_grid.pack(fill="x", padx=5, pady=5)

        # Name
        self.lbl_name = ctk.CTkLabel(self.frame_settings_grid, text="App Name:")
        self.lbl_name.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_name = ctk.CTkEntry(self.frame_settings_grid)
        self.entry_name.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # ID
        self.lbl_id = ctk.CTkLabel(self.frame_settings_grid, text="App ID:")
        self.lbl_id.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_id = ctk.CTkEntry(self.frame_settings_grid, placeholder_text="com.example.app")
        self.entry_id.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Version
        self.lbl_ver = ctk.CTkLabel(self.frame_settings_grid, text="Version:")
        self.lbl_ver.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.entry_ver = ctk.CTkEntry(self.frame_settings_grid)
        self.entry_ver.insert(0, "1.0.0")
        self.entry_ver.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        self.frame_settings_grid.columnconfigure(1, weight=1)

        # Wrap Button
        self.btn_wrap = ctk.CTkButton(self.main_frame, text="Wrap App", height=40, font=ctk.CTkFont(size=16, weight="bold"), command=self.start_wrap)
        self.btn_wrap.pack(fill="x", pady=20)

        # Progress
        self.progress = ctk.CTkProgressBar(self.main_frame)
        self.progress.pack(fill="x", pady=(0, 10))
        self.progress.set(0)

        # Log
        self.txt_log = ctk.CTkTextbox(self.main_frame, height=150)
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.configure(state="disabled")

        # Open Folder Button (Hidden initially)
        self.btn_open = ctk.CTkButton(self.main_frame, text="Open Folder", fg_color="green", command=self.open_output_folder)

        # Start dependency check
        self.root.after(100, self.start_dep_check)

    def setup_tk(self):
        # Fallback to standard tkinter
        self.root = tk.Tk()
        self.root.title("Cordova App Wrapper (Standard Mode)")
        self.root.geometry("600x700")

        style = ttk.Style()
        style.theme_use('clam')

        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill="both", expand=True)

        ttk.Label(self.main_frame, text="Cordova App Wrapper", font=("Helvetica", 18, "bold")).pack(pady=(0, 20))

        # Target
        frame_target = ttk.LabelFrame(self.main_frame, text="Website Folder (Source)", padding=10)
        frame_target.pack(fill="x", pady=5)
        self.entry_target = ttk.Entry(frame_target)
        self.entry_target.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame_target, text="Browse", command=self.browse_target).pack(side="right")

        # Dest
        frame_dest = ttk.LabelFrame(self.main_frame, text="Output Folder", padding=10)
        frame_dest.pack(fill="x", pady=5)
        self.entry_dest = ttk.Entry(frame_dest)
        self.entry_dest.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame_dest, text="Browse", command=self.browse_dest).pack(side="right")

        # Settings
        frame_settings = ttk.LabelFrame(self.main_frame, text="Settings", padding=10)
        frame_settings.pack(fill="x", pady=10)

        ttk.Label(frame_settings, text="App Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_name = ttk.Entry(frame_settings)
        self.entry_name.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(frame_settings, text="App ID:").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_id = ttk.Entry(frame_settings)
        self.entry_id.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(frame_settings, text="Version:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_ver = ttk.Entry(frame_settings)
        self.entry_ver.insert(0, "1.0.0")
        self.entry_ver.grid(row=2, column=1, sticky="ew", pady=2)

        frame_settings.columnconfigure(1, weight=1)

        # Wrap
        self.btn_wrap = ttk.Button(self.main_frame, text="Wrap App", command=self.start_wrap)
        self.btn_wrap.pack(fill="x", pady=20)

        # Progress
        self.progress = ttk.Progressbar(self.main_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))

        # Log
        self.txt_log = tk.Text(self.main_frame, height=10)
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.config(state="disabled")

        self.btn_open = ttk.Button(self.main_frame, text="Open Folder", command=self.open_output_folder)

        self.root.after(100, self.start_dep_check)

    def run(self):
        self.root.mainloop()

    def browse_target(self):
        path = filedialog.askdirectory(title="Select Website Folder")
        if path:
            self.update_entry(self.entry_target, path)
            self.auto_fill(path)

    def browse_dest(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.update_entry(self.entry_dest, path)

    def update_entry(self, entry, text):
        entry.delete(0, "end")
        entry.insert(0, text)

    def auto_fill(self, source_path):
        folder_name = os.path.basename(source_path)
        if not folder_name: # Handle trailing slash
            folder_name = os.path.basename(os.path.dirname(source_path))

        # Set Dest
        parent = os.path.dirname(source_path)
        dest = os.path.join(parent, f"{folder_name} Wrapped")
        self.update_entry(self.entry_dest, dest)

        # Set Name
        self.update_entry(self.entry_name, folder_name)

        # Set ID
        safe_name = "".join(c.lower() for c in folder_name if c.isalnum())
        self.update_entry(self.entry_id, f"com.example.{safe_name}")

    def on_log(self, message):
        self.root.after(0, self._append_log, message)

    def _append_log(self, message):
        if HAS_CTK:
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", message + "\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        else:
            self.txt_log.config(state="normal")
            self.txt_log.insert("end", message + "\n")
            self.txt_log.see("end")
            self.txt_log.config(state="disabled")

    def on_progress(self, percent, step_name):
        self.root.after(0, self._update_progress_ui, percent, step_name)

    def _update_progress_ui(self, percent, step_name):
        val = percent / 100.0
        if HAS_CTK:
            self.progress.set(val)
        else:
            self.progress['value'] = percent

        self._append_log(f"[{percent}%] {step_name}")

    def start_dep_check(self):
        threading.Thread(target=self._check_deps_thread, daemon=True).start()

    def _check_deps_thread(self):
        self.on_log("Checking dependencies...")
        success = self.builder.check_dependencies()
        if not success:
            self.on_log("CRITICAL: Missing dependencies. Check log above.")
            messagebox.showerror("Error", "Missing dependencies. Please see log.")
        else:
            self.on_log("Ready to wrap.")

    def start_wrap(self):
        if self.is_wrapping: return

        target = self.entry_target.get()
        dest = self.entry_dest.get()
        name = self.entry_name.get()
        app_id = self.entry_id.get()
        ver = self.entry_ver.get()

        if not target or not dest or not name or not app_id:
            messagebox.showwarning("Missing Input", "Please fill in all fields.")
            return

        if not os.path.exists(target):
            messagebox.showerror("Error", "Source folder does not exist.")
            return

        if os.path.exists(dest):
            confirm = messagebox.askyesno("Confirm Overwrite", f"The folder '{dest}' already exists.\nDo you want to delete it and replace it?")
            if not confirm:
                return

        self.is_wrapping = True
        self.btn_wrap.configure(state="disabled") if HAS_CTK else self.btn_wrap.config(state="disabled")

        threading.Thread(target=self._wrap_thread, args=(target, dest, name, app_id, ver, True), daemon=True).start()

    def _wrap_thread(self, target, dest, name, app_id, ver, overwrite):
        success = self.builder.wrap_project(target, dest, name, app_id, ver, overwrite=overwrite)
        self.is_wrapping = False

        self.root.after(0, self._wrap_finished, success, dest)

    def _wrap_finished(self, success, dest):
        if HAS_CTK:
            self.btn_wrap.configure(state="normal")
        else:
            self.btn_wrap.config(state="normal")

        if success:
            messagebox.showinfo("Success", "Project wrapped successfully!")
            if HAS_CTK:
                self.btn_open.pack(pady=10)
            else:
                self.btn_open.pack(pady=10)
            self.final_dest = dest
        else:
            messagebox.showerror("Error", "Wrapping failed. See log for details.")

    def open_output_folder(self):
        if not hasattr(self, 'final_dest'): return

        path = self.final_dest
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            self.on_log(f"Could not open folder: {e}")

if __name__ == "__main__":
    import subprocess # re-import for open_output_folder if needed
    app = App()
    app.run()
