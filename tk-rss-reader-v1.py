import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import feedparser
import json
import sqlite3
import webbrowser
from datetime import datetime, timedelta
import threading

class RSSDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('rss_entries.db')
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS saved_entries
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           title TEXT,
                           link TEXT,
                           published TEXT)''')
        self.conn.commit()

    def save_entry(self, entry):
        # Convert datetime to ISO formatted string if necessary.
        published = entry['published']
        if isinstance(published, datetime):
            published = published.strftime('%Y-%m-%d %H:%M:%S')
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO saved_entries (title, link, published) VALUES (?, ?, ?)',
                       (entry['title'], entry['link'], published))
        self.conn.commit()

class RSSSettings:
    def __init__(self):
        self.settings_file = 'rss_settings.json'
        self.default_settings = {
            'feeds': ['http://feeds.bbci.co.uk/news/rss.xml'],
            'days': 7,
            'font_size': 12,
            'dark_mode': False,
            'refresh_interval': 30  # in minutes
        }
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = self.default_settings
            self.save_settings()

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f)

class RSSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RSS Reader")
        self.db = RSSDatabase()
        self.settings = RSSSettings()
        self.entries = []
        self.selected_entries = set()
        self.current_sort = 'date'

        self.setup_ui()
        self.apply_settings()
        self.load_feeds()
        self.start_auto_refresh()

    def setup_ui(self):
        # Menu Bar
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Export Selected", command=self.export_selected)
        file_menu.add_command(label="Export Selected (Markdown)", command=self.export_selected_markdown)
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Settings menu
        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        settings_menu.add_command(label="App Settings", command=self.open_settings)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)

        # Configure styles
        self.style = ttk.Style()
        self.style.theme_use('clam')  # always use 'clam' and then adjust colors
        self.configure_styles()

        # Main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Toolbar
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Refresh", command=self.load_feeds).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Save to DB", command=self.save_selected_to_db).pack(side=tk.LEFT)

        # Entries list inside a Canvas with a Scrollbar
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.entries_frame = ttk.Frame(self.canvas)

        self.entries_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.entries_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mouse wheel events for scrolling (Windows/Mac and Linux)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind("<Button-5>", self._on_mousewheel_linux)

    def _on_mousewheel(self, event):
        # For Windows and MacOS, scrolling is handled via event.delta.
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        # For Linux, mouse wheel events use Button-4 (up) and Button-5 (down).
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def configure_styles(self):
        # Configure base font size.
        self.style.configure('.', font=('Arial', self.settings.settings['font_size']))
        # Light mode default styles.
        self.style.configure('TFrame', background='white')
        self.style.configure('TLabel', foreground='black', background='white')
        self.style.configure('TCheckbutton', background='white')

        # Custom styles for dark mode.
        self.style.configure('Dark.TFrame', background='#333333')
        self.style.configure('Dark.TLabel', foreground='white', background='#333333')
        self.style.configure('Dark.TCheckbutton', background='#333333')

    def apply_settings(self):
        dark_mode = self.settings.settings['dark_mode']
        bg = '#333333' if dark_mode else 'white'
        fg = 'white' if dark_mode else 'black'

        # Update the root window background.
        self.root.config(bg=bg)

        # Update styles based on dark mode.
        if dark_mode:
            self.style.configure('TFrame', background='#333333')
            self.style.configure('TLabel', foreground='white', background='#333333')
            self.style.configure('TCheckbutton', background='#333333')
        else:
            self.style.configure('TFrame', background='white')
            self.style.configure('TLabel', foreground='black', background='white')
            self.style.configure('TCheckbutton', background='white')

        # Update widget colors recursively.
        self.update_widget_colors(self.root, bg, fg)

    def update_widget_colors(self, widget, bg, fg):
        try:
            if isinstance(widget, (tk.Listbox, tk.Entry, tk.Canvas)):
                widget.config(bg=bg, fg=fg, insertbackground=fg)
            else:
                widget.config(bg=bg, fg=fg)
        except tk.TclError:
            pass

        for child in widget.winfo_children():
            self.update_widget_colors(child, bg, fg)

    def open_settings(self):
        SettingsWindow(self)

    def load_feeds(self):
        def fetch_feeds():
            new_entries = []
            cutoff_date = datetime.now() - timedelta(days=self.settings.settings['days'])
            
            for feed_url in self.settings.settings['feeds']:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries:
                        if hasattr(entry, 'published_parsed'):
                            published = datetime(*entry.published_parsed[:6])
                        else:
                            published = datetime.now()
                        if published >= cutoff_date:
                            new_entries.append({
                                'title': entry.title,
                                'link': entry.link,
                                'published': published,
                                'feed': feed_url
                            })
                except Exception as e:
                    self.root.after(0, lambda url=feed_url, err=str(e): 
                                    messagebox.showerror("Error", f"Failed to load feed: {url}\n{err}"))
            
            new_entries.sort(key=lambda x: x['published'], reverse=True)
            self.entries = new_entries
            self.root.after(0, self.display_entries)

        threading.Thread(target=fetch_feeds, daemon=True).start()

    def display_entries(self):
        for widget in self.entries_frame.winfo_children():
            widget.destroy()

        for idx, entry in enumerate(self.entries):
            entry_frame = ttk.Frame(self.entries_frame)
            entry_frame.pack(fill=tk.X, pady=2)

            chk_var = tk.IntVar()
            ttk.Checkbutton(entry_frame, variable=chk_var, 
                          command=lambda i=idx: self.toggle_selection(i)).pack(side=tk.LEFT)

            entry_text = f"{entry['published'].strftime('%Y-%m-%d %H:%M')} - {entry['title']}"
            label = ttk.Label(entry_frame, text=entry_text, cursor="hand2")
            label.pack(side=tk.LEFT, padx=5)
            label.bind("<Button-1>", lambda e, link=entry['link']: webbrowser.open(link))

    def toggle_selection(self, index):
        if index in self.selected_entries:
            self.selected_entries.remove(index)
        else:
            self.selected_entries.add(index)

    def delete_selected(self):
        for index in sorted(self.selected_entries, reverse=True):
            del self.entries[index]
        self.selected_entries.clear()
        self.display_entries()

    def export_selected(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for index in self.selected_entries:
                        entry = self.entries[index]
                        f.write(f"{entry['title']}\n{entry['link']}\n\n")
                messagebox.showinfo("Export", "Entries exported successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export entries:\n{str(e)}")

    def export_selected_markdown(self):
        # Generate a default file name based on current date and time.
        default_name = datetime.now().strftime("export_%Y%m%d_%H%M%S.md")
        file_path = filedialog.asksaveasfilename(defaultextension=".md", initialfile=default_name)
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Export each selected entry as a markdown list item.
                    for index in sorted(self.selected_entries):
                        entry = self.entries[index]
                        published = entry['published'].strftime('%Y-%m-%d %H:%M')
                        f.write(f"- [{entry['title']}]({entry['link']}) - {published}\n")
                messagebox.showinfo("Export", "Entries exported in Markdown format.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export entries:\n{str(e)}")

    def save_selected_to_db(self):
        for index in self.selected_entries:
            self.db.save_entry(self.entries[index])
        messagebox.showinfo("Info", "Selected entries saved to database")

    def start_auto_refresh(self):
        self.load_feeds()
        interval_ms = self.settings.settings['refresh_interval'] * 60 * 1000
        self.root.after(interval_ms, self.start_auto_refresh)

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent.root)
        self.parent = parent
        self.title("Settings")
        # Resize the window to be taller so all options are visible.
        self.geometry("400x400")
        
        # --- RSS Feeds List and Management ---
        # Create a frame for the feeds list and its buttons.
        feeds_frame = ttk.Frame(self)
        feeds_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(feeds_frame, text="RSS Feeds:").pack(anchor="w")
        self.feeds_list = tk.Listbox(feeds_frame, height=5)
        self.feeds_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for feed in self.parent.settings.settings['feeds']:
            self.feeds_list.insert(tk.END, feed)
            
        button_frame = ttk.Frame(feeds_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Add Feed", command=self.add_feed).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Remove Feed", command=self.remove_feed).pack(side=tk.LEFT, padx=5)
        
        # --- Options Layout ---
        # Create a frame for the other settings options arranged in rows.
        options_frame = ttk.Frame(self)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Days to keep
        ttk.Label(options_frame, text="Days to keep:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.days_entry = ttk.Entry(options_frame, width=10)
        self.days_entry.insert(0, str(self.parent.settings.settings['days']))
        self.days_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Font Size
        ttk.Label(options_frame, text="Font Size:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.font_entry = ttk.Entry(options_frame, width=10)
        self.font_entry.insert(0, str(self.parent.settings.settings['font_size']))
        self.font_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Refresh Interval
        ttk.Label(options_frame, text="Refresh Interval (min):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.refresh_entry = ttk.Entry(options_frame, width=10)
        self.refresh_entry.insert(0, str(self.parent.settings.settings['refresh_interval']))
        self.refresh_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Dark Mode Toggle
        ttk.Label(options_frame, text="Dark Mode:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.dark_mode_var = tk.BooleanVar(value=self.parent.settings.settings['dark_mode'])
        dark_mode_cb = ttk.Checkbutton(options_frame, variable=self.dark_mode_var)
        dark_mode_cb.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        
        # --- Save Button ---
        ttk.Button(self, text="Save", command=self.save_settings).pack(pady=10)

    def add_feed(self):
        new_feed = simpledialog.askstring("New Feed", "Enter RSS Feed URL:")
        if new_feed:
            self.feeds_list.insert(tk.END, new_feed)

    def remove_feed(self):
        selection = self.feeds_list.curselection()
        if selection:
            self.feeds_list.delete(selection[0])

    def save_settings(self):
        try:
            self.parent.settings.settings['feeds'] = [url for url in self.feeds_list.get(0, tk.END) if url.strip()]
            self.parent.settings.settings['days'] = int(self.days_entry.get())
            self.parent.settings.settings['font_size'] = int(self.font_entry.get())
            self.parent.settings.settings['refresh_interval'] = int(self.refresh_entry.get())
            self.parent.settings.settings['dark_mode'] = self.dark_mode_var.get()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numerical values for Days, Font Size, and Refresh Interval.")
            return

        self.parent.settings.save_settings()
        self.parent.apply_settings()
        self.parent.load_feeds()
        self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = RSSApp(root)
    root.mainloop()
