#!/usr/bin/env python3
# Author: Raoul Comninos
# pip install pillow send2trash
import os
import sys
import shutil
import subprocess

# Disable keyring to prevent GNOME keyring warnings on non-GNOME systems
os.environ['PYTHON_KEYRING_BACKEND'] = 'keyring.backends.null.Keyring'
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import json
import random
import time
from send2trash import send2trash

class ImageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Viewer")
        self.root.geometry("1000x700")
        
        # Store the default windowed geometry before going fullscreen
        self.original_geometry = "1000x700+100+100"
        # Set fullscreen immediately during initialization
        self.root.attributes('-fullscreen', True)
        
        # Application state variables
        self.is_fullscreen = True  # Start in fullscreen mode
        self.is_random = False
        self.is_slideshow = False
        self.slideshow_paused = False
        self.slideshow_timer_id = None
        self.slideshow_interval = 3000  # 3 seconds
        self.is_toolbar_hidden = False  # Track toolbar visibility state
        
        # Double-click detection
        self.last_click_time = 0
        self.double_click_threshold = 300  # milliseconds
        
        # Image display variables
        self.current_image = None
        self.current_photo = None
        self.original_image = None
        
        # Animation variables for GIFs
        self.is_animated = False
        self.gif_frames = []
        self.gif_durations = []
        self.current_frame = 0
        self.animation_job = None
        
        # Zoom control variables
        self.zoom_level = 1.0  # Default zoom level (1.0 = fit to window)
        self.zoom_increment = 0.1  # Zoom step size (10%)
        self.min_zoom = 0.1  # Minimum zoom (10%)
        self.max_zoom = 5.0  # Maximum zoom (500%)
        
        # Image panning variables
        self.pan_start_x = None
        self.pan_start_y = None
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.is_panning = False
        
        # Temporary message system
        self.showing_temp_message = False
        
        # Image-specific zoom memory
        self.image_zoom_memory = {}  # Dictionary to store zoom levels per image file
        self.zoom_settings_file = os.path.expanduser("~/.image_viewer_zoom.json")  # Persistent storage file
        
        # Last viewed image tracking
        self.last_image_file = os.path.expanduser("~/.image_viewer_last.json")
        self.last_viewed_image = None
        
        # Crop variables
        self.crop_start_x = None
        self.crop_start_y = None
        self.crop_end_x = None
        self.crop_end_y = None
        self.crop_rect = None
        self.is_cropping = False
        
        # Create main display area
        self.image_frame = tk.Frame(root, bg="black")
        self.image_frame.pack(fill=tk.BOTH, expand=True)
        
        # Background options for transparent images
        self.background_options = {
            "White": "#FFFFFF",
            "Light Gray": "#F0F0F0", 
            "Dark Gray": "#404040",
            "Black": "#000000",
            "Checkered": "checkered"
        }
        self.current_background = "Checkered"  # Default to checkered for best transparency visibility
        self.show_image_border = True  # Show border by default to see image boundaries
        
        # Create canvas for image display
        canvas_bg = "#E0E0E0" if self.current_background == "Checkered" else self.background_options[self.current_background]
        self.canvas = tk.Canvas(self.image_frame, bg=canvas_bg, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Control panel at the bottom
        self.control_panel = tk.Frame(root, height=120)
        self.control_panel.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Create buttons - first row (navigation controls)
        button_frame1 = tk.Frame(self.control_panel)
        button_frame1.pack(fill=tk.X, side=tk.TOP, padx=5, pady=2)
        
        self.prev_button = tk.Button(button_frame1, text="Previous (P/PgUp)", command=self.prev_image)
        self.prev_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.next_button = tk.Button(button_frame1, text="Next (N/PgDn)", command=self.next_image)
        self.next_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.first_button = tk.Button(button_frame1, text="First (H/Home)", command=self.first_image)
        self.first_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.last_button = tk.Button(button_frame1, text="Last (E/End)", command=self.last_image)
        self.last_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.random_button = tk.Button(button_frame1, text="Random: Off (R)", command=self.toggle_random)
        self.random_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.slideshow_button = tk.Button(button_frame1, text="Slideshow (W)", command=self.toggle_slideshow)
        self.slideshow_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.animation_button = tk.Button(button_frame1, text="⏸️ Pause (Space)", command=self.toggle_animation)
        self.animation_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.refresh_button = tk.Button(button_frame1, text="🔄 Refresh (F5)", command=self.refresh_folder)
        self.refresh_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.fullscreen_button = tk.Button(button_frame1, text="Fullscreen (F/F11)", command=self.toggle_fullscreen)
        self.fullscreen_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.hide_toolbar_button = tk.Button(button_frame1, text="👁️ Hide Toolbar (F9)", command=self.toggle_toolbar)
        self.hide_toolbar_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Status label (feedback) - moved to row 1
        self.status_label = tk.Label(button_frame1, text="No folder selected")
        self.status_label.pack(side=tk.RIGHT, padx=10, pady=2)
        
        # Second row (zoom and mode buttons)
        button_frame2 = tk.Frame(self.control_panel)
        button_frame2.pack(fill=tk.X, side=tk.TOP, padx=5, pady=2)
        
        self.delete_button = tk.Button(button_frame2, text="Delete (D/Del)", command=self.delete_image)
        self.delete_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.zoom_out_button = tk.Button(button_frame2, text="Zoom- (-)", command=self.zoom_out)
        self.zoom_out_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.zoom_in_button = tk.Button(button_frame2, text="Zoom+ (+)", command=self.zoom_in)
        self.zoom_in_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.save_zoom_button = tk.Button(button_frame2, text="Save View (S/9)", command=self.save_current_zoom)
        self.save_zoom_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.zoom_reset_button = tk.Button(button_frame2, text="Fit (0)", command=self.reset_zoom)
        self.zoom_reset_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.clear_zoom_button = tk.Button(button_frame2, text="Clear View (8)", command=self.clear_saved_zoom)
        self.clear_zoom_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.crop_button = tk.Button(button_frame2, text="Crop Mode", command=self.toggle_crop_mode)
        self.crop_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.select_folder_button = tk.Button(button_frame2, text="Select Folder", command=self.select_folder)
        self.select_folder_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Add folder navigation buttons to row 2
        self.prev_folder_button = tk.Button(button_frame2, text="◀ Prev Folder (Ctrl+←)", command=self.prev_folder, bg="#e6f3ff")
        self.prev_folder_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.next_folder_button = tk.Button(button_frame2, text="Next Folder ▶ (Ctrl+→)", command=self.next_folder, bg="#e6f3ff")
        self.next_folder_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Add browse in file manager button to row 2
        self.browse_folder_button = tk.Button(button_frame2, text="📁 Browse in Nemo", command=self.browse_in_nemo)
        self.browse_folder_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Add full path label centered in button_frame2
        self.path_label = tk.Label(button_frame2, text="Path: No folder selected", font=("Arial", 12), fg="gray30")
        self.path_label.pack(side=tk.LEFT, expand=True, padx=10, pady=2)
        
        # Store default button colors for resetting later
        self.default_button_bg = self.crop_button.cget("bg")
        
        # Third row (file operations and system buttons)
        button_frame3 = tk.Frame(self.control_panel)
        button_frame3.pack(fill=tk.X, side=tk.TOP, padx=5, pady=2)
        
        # Add exit button at the beginning
        self.exit_button = tk.Button(button_frame3, text="Exit (Q)", command=self.on_close, bg="#ffcccc")
        self.exit_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.move_button = tk.Button(button_frame3, text="Move (V)", command=self.move_image)
        self.move_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.duplicate_button = tk.Button(button_frame3, text="Duplicate (D)", command=self.duplicate_image)
        self.duplicate_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.copy_button = tk.Button(button_frame3, text="Copy (C)", command=self.copy_image)
        self.copy_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Add background selector button
        self.background_button = tk.Button(button_frame3, text=f"🎨 {self.current_background}", command=self.cycle_background)
        self.background_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Add dangerous delete folder button (separated with spacing)
        tk.Frame(button_frame3, width=15).pack(side=tk.LEFT)  # Spacer
        self.delete_folder_button = tk.Button(button_frame3, text="🗑️ Delete Folder (Ctrl+Shift+Del)", 
                                             command=self.delete_images_and_folder, 
                                             bg="#ff9999", fg="black", font=('Arial', 8, 'bold'))
        self.delete_folder_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.remove_dupes_button = tk.Button(button_frame3, text="Remove Dupes", command=self.remove_duplicates)
        self.remove_dupes_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Add exit button at the end too
        self.exit_button2 = tk.Button(button_frame3, text="Exit (Q)", command=self.on_close, bg="#ffcccc")
        self.exit_button2.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Image list and current position
        self.image_files = []
        self.current_index = -1
        self.current_folder = None
        
        # Load folder history
        self.history_file = os.path.expanduser("~/.image_viewer_history")
        self.folder_history = self.load_folder_history()
        
        # Load copy/move destination history
        self.copy_move_history_file = os.path.expanduser("~/.image_viewer_copy_move_history")
        self.copy_move_history = self.load_copy_move_history()
        
        # Load saved zoom preferences
        self.load_zoom_data()
        
        # Load last viewed image
        self.load_last_viewed_image()
        
        # On startup, load last-used folder if available but don't auto-display
        if self.folder_history and os.path.exists(self.folder_history[0]):
            self.status_label.config(text=f"Loading last folder: {os.path.basename(self.folder_history[0])}")
            self.load_images_from_folder(self.folder_history[0], auto_display=False)
        else:
            self.status_label.config(text="No recent folders - Click 'Select Folder' to begin")
        
        # Bind the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Set up key bindings
        self.setup_key_bindings()
        
        # Set up mouse bindings for cropping
        self.setup_mouse_bindings()
        
        # Bind canvas resize to update image display
        self.canvas.bind("<Configure>", self.on_canvas_resize)
    
    def show_temporary_message(self, message, duration=2000, prominent=False):
        """Show a temporary message in the status label that disappears after specified duration (ms)"""
        # Set flag to prevent status updates during temp message
        self.showing_temp_message = True
        
        if prominent:
            # Show prominent overlay message for wrap notifications
            self.show_prominent_message(message, duration)
        else:
            # Regular status bar message
            original_text = self.status_label.cget("text")
            original_bg = self.status_label.cget("bg")
            
            # Show the temporary message with a subtle background
            self.status_label.config(text=message, bg="#e6ffe6")  # Light green background
            
            # Schedule to revert back to original text and background
            def restore_status():
                self.showing_temp_message = False
                self.status_label.config(text=original_text, bg=original_bg)
            
            self.root.after(duration, restore_status)
    
    def show_prominent_message(self, message, duration=2000):
        """Show a prominent overlay message as a temporary popup"""
        # Create a temporary toplevel window
        popup = tk.Toplevel(self.root)
        popup.withdraw()  # Hide initially
        popup.overrideredirect(True)  # Remove window decorations
        popup.configure(bg="#ffeb3b")  # Bright yellow background
        
        # Create label with message
        label = tk.Label(popup, text=message,
                        font=("Arial", 16, "bold"),
                        bg="#ffeb3b", fg="#333333",
                        padx=20, pady=10,
                        relief="raised", borderwidth=2)
        label.pack()
        
        # Position popup in center of main window
        popup.update_idletasks()  # Calculate size
        
        # Get main window position and size
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        # Calculate popup position (bottom right of main window)
        popup_width = popup.winfo_width()
        popup_height = popup.winfo_height()
        x = root_x + root_width - popup_width - 400  # 400px margin from right edge (about 4 inches)
        y = root_y + root_height - popup_height - 200  # 200px margin from bottom edge (about 2 inches up)
        
        popup.geometry(f"+{x}+{y}")
        popup.deiconify()  # Show popup
        popup.lift()  # Bring to front
        popup.attributes('-topmost', True)  # Keep on top
        
        # Schedule removal and reset flag
        def remove_popup():
            try:
                popup.destroy()
            except:
                pass  # Ignore if already destroyed
            self.showing_temp_message = False
        
        self.root.after(duration, remove_popup)
    
    def extract_gif_frames(self, image):
        """Extract all frames and durations from an animated GIF"""
        frames = []
        durations = []
        
        try:
            # Check if image is animated
            if not getattr(image, "is_animated", False):
                return frames, durations
            
            # Extract all frames
            for frame_idx in range(image.n_frames):
                image.seek(frame_idx)
                
                # Get frame duration (in milliseconds)
                duration = image.info.get('duration', 100)  # Default 100ms if not specified
                if duration == 0:
                    duration = 100  # Some GIFs have 0 duration, use default
                
                # Convert to RGBA to handle transparency properly
                frame = image.copy().convert('RGBA')
                frames.append(frame)
                durations.append(duration)
            
            # Reset to first frame
            image.seek(0)
            
        except Exception as e:
            # If there's any error, treat as static image
            pass
        
        return frames, durations
    
    def animate_gif(self):
        """Animate the current GIF by cycling through frames"""
        if not self.is_animated or not self.gif_frames:
            return
        
        try:
            # Get current frame
            current_gif_frame = self.gif_frames[self.current_frame]
            
            # Apply the same zoom and positioning as static images
            self.current_image = current_gif_frame.copy()
            self.apply_zoom_and_display()
            
            # Move to next frame
            self.current_frame = (self.current_frame + 1) % len(self.gif_frames)
            
            # Schedule next frame
            duration = self.gif_durations[self.current_frame] if self.gif_durations else 100
            self.animation_job = self.root.after(duration, self.animate_gif)
            
        except Exception as e:
            # Stop animation on error
            self.stop_animation()
    
    def stop_animation(self):
        """Stop the current GIF animation"""
        if self.animation_job:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
    
    def toggle_animation(self):
        """Pause/resume GIF animation or slideshow"""
        if self.is_slideshow:
            # If slideshow is running, button controls slideshow pause/resume
            self.toggle_slideshow_pause()
            return
        
        # Normal GIF animation control
        if not self.is_animated:
            return
        
        if self.animation_job:
            # Animation is running, pause it
            self.stop_animation()
            self.animation_button.config(text="▶️ Play (Space)", bg="#e6ffe6")
        else:
            # Animation is paused, resume it
            if self.gif_frames:
                self.animate_gif()
                self.animation_button.config(text="⏸️ Pause (Space)", bg=self.default_button_bg)
    
    def setup_key_bindings(self):
        """Set up all keyboard shortcuts"""
        self.root.bind("n", lambda e: self.next_image())               # Next
        self.root.bind("p", lambda e: self.prev_image())               # Previous
        self.root.bind("h", lambda e: self.first_image())              # First (H key)
        self.root.bind("e", lambda e: self.last_image())               # Last (E key)
        self.root.bind("<Home>", lambda e: self.first_image())         # First (Home key)
        self.root.bind("<End>", lambda e: self.last_image())           # Last (End key)
        self.root.bind("<Next>", lambda e: self.next_image())          # Next (Page Down)
        self.root.bind("<Prior>", lambda e: self.prev_image())         # Previous (Page Up)
        self.root.bind("f", lambda e: self.toggle_fullscreen())        # Fullscreen toggle
        self.root.bind("<F5>", lambda e: self.refresh_folder())        # Refresh folder
        self.root.bind("<F9>", lambda e: self.toggle_toolbar())        # Toggle toolbar visibility
        self.root.bind("s", lambda e: self.save_current_zoom())        # Save view (S key)
        self.root.bind("r", lambda e: self.toggle_random())            # Random mode
        self.root.bind("q", lambda e: self.on_close())                 # Exit
        self.root.bind("d", lambda e: self.delete_image())             # Delete
        self.root.bind("<Delete>", lambda e: self.delete_image())      # Delete
        self.root.bind("<Control-Shift-Delete>", lambda e: self.delete_images_and_folder())  # Delete all images & folder (dangerous!)
        self.root.bind("b", lambda e: self.browse_in_nemo())           # Browse in Nemo
        self.root.bind("g", lambda e: self.cycle_background())         # Change background
        self.root.bind("o", lambda e: self.toggle_border())            # Toggle border (O for outline)
        self.root.bind("c", lambda e: self.copy_image())               # Copy
        self.root.bind("d", lambda e: self.duplicate_image())          # Duplicate
        self.root.bind("v", lambda e: self.move_image())               # Move
        self.root.bind("w", lambda e: self.toggle_slideshow())         # Slideshow
        self.root.bind("<KeyPress-plus>", lambda e: self.zoom_in())    # Zoom in (+)
        self.root.bind("<KeyPress-equal>", lambda e: self.zoom_in())   # Zoom in (= key without shift)
        self.root.bind("<KeyPress-minus>", lambda e: self.zoom_out())  # Zoom out (-)
        self.root.bind("<KeyPress-0>", lambda e: self.reset_zoom())    # Reset zoom (0)
        self.root.bind("<KeyPress-9>", lambda e: self.save_current_zoom())    # Save zoom (9)
        self.root.bind("<KeyPress-8>", lambda e: self.clear_saved_zoom())     # Clear saved zoom (8)
        self.root.bind("<space>", lambda e: self.handle_space_key())   # Smart space handler for slideshow/animation
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())    # Fullscreen (F11)
        self.root.bind("<Escape>", lambda e: self.exit_fullscreen())   # Exit fullscreen
        self.root.bind("<Control-Left>", lambda e: self.prev_folder()) # Previous folder (Ctrl+Left)
        self.root.bind("<Control-Right>", lambda e: self.next_folder()) # Next folder (Ctrl+Right)
        
        # Arrow key panning (pan image view)
        self.root.bind("<Left>", lambda e: self.pan_with_keys(-20, 0))   # Pan left
        self.root.bind("<Right>", lambda e: self.pan_with_keys(20, 0))   # Pan right
        self.root.bind("<Up>", lambda e: self.pan_with_keys(0, 20))      # Move image down
        self.root.bind("<Down>", lambda e: self.pan_with_keys(0, -20))   # Move image up
        
        # Enable focus so key bindings work
        self.root.focus_set()
    
    def setup_mouse_bindings(self):
        """Set up mouse bindings for panning and cropping"""
        self.canvas.bind("<Button-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
    
    def on_mouse_press(self, event):
        """Handle mouse press for both panning and cropping"""
        if not self.current_image:
            return
            
        # Check for double-click
        current_time = time.time() * 1000  # milliseconds
        if current_time - self.last_click_time < self.double_click_threshold:
            # Double-click detected
            self.toggle_toolbar()
            self.last_click_time = 0  # Reset
            return
        
        # Single click
        self.last_click_time = current_time
        
        if self.is_cropping:
            # Crop mode: start crop selection
            self.start_crop(event)
        else:
            # Pan mode: start panning
            self.start_pan(event)
    
    def on_mouse_drag(self, event):
        """Handle mouse drag for both panning and cropping"""
        if not self.current_image:
            return
            
        if self.is_cropping:
            # Crop mode: update crop selection
            self.update_crop(event)
        else:
            # Pan mode: update pan position
            self.update_pan(event)
    
    def on_mouse_release(self, event):
        """Handle mouse release for both panning and cropping"""
        if not self.current_image:
            return
            
        if self.is_cropping:
            # Crop mode: end crop selection
            self.end_crop(event)
        else:
            # Pan mode: end panning
            self.end_pan(event)
    
    def start_pan(self, event):
        """Start panning the image"""
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor="fleur")  # Change cursor to indicate panning
    
    def update_pan(self, event):
        """Update image position during panning"""
        if not self.is_panning:
            return
            
        # Calculate movement delta
        delta_x = event.x - self.pan_start_x
        delta_y = event.y - self.pan_start_y
        
        # Update image offset
        self.image_offset_x += delta_x
        self.image_offset_y += delta_y
        
        # Update start position for next delta
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        
        # Redraw image with new position
        self.apply_zoom_and_display()
    
    def end_pan(self, event):
        """End panning the image"""
        self.is_panning = False
        self.canvas.config(cursor="")  # Reset cursor
    
    def pan_with_keys(self, delta_x, delta_y):
        """Pan the image using keyboard arrow keys"""
        if not self.current_image:
            return
            
        # Update image offset
        self.image_offset_x += delta_x
        self.image_offset_y += delta_y
        
        # Redraw image with new position
        self.apply_zoom_and_display()
    
    def on_canvas_resize(self, event):
        """Handle canvas resize events"""
        if self.current_image and not self.is_slideshow:
            self.display_current_image()
    
    def load_folder_history(self):
        """Load folder history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return [line.strip() for line in f.readlines() if line.strip()]
        except:
            pass
        return []
    
    def save_folder_history(self):
        """Save folder history to file"""
        try:
            with open(self.history_file, 'w') as f:
                for folder in self.folder_history:
                    f.write(folder + '\n')
        except:
            pass
    
    def add_to_history(self, folder_path):
        """Add folder to history, moving it to top if it exists"""
        if folder_path in self.folder_history:
            self.folder_history.remove(folder_path)
        self.folder_history.insert(0, folder_path)
        # Keep only last 10 folders
        self.folder_history = self.folder_history[:10]
        self.save_folder_history()
    
    def load_zoom_data(self):
        """Load saved zoom preferences from file"""
        try:
            if os.path.exists(self.zoom_settings_file):
                with open(self.zoom_settings_file, 'r') as f:
                    self.image_zoom_memory = json.load(f)
        except Exception as e:
            print(f"Could not load zoom data: {e}")
            self.image_zoom_memory = {}
    
    def save_zoom_data(self):
        """Save current zoom preferences to file"""
        try:
            with open(self.zoom_settings_file, 'w') as f:
                json.dump(self.image_zoom_memory, f, indent=2)
        except Exception as e:
            print(f"Could not save zoom data: {e}")
    
    def load_last_viewed_image(self):
        """Load the last viewed image from file"""
        try:
            if os.path.exists(self.last_image_file):
                with open(self.last_image_file, 'r') as f:
                    data = json.load(f)
                    self.last_viewed_image = data.get('last_image', None)
        except Exception as e:
            print(f"Could not load last viewed image: {e}")
            self.last_viewed_image = None
    
    def save_last_viewed_image(self):
        """Save the current image as the last viewed image"""
        if self.image_files and self.current_index >= 0:
            try:
                current_image_path = self.image_files[self.current_index]
                data = {'last_image': current_image_path}
                with open(self.last_image_file, 'w') as f:
                    json.dump(data, f, indent=2)
                self.last_viewed_image = current_image_path
            except Exception as e:
                print(f"Could not save last viewed image: {e}")
    
    def select_folder(self):
        """Show folder selection dialog with history"""
        if self.folder_history:
            # Create a popup menu for folder selection
            choice_window = tk.Toplevel(self.root)
            choice_window.title("Select Folder")
            choice_window.geometry("500x300")
            choice_window.transient(self.root)
            choice_window.grab_set()
            
            tk.Label(choice_window, text="Recent folders:", font=("Arial", 12, "bold")).pack(pady=5)
            
            # Create listbox for history
            listbox_frame = tk.Frame(choice_window)
            listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            scrollbar = tk.Scrollbar(listbox_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.history_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
            self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=self.history_listbox.yview)
            
            # Populate listbox with history
            for folder in self.folder_history:
                if os.path.exists(folder):  # Only show existing folders
                    self.history_listbox.insert(tk.END, folder)
            
            # Button frame
            button_frame = tk.Frame(choice_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)
            
            def use_selected():
                selection = self.history_listbox.curselection()
                if selection:
                    folder_path = self.history_listbox.get(selection[0])
                    choice_window.destroy()
                    self.add_to_history(folder_path)
                    self.load_images_from_folder(folder_path)
            
            def browse_new():
                choice_window.destroy()
                self.browse_for_folder()
            
            tk.Button(button_frame, text="Use Selected", command=use_selected).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Browse New Folder", command=browse_new).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Cancel", command=choice_window.destroy).pack(side=tk.RIGHT, padx=5)
            
            # Double-click to select
            self.history_listbox.bind("<Double-Button-1>", lambda e: use_selected())
        else:
            # No history, go straight to browser
            self.browse_for_folder()
    
    def browse_for_folder(self):
        """Browse for a new folder"""
        # Set initial directory to last used folder if available
        initial_dir = self.folder_history[0] if self.folder_history else None
        if initial_dir and not os.path.exists(initial_dir):
            initial_dir = os.path.dirname(initial_dir) if initial_dir else None
        
        folder_path = filedialog.askdirectory(
            title="Select Folder Containing Images",
            initialdir=initial_dir,
            mustexist=True
        )
        
        if folder_path:
            self.add_to_history(folder_path)
            self.load_images_from_folder(folder_path)
    
    def browse_in_nemo(self):
        """Open the current folder in Nemo file manager"""
        if not hasattr(self, 'current_folder') or not self.current_folder:
            self.show_temporary_message("No folder loaded", 2000)
            return
        
        if not os.path.exists(self.current_folder):
            self.show_temporary_message("Current folder no longer exists", 2000)
            return
        
        try:
            # Try to open with Nemo file manager
            subprocess.run(['nemo', self.current_folder], check=False)
            self.show_temporary_message(f"Opened folder in Nemo", 1500)
        except FileNotFoundError:
            try:
                # Fallback to default file manager if Nemo is not available
                subprocess.run(['xdg-open', self.current_folder], check=False)
                self.show_temporary_message(f"Opened folder in file manager", 1500)
            except Exception as e:
                self.show_temporary_message(f"Failed to open folder: {str(e)}", 3000)
    
    def load_images_from_folder(self, folder_path, auto_display=True):
        """Load all image files from the specified folder"""
        # Store the current folder for reference
        self.current_folder = folder_path
        
        # Update path label with full folder path
        self.path_label.config(text=f"Path: {folder_path}")
        
        # Common image file extensions (including .enc for encrypted/renamed images)
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.enc')
        
        # Get all image files (skip dot files)
        self.image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                           if os.path.isfile(os.path.join(folder_path, f)) and 
                           not f.startswith('.') and
                           f.lower().endswith(image_extensions)]
        
        if not self.image_files:
            self.status_label.config(text="No image files found in folder")
            # Still show path even if no images found
            self.path_label.config(text=f"Path: {folder_path}")
            return
        
        # Sort files naturally
        self.image_files.sort()
        
        # Set initial index - try to find last viewed image first
        start_index = 0
        if self.last_viewed_image and self.last_viewed_image in self.image_files:
            try:
                start_index = self.image_files.index(self.last_viewed_image)
            except ValueError:
                start_index = 0
        
        if auto_display:
            self.current_index = start_index
            self.status_label.config(text=f"Found {len(self.image_files)} images")
            self.display_current_image()
        else:
            # Position to one BEFORE the last viewed image, so Next goes to last viewed
            if self.last_viewed_image and self.last_viewed_image in self.image_files:
                self.current_index = start_index - 1  # So first "Next" will go to last viewed image
                self.status_label.config(text=f"Found {len(self.image_files)} images - Next will show last viewed image")
            else:
                self.current_index = -1  # So first "Next" will go to index 0
                self.status_label.config(text=f"Found {len(self.image_files)} images - Press N/P or use buttons to navigate")
    
    def refresh_folder(self):
        """Refresh the current folder to pick up any new images"""
        if not hasattr(self, 'current_folder') or not self.current_folder:
            messagebox.showinfo("No Folder", "No folder currently loaded. Please select a folder first.")
            return
        
        if not os.path.exists(self.current_folder):
            messagebox.showerror("Folder Not Found", f"Current folder no longer exists:\n{self.current_folder}")
            return
        
        # Remember current image if any
        current_image_path = None
        if self.image_files and 0 <= self.current_index < len(self.image_files):
            current_image_path = self.image_files[self.current_index]
        
        # Store old count for comparison
        old_count = len(self.image_files) if self.image_files else 0
        
        # Reload the folder
        self.load_images_from_folder(self.current_folder, auto_display=False)
        
        # Try to maintain position at the same image
        if current_image_path and current_image_path in self.image_files:
            self.current_index = self.image_files.index(current_image_path)
            self.display_current_image()
        elif self.image_files:
            # If current image no longer exists, go to first image
            self.current_index = 0
            self.display_current_image()
        
        # Show refresh status
        new_count = len(self.image_files) if self.image_files else 0
        if new_count > old_count:
            self.status_label.config(text=f"Refreshed! Found {new_count - old_count} new images ({new_count} total)")
        elif new_count < old_count:
            self.status_label.config(text=f"Refreshed! {old_count - new_count} images removed ({new_count} total)")
        else:
            self.status_label.config(text=f"Refreshed! No changes ({new_count} images)")
    
    def display_current_image(self):
        """Display the current image on the canvas"""
        if not self.image_files or self.current_index < 0 or self.current_index >= len(self.image_files):
            return
        
        try:
            # Stop any existing animation
            self.stop_animation()
            
            # Get the current image file
            image_path = self.image_files[self.current_index]
            
            # Validate file path and existence
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"File not found: {image_path}")
            
            # Check file size and readability
            try:
                file_size = os.path.getsize(image_path)
                if file_size == 0:
                    raise ValueError(f"File is empty: {image_path}")
            except OSError as e:
                raise ValueError(f"Cannot access file: {image_path} - {str(e)}")
            
            # Update the window title with the filename
            filename = os.path.basename(image_path)
            self.root.title(f"Image Viewer - {filename}")
            
            # Try to load the image with forgiving error handling
            try:
                self.original_image = Image.open(image_path)
                # Don't use verify() as it's too strict - just try to load the image data
                # This allows partially corrupted images to be displayed
                try:
                    # Try to load the image data to ensure it's at least partially readable
                    self.original_image.load()
                except Exception as load_error:
                    # If load fails, still try to proceed - the image might be partially viewable
                    print(f"Warning: Image may be partially corrupted: {filename} - {load_error}")
                    # Re-open the image since load() might have corrupted the state
                    self.original_image = Image.open(image_path)
            except Exception as pil_error:
                # Only fail if we absolutely cannot open the image at all
                pil_error_str = str(pil_error).replace(image_path, f"'{filename}'")
                raise ValueError(f"Cannot open image '{filename}': {pil_error_str}. "
                               f"File size: {file_size} bytes. "
                               f"This file appears to be completely unreadable.")
            
            # Check if this is an animated GIF
            self.is_animated = getattr(self.original_image, "is_animated", False)
            
            if self.is_animated:
                # Extract all frames for animation
                self.gif_frames, self.gif_durations = self.extract_gif_frames(self.original_image)
                self.current_frame = 0
                
                if self.gif_frames:
                    # Use the first frame as the base image
                    self.current_image = self.gif_frames[0].copy()
                else:
                    # Fallback to static display if frame extraction failed
                    self.is_animated = False
                    self.current_image = self.original_image.copy()
            else:
                # Static image
                self.current_image = self.original_image.copy()
                self.gif_frames = []
                self.gif_durations = []
            
            # Load saved zoom and position for this image or use defaults
            self.zoom_level, self.image_offset_x, self.image_offset_y = self.load_saved_zoom_and_position()
            
            # Apply zoom and fit to canvas
            self.apply_zoom_and_display()
            
            # Save this image as the last viewed image
            self.save_last_viewed_image()
            
            # Update animation button visibility and state
            if self.is_slideshow:
                # During slideshow, pause button controls slideshow pause
                if self.slideshow_paused:
                    self.animation_button.config(text="▶️ Resume (Space)", bg="#e6ffe6", state='normal')
                else:
                    self.animation_button.config(text="⏸️ Pause (Space)", bg=self.default_button_bg, state='normal')
            elif self.is_animated and self.gif_frames:
                self.animation_button.config(text="⏸️ Pause (Space)", bg=self.default_button_bg, state='normal')
                self.animate_gif()
            else:
                self.animation_button.config(text="⏸️ Pause (Space)", bg=self.default_button_bg, state='disabled')
            
            # Update status - clean and consistent format with folder path
            folder_name = os.path.basename(self.current_folder) if self.current_folder else "No folder"
            status_text = f"[{folder_name}] Image {self.current_index+1} of {len(self.image_files)}"
            
            # Add animation indicator
            if self.is_animated:
                frame_count = len(self.gif_frames) if self.gif_frames else 0
                status_text += f" • Animated GIF ({frame_count} frames)"
            
            # Only update status if not showing a temporary message
            if not self.showing_temp_message:
                self.status_label.config(text=status_text)
            
        except Exception as e:
            # Automatically try to force display the corrupted image
            filename = os.path.basename(self.image_files[self.current_index]) if self.image_files else "unknown"
            
            # First attempt: try to force display the corrupted image
            if self.force_display_corrupted_image(image_path, filename, silent=True):
                # Successfully displayed corrupted image
                return
            
            # If force display also failed, silently skip to next image
            if len(self.image_files) > 1:
                # Remove problematic image from the list and skip to next
                problematic_file = self.image_files[self.current_index]
                self.image_files.remove(problematic_file)
                
                # Adjust current index if needed
                if self.current_index >= len(self.image_files):
                    self.current_index = 0
                
                # Try to display the next image
                self.display_current_image()
                self.show_temporary_message(f"Skipped unreadable image: {filename}", 2000)
            else:
                # Only one image in folder - show error in status
                error_msg = f"Cannot load the only image: {filename}"
                if not self.showing_temp_message:
                    self.status_label.config(text=error_msg)
    
    def show_corrupted_image_dialog(self, filename, error_message):
        """Show custom dialog for handling corrupted images with Skip/Delete/Cancel options"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Image Loading Error")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        result = {"action": "cancel"}
        
        # Main message
        message_frame = tk.Frame(dialog)
        message_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(message_frame, text=f"Failed to load: {filename}", 
                font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        tk.Label(message_frame, text=f"Error: {error_message}", 
                wraplength=350, justify=tk.LEFT).pack(pady=(0, 10))
        
        tk.Label(message_frame, text="This file may be corrupted or in an unsupported format.", 
                wraplength=350, justify=tk.LEFT).pack(pady=(0, 20))
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
        
        def on_skip():
            result["action"] = "skip"
            dialog.destroy()
            
        def on_delete():
            result["action"] = "delete"
            dialog.destroy()
            
        def on_try_anyway():
            result["action"] = "try_anyway"
            dialog.destroy()
        
        def on_cancel():
            result["action"] = "cancel"
            dialog.destroy()
        
        # Button layout
        tk.Button(button_frame, text="Try Anyway", command=on_try_anyway, 
                 bg="#ffffcc", width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Skip", command=on_skip, 
                 bg="#e6f3ff", width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Delete", command=on_delete, 
                 bg="#ffcccc", width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Cancel", command=on_cancel, 
                 bg="#f0f0f0", width=10).pack(side=tk.RIGHT, padx=2)
        
        # Handle window close button
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        
        # Make dialog modal and wait for result
        dialog.wait_window()
        
        return result["action"]
    
    def force_display_corrupted_image(self, image_path, filename, silent=False):
        """Attempt to display a corrupted image using minimal error checking"""
        try:
            # Try multiple approaches to load the corrupted image
            success = False
            
            # Approach 1: Basic PIL open with no verification
            try:
                self.original_image = Image.open(image_path)
                self.current_image = self.original_image.copy()
                success = True
            except:
                pass
            
            # Approach 2: Try converting to RGB if initial load fails
            if not success:
                try:
                    img = Image.open(image_path)
                    self.original_image = img.convert('RGB')
                    self.current_image = self.original_image.copy()
                    success = True
                except:
                    pass
            
            # Approach 3: Try loading with different modes
            if not success:
                for mode in ['RGB', 'RGBA', 'L', 'P']:
                    try:
                        img = Image.open(image_path)
                        self.original_image = img.convert(mode)
                        self.current_image = self.original_image.copy()
                        success = True
                        break
                    except:
                        continue
            
            if success:
                # Set up for display
                self.is_animated = False
                self.gif_frames = []
                self.gif_durations = []
                
                # Load saved zoom and position or use defaults
                self.zoom_level, self.image_offset_x, self.image_offset_y = self.load_saved_zoom_and_position()
                
                # Save this as last viewed and display
                self.save_last_viewed_image()
                self.apply_zoom_and_display()
                
                # Update status and UI
                if self.is_slideshow:
                    # During slideshow, pause button controls slideshow pause
                    if self.slideshow_paused:
                        self.animation_button.config(text="▶️ Resume (Space)", bg="#e6ffe6", state='normal')
                    else:
                        self.animation_button.config(text="⏸️ Pause (Space)", bg=self.default_button_bg, state='normal')
                else:
                    self.animation_button.config(text="⏸️ Pause (Space)", bg=self.default_button_bg, state='disabled')
                status_text = f"Image {self.current_index+1} of {len(self.image_files)} (Corrupted - Partial Display)"
                if not self.showing_temp_message:
                    self.status_label.config(text=status_text)
                
                if not silent:
                    self.show_temporary_message(f"Displaying corrupted image: {filename}", 3000)
                
                return True
            else:
                # All approaches failed
                if not silent:
                    messagebox.showerror("Cannot Display", 
                                       f"Unable to display {filename} even with forced loading. "
                                       f"The file appears to be completely corrupted.")
                return False
                
        except Exception as e:
            if not silent:
                messagebox.showerror("Force Display Failed", 
                                   f"Failed to force display {filename}: {str(e)}")
            return False
    
    def apply_zoom_and_display(self):
        """Apply current zoom level and display the image"""
        if not self.current_image:
            return
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready yet
            self.root.after(100, self.apply_zoom_and_display)
            return
        
        # Calculate base size (fit to window)
        img_width, img_height = self.current_image.size
        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        base_scale = min(scale_w, scale_h)
        
        # Apply zoom level to the base scale
        final_scale = base_scale * self.zoom_level
        display_width = int(img_width * final_scale)
        display_height = int(img_height * final_scale)
        
        # Resize image
        if display_width > 0 and display_height > 0:
            display_image = self.current_image.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            # Handle transparency properly based on selected background
            if display_image.mode in ('RGBA', 'LA') or (display_image.mode == 'P' and 'transparency' in display_image.info):
                if self.current_background == "Checkered":
                    # Create checkered background
                    background = self.create_checkered_image(display_image.size)
                else:
                    # Create solid color background
                    bg_color = self.background_options[self.current_background]
                    # Convert hex color to RGB tuple
                    bg_rgb = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5))
                    background = Image.new('RGB', display_image.size, bg_rgb)
                
                if display_image.mode == 'P':
                    display_image = display_image.convert('RGBA')
                background.paste(display_image, mask=display_image.split()[-1] if display_image.mode in ('RGBA', 'LA') else None)
                display_image = background
            elif display_image.mode != 'RGB':
                # Convert other modes to RGB for consistent display
                display_image = display_image.convert('RGB')
                
            self.current_photo = ImageTk.PhotoImage(display_image)
            
            # Clear canvas and display image
            self.canvas.delete("all")
            
            # Calculate position with panning offset
            base_x = (canvas_width - display_width) // 2
            base_y = (canvas_height - display_height) // 2
            x = base_x + self.image_offset_x
            y = base_y + self.image_offset_y
            
            # Create a subtle border around the image to show boundaries (if enabled)
            if self.show_image_border:
                # Choose border color that contrasts with current background
                if self.current_background in ["White", "Light Gray"]:
                    border_color = "#808080"  # Medium gray for light backgrounds
                elif self.current_background == "Checkered":
                    border_color = "#606060"  # Darker gray for checkered
                else:  # Dark Gray, Black
                    border_color = "#C0C0C0"  # Light gray for dark backgrounds
                    
                border_width = 1
                self.canvas.create_rectangle(
                    x - border_width, y - border_width,
                    x + display_width + border_width, y + display_height + border_width,
                    outline=border_color, width=1, fill=""
                )
            
            self.canvas.create_image(x, y, anchor=tk.NW, image=self.current_photo)
            
            # Store image position for cropping and panning
            self.image_x = x
            self.image_y = y
            self.image_width = display_width
            self.image_height = display_height
    
    def next_image(self):
        """Navigate to the next image"""
        if not self.image_files:
            return
        
        if self.is_random:
            self.random_image()
        else:
            old_index = self.current_index
            
            # If we're at -1 or negative (no image selected yet), handle specially
            if self.current_index < 0:
                if self.last_viewed_image and self.last_viewed_image in self.image_files:
                    try:
                        self.current_index = self.image_files.index(self.last_viewed_image)
                    except ValueError:
                        self.current_index = 0
                else:
                    self.current_index = 0
                self.display_current_image()
                return
            
            self.current_index = (self.current_index + 1) % len(self.image_files)
            
            # Show message when wrapping from last to first image
            if old_index == len(self.image_files) - 1 and self.current_index == 0:
                self.show_temporary_message("🔄 Wrapped to first image", 1000, prominent=True)
                # Delay display update to show message first
                self.root.after(10, self.display_current_image)
            else:
                self.display_current_image()
    
    def prev_image(self):
        """Navigate to the previous image"""
        if not self.image_files:
            return
        
        if self.is_random:
            self.random_image()
        else:
            old_index = self.current_index
            self.current_index = (self.current_index - 1) % len(self.image_files)
            
            # Show message when wrapping from first to last image
            if old_index == 0 and self.current_index == len(self.image_files) - 1:
                self.show_temporary_message("🔄 Wrapped to last image", 1000, prominent=True)
                # Delay display update to show message first
                self.root.after(10, self.display_current_image)
            else:
                self.display_current_image()
    
    def first_image(self):
        """Navigate to the first image"""
        if not self.image_files:
            return
        
        self.current_index = 0
        self.display_current_image()
    
    def last_image(self):
        """Navigate to the last image"""
        if not self.image_files:
            return
        
        self.current_index = len(self.image_files) - 1
        self.display_current_image()
    
    def random_image(self):
        """Navigate to a random image"""
        if not self.image_files or len(self.image_files) <= 1:
            return
        
        # Get a random index that's different from current
        available_indices = [i for i in range(len(self.image_files)) if i != self.current_index]
        if available_indices:
            self.current_index = random.choice(available_indices)
            self.display_current_image()
    
    def toggle_random(self):
        """Toggle random mode on/off"""
        self.is_random = not self.is_random
        self.random_button.config(text=f"Random: {'On' if self.is_random else 'Off'} (R)")
    
    def delete_image(self):
        """Delete the current image to trash"""
        if not self.image_files or self.current_index < 0 or self.current_index >= len(self.image_files):
            return
        
        # Get the current image file
        image_path = self.image_files[self.current_index]
        filename = os.path.basename(image_path)
        
        # Delete immediately without confirmation
        try:
            # Try to use send2trash if available, otherwise fallback to system trash
            try:
                send2trash(image_path)
                self.status_label.config(text=f"Moved '{filename}' to trash")
            except:
                # Fallback: try to move to system trash manually
                import subprocess
                if sys.platform.startswith('linux'):
                    subprocess.run(['gio', 'trash', image_path], check=True)
                else:
                    # For other platforms, just delete permanently as fallback
                    os.remove(image_path)
                self.status_label.config(text=f"Deleted '{filename}'")
            
            # Remove from our list
            del self.image_files[self.current_index]
            
            # Move to next image or update UI
            if self.image_files:
                if self.current_index >= len(self.image_files):
                    self.current_index = len(self.image_files) - 1
                self.display_current_image()
            else:
                self.canvas.delete("all")
                self.status_label.config(text="No images left in folder")
                self.root.title("Image Viewer")
                
        except Exception as e:
            messagebox.showerror("Delete Error", f"Could not delete image: {str(e)}")
            self.status_label.config(text=f"Delete failed: {str(e)}")
    
    def remove_duplicates(self):
        """Remove duplicate images from the current folder using fdupes"""
        if not self.image_files:
            messagebox.showwarning("No Folder", "No images loaded. Please select a folder first.")
            return
        
        # Get the current folder
        current_folder = os.path.dirname(self.image_files[0])
        
        # Ask for confirmation
        result = messagebox.askyesno(
            "Remove Duplicates", 
            f"This will scan for and remove duplicate images in:\n{current_folder}\n\n"
            "This action cannot be undone. Continue?"
        )
        
        if not result:
            return
        
        # Immediately show button as activated after confirmation
        self.remove_dupes_button.config(state="disabled", text="Working...", bg="#ffffcc")
        self.status_label.config(text="Scanning for duplicates... Please wait...")
        self.root.update()
        
        try:
            import subprocess
            
            # Check if fdupes is installed
            try:
                subprocess.run(['fdupes', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                messagebox.showerror(
                    "Missing Tool", 
                    "fdupes is not installed.\n\nInstall it with:\nsudo apt install fdupes"
                )
                return
            
            # Run fdupes command (recursive, delete duplicates, no prompts)
            result = subprocess.run(
                ['fdupes', '-rdN', current_folder], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                # Reload the folder to update the file list
                old_count = len(self.image_files)
                self.load_images_from_folder(current_folder, auto_display=False)
                new_count = len(self.image_files)
                removed_count = old_count - new_count
                
                if removed_count > 0:
                    # Show temporary success message
                    success_msg = f"✓ Removed {removed_count} duplicate image{'s' if removed_count != 1 else ''} ({old_count} → {new_count} images)"
                    self.show_temporary_message(success_msg, 4000)  # Show for 4 seconds
                    
                    # If current image was deleted, reset to first image
                    if self.current_index >= len(self.image_files):
                        self.current_index = 0
                        if self.image_files:
                            self.display_current_image()
                else:
                    # Show temporary info message
                    info_msg = f"No duplicates found ({new_count} images total)"
                    self.show_temporary_message(info_msg, 3000)  # Show for 3 seconds
            else:
                error_msg = result.stderr or "Unknown error occurred"
                messagebox.showerror("Duplicate Removal Failed", f"fdupes error:\n{error_msg}")
                self.status_label.config(text="Duplicate removal failed")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove duplicates: {str(e)}")
            self.status_label.config(text=f"Error: {str(e)}")
        
        finally:
            # Re-enable button and restore normal color
            self.remove_dupes_button.config(state="normal", text="Remove Dupes", bg=self.default_button_bg)
    
    def load_copy_move_history(self):
        """Load copy/move destination folder history"""
        try:
            if os.path.exists(self.copy_move_history_file):
                with open(self.copy_move_history_file, 'r') as f:
                    return [line.strip() for line in f.readlines() if line.strip()]
            return []
        except:
            return []
    
    def save_copy_move_history(self):
        """Save copy/move destination folder history"""
        try:
            with open(self.copy_move_history_file, 'w') as f:
                for folder in self.copy_move_history[:10]:  # Keep only last 10
                    f.write(folder + '\n')
        except:
            pass
    
    def add_to_copy_move_history(self, folder_path):
        """Add folder to copy/move history"""
        if folder_path in self.copy_move_history:
            self.copy_move_history.remove(folder_path)
        self.copy_move_history.insert(0, folder_path)
        self.copy_move_history = self.copy_move_history[:10]  # Keep only last 10
        self.save_copy_move_history()
    
    def select_destination_folder(self, operation_name):
        """Select destination folder with history menu"""
        if not self.image_files or self.current_index < 0:
            messagebox.showwarning("No Image", "No image selected to copy/move.")
            return None
        
        # Create a custom dialog with history
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Select Destination - {operation_name}")
        dialog.transient(self.root)
        
        # Hide dialog initially to prevent positioning flash
        dialog.withdraw()
        
        # Calculate center position first, then set geometry once
        dialog.update_idletasks()
        width, height = 650, 500  # Increased size to accommodate larger fonts and spacing
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Allow resizing in case content still doesn't fit
        dialog.resizable(True, True)
        dialog.minsize(600, 450)  # Set minimum size to ensure content is always visible
        
        # Show dialog at correct position and grab focus
        dialog.deiconify()
        dialog.grab_set()
        
        selected_folder = None
        
        # Define functions that will be used throughout the dialog
        def use_selected_history():
            nonlocal selected_folder
            if self.copy_move_history:
                # If listbox exists and has selection, use it; otherwise use most recent (first item)
                if hasattr(use_selected_history, 'listbox_ref') and use_selected_history.listbox_ref:
                    selection = use_selected_history.listbox_ref.curselection()
                    if selection:
                        selected_folder = self.copy_move_history[selection[0]]
                    else:
                        selected_folder = self.copy_move_history[0]  # Default to most recent
                else:
                    selected_folder = self.copy_move_history[0]  # Default to most recent
                dialog.destroy()
        
        def browse_new_folder():
            nonlocal selected_folder
            folder = filedialog.askdirectory(title=f"Select destination folder for {operation_name.lower()}")
            if folder:
                selected_folder = folder
            dialog.destroy()
        
        def cancel_selection():
            dialog.destroy()
        
        # Instructions with consistent spacing
        tk.Label(dialog, text=f"Choose destination folder for {operation_name.lower()}:", font=('Arial', 10, 'bold')).pack(pady=(10, 8))
        
        # Recent folders frame
        if self.copy_move_history:
            tk.Label(dialog, text="Recent destinations:", font=('Arial', 9)).pack(anchor=tk.W, padx=10)
            
            history_frame = tk.Frame(dialog)
            history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Scrollable listbox for history
            scrollbar = tk.Scrollbar(history_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            history_listbox = tk.Listbox(history_frame, yscrollcommand=scrollbar.set, height=8)  # Limit height to 8 items
            for folder in self.copy_move_history:
                history_listbox.insert(tk.END, folder)
            history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=history_listbox.yview)
            
            # Store reference to listbox for the function
            use_selected_history.listbox_ref = history_listbox
            
            # Automatically select the most recent folder (first item)
            if self.copy_move_history:
                history_listbox.selection_set(0)
                history_listbox.activate(0)
                history_listbox.focus_set()
            
            # Bind keys for better navigation
            def on_listbox_key(event):
                if event.keysym == 'Return':
                    use_selected_history()
                elif event.keysym == 'Escape':
                    cancel_selection()
            
            history_listbox.bind("<Return>", on_listbox_key)
            history_listbox.bind("<Escape>", on_listbox_key)
            history_listbox.bind("<Double-Button-1>", lambda e: use_selected_history())  # Double-click also works
            
            # Button for using selected history folder with balanced spacing
            history_button_frame = tk.Frame(dialog)
            history_button_frame.pack(pady=(6, 4))
            tk.Button(history_button_frame, text="Use Selected Folder (Enter)", command=use_selected_history, 
                     bg="#e6ffe6", font=('Arial', 11, 'bold'), padx=25, pady=6).pack(pady=6)
            
            # Separator with balanced spacing
            tk.Frame(dialog, height=2, bg='gray').pack(fill=tk.X, padx=20, pady=(8, 12))
        else:
            # No history available
            use_selected_history.listbox_ref = None  # No listbox when no history
            tk.Label(dialog, text="No recent destinations available.", font=('Arial', 10), fg='gray').pack(pady=20)
        
        # Label for alternative option with balanced spacing
        tk.Label(dialog, text="Or choose a different folder:", font=('Arial', 10)).pack(pady=(12, 8))
        
        # Main action buttons frame with balanced spacing
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=(5, 15))
        
        # Make the browse button more prominent with larger font and balanced spacing
        browse_button = tk.Button(button_frame, text="Browse for New Folder...", command=browse_new_folder,
                                 bg="#ffffcc", font=('Arial', 11, 'bold'), padx=25, pady=6)
        browse_button.pack(side=tk.LEFT, padx=15)
        
        cancel_button = tk.Button(button_frame, text="Cancel (Esc)", command=cancel_selection,
                                 bg="#ffcccc", font=('Arial', 11), padx=25, pady=6)
        cancel_button.pack(side=tk.LEFT, padx=15)
        
        # Add global keyboard bindings for the dialog
        def on_dialog_key(event):
            if event.keysym == 'Return':
                if self.copy_move_history:
                    use_selected_history()
                else:
                    # If no history, Enter key opens browse dialog
                    browse_new_folder()
            elif event.keysym == 'Escape':
                cancel_selection()
        
        # Bind keys to both the dialog and the buttons for better responsiveness
        dialog.bind('<Key>', on_dialog_key)
        dialog.bind('<Return>', lambda e: on_dialog_key(e))
        dialog.bind('<Escape>', lambda e: cancel_selection())
        
        # Also bind to buttons for focus-based keyboard navigation
        browse_button.bind('<Return>', lambda e: browse_new_folder())
        cancel_button.bind('<Return>', lambda e: cancel_selection())
        
        # Set initial focus appropriately
        if self.copy_move_history:
            # If there's history, focus on the listbox so arrow keys work immediately
            history_listbox.focus_set()
        else:
            # If no history, focus on the browse button
            browse_button.focus_set()
        
        # Wait for dialog to close
        dialog.wait_window()
        return selected_folder
    
    def copy_image(self):
        """Copy current image to selected folder"""
        if not self.image_files or self.current_index < 0:
            messagebox.showwarning("No Image", "No image selected to copy.")
            return
        
        destination = self.select_destination_folder("Copy")
        if not destination:
            return
        
        try:
            current_image = self.image_files[self.current_index]
            filename = os.path.basename(current_image)
            destination_path = os.path.join(destination, filename)
            
            # Handle filename conflicts
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(destination_path):
                new_filename = f"{base_name}_copy_{counter}{ext}"
                destination_path = os.path.join(destination, new_filename)
                counter += 1
            
            # Copy the file
            shutil.copy2(current_image, destination_path)
            
            # Add to history
            self.add_to_copy_move_history(destination)
            
            # Update status and show temporary success message
            final_filename = os.path.basename(destination_path)
            success_msg = f"✓ Copied '{filename}' to '{os.path.basename(destination)}'"
            self.show_temporary_message(success_msg, 3000)  # Show for 3 seconds
            
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy image: {str(e)}")
            self.status_label.config(text=f"Copy failed: {str(e)}")
    
    def duplicate_image(self):
        """Duplicate current image in the same folder"""
        if not self.image_files or self.current_index < 0:
            messagebox.showwarning("No Image", "No image selected to duplicate.")
            return
        
        try:
            current_image = self.image_files[self.current_index]
            filename = os.path.basename(current_image)
            directory = os.path.dirname(current_image)
            base_name, ext = os.path.splitext(filename)
            
            # Find next available duplicate name
            counter = 1
            while True:
                duplicate_name = f"{base_name}_copy{counter}{ext}"
                duplicate_path = os.path.join(directory, duplicate_name)
                if not os.path.exists(duplicate_path):
                    break
                counter += 1
            
            # Create the duplicate
            shutil.copy2(current_image, duplicate_path)
            
            # Add the new duplicate to the file list and sort
            self.image_files.append(duplicate_path)
            self.image_files.sort()
            
            # Update status and show temporary success message
            success_msg = f"✓ Duplicated as '{duplicate_name}'"
            self.show_temporary_message(success_msg, 3000)  # Show for 3 seconds
            
        except Exception as e:
            messagebox.showerror("Duplicate Error", f"Failed to duplicate image: {str(e)}")
            self.status_label.config(text=f"Duplicate failed: {str(e)}")
    
    def move_image(self):
        """Move current image to selected folder"""
        if not self.image_files or self.current_index < 0:
            messagebox.showwarning("No Image", "No image selected to move.")
            return
        
        destination = self.select_destination_folder("Move")
        if not destination:
            return
        
        try:
            current_image = self.image_files[self.current_index]
            filename = os.path.basename(current_image)
            destination_path = os.path.join(destination, filename)
            
            # Handle filename conflicts
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(destination_path):
                new_filename = f"{base_name}_moved_{counter}{ext}"
                destination_path = os.path.join(destination, new_filename)
                counter += 1
            
            # Move the file
            shutil.move(current_image, destination_path)
            
            # Add to history
            self.add_to_copy_move_history(destination)
            
            # Remove from current list and update display
            del self.image_files[self.current_index]
            
            # Move to next image or update UI
            if self.image_files:
                if self.current_index >= len(self.image_files):
                    self.current_index = len(self.image_files) - 1
                self.display_current_image()
            else:
                self.canvas.delete("all")
                self.status_label.config(text="No images left in folder")
                self.root.title("Image Player")
                return
            
            # Update status and show temporary success message
            final_filename = os.path.basename(destination_path)
            success_msg = f"✓ Moved '{filename}' to '{os.path.basename(destination)}'"
            self.show_temporary_message(success_msg, 3000)  # Show for 3 seconds
            
        except Exception as e:
            messagebox.showerror("Move Error", f"Failed to move image: {str(e)}")
            self.status_label.config(text=f"Move failed: {str(e)}")
    
    def delete_images_and_folder(self):
        """Delete all images in the current folder and the folder itself (only if it contains only images)"""
        # Check if we have a current folder (either from loaded images or last known folder)
        folder_path = None
        
        if self.image_files:
            # Get folder from currently loaded images
            folder_path = os.path.dirname(self.image_files[0])
        elif hasattr(self, 'current_folder') and self.current_folder:
            # Use the last known folder (even if no images remain)
            folder_path = self.current_folder
        else:
            messagebox.showwarning("No Folder", "No folder is currently selected. Please select a folder first.")
            return
        
        folder_name = os.path.basename(folder_path)
        
        try:
            # Get all files in the folder (not just image files we loaded)
            all_files = []
            all_dirs = []
            
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    all_files.append(item)
                elif os.path.isdir(item_path):
                    all_dirs.append(item)
            
            # Check if there are any subdirectories
            if all_dirs:
                messagebox.showerror("Cannot Delete", 
                    f"Folder '{folder_name}' contains subdirectories:\n{', '.join(all_dirs[:5])}\n\n" +
                    "This command only works with folders that contain only image files.")
                return
            
            # Check if there are any non-image files
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico', '.enc'}
            safe_text_files = {'.nfo', '.txt'}  # Additional safe files to allow deletion
            non_image_files = []
            
            for file in all_files:
                # Skip system files that are commonly safe to delete
                if file.lower() in {'.ds_store', 'thumbs.db', '.picasa.ini', 'desktop.ini'}:
                    continue
                
                file_ext = os.path.splitext(file.lower())[1]
                # Allow deletion if it's an image file or a safe text file
                if file_ext not in image_extensions and file_ext not in safe_text_files:
                    non_image_files.append(file)
            
            if non_image_files:
                messagebox.showerror("Cannot Delete", 
                    f"Folder '{folder_name}' contains unsupported files:\n{', '.join(non_image_files[:5])}\n\n" +
                    "This command only works with folders containing:\n" +
                    "• Image files (jpg, png, gif, bmp, etc.)\n" +
                    "• Text files (.nfo, .txt)\n" +
                    "• Common system files (.DS_Store, Thumbs.db)")
                return
            
            # Confirm the dangerous operation (single confirmation)
            total_files = len(all_files)
            confirmation_msg = (
                f"⚠️ DELETE FOLDER AND ALL CONTENTS ⚠️\n\n"
                f"This will permanently DELETE:\n"
                f"• All {total_files} image files in folder '{folder_name}'\n"
                f"• The folder '{folder_name}' itself\n\n"
                f"Folder: {folder_path}\n\n"
                f"This action CANNOT be undone!\n\n"
                f"Proceed with deletion?"
            )
            
            result = messagebox.askyesno(
                "⚠️ CONFIRM FOLDER DELETION ⚠️", 
                confirmation_msg,
                icon='warning'
            )
            
            if not result:
                return
            
            # Perform the deletion
            import shutil
            
            # Remember the parent directory before deletion
            parent_dir = os.path.dirname(folder_path)
            
            # Delete the entire folder and all its contents
            shutil.rmtree(folder_path)
            
            # Clear the current state
            self.image_files = []
            self.current_index = -1
            self.current_folder = None
            self.canvas.delete("all")
            self.root.title("Image Viewer")
            
            # Show success message
            success_msg = f"✓ Deleted folder '{folder_name}' and all {total_files} image files"
            self.show_temporary_message(success_msg, 4000)
            
            # Try to find and load the next available folder with images
            next_folder = self.find_next_folder_with_images(parent_dir, folder_name)
            if next_folder:
                self.load_images_from_folder(next_folder)
                self.status_label.config(text=f"Moved to next folder: {os.path.basename(next_folder)}")
            else:
                self.status_label.config(text="Folder deleted - No other image folders found in parent directory")
            
        except Exception as e:
            messagebox.showerror("Deletion Error", f"Failed to delete folder: {str(e)}")
            self.status_label.config(text=f"Deletion failed: {str(e)}")
    
    def find_next_folder_with_images(self, parent_dir, deleted_folder_name):
        """Find the next folder in the parent directory that contains images"""
        try:
            # Get all subdirectories in the parent directory
            all_dirs = []
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    all_dirs.append(item)
            
            # Sort directories
            all_dirs.sort()
            
            # Find where the deleted folder would have been (it's already deleted)
            deleted_index = -1
            for i, dir_name in enumerate(all_dirs):
                if dir_name > deleted_folder_name:  # First folder that comes after alphabetically
                    deleted_index = i - 1
                    break
            
            # If no folder comes after, the deleted folder was at the end
            if deleted_index == -1:
                deleted_index = len(all_dirs)
            
            # Check folders starting from where the deleted folder would have been
            image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.enc')
            
            # First, try folders after the deleted one
            for i in range(deleted_index + 1, len(all_dirs)):
                folder_path = os.path.join(parent_dir, all_dirs[i])
                if self.folder_has_images(folder_path, image_extensions):
                    return folder_path
            
            # Then, try folders before the deleted one
            for i in range(0, deleted_index):
                folder_path = os.path.join(parent_dir, all_dirs[i])
                if self.folder_has_images(folder_path, image_extensions):
                    return folder_path
            
            return None
            
        except Exception:
            return None
    
    def folder_has_images(self, folder_path, image_extensions):
        """Check if a folder contains any image files"""
        try:
            for file in os.listdir(folder_path):
                if (os.path.isfile(os.path.join(folder_path, file)) and 
                    not file.startswith('.') and 
                    file.lower().endswith(image_extensions)):
                    return True
            return False
        except Exception:
            return False
    
    def get_subfolders_with_images(self, folder_path):
        """Get all subfolders in the given folder that contain images, sorted alphabetically"""
        try:
            subfolders_with_images = []
            image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.enc')
            
            # Get all subdirectories
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    if self.folder_has_images(item_path, image_extensions):
                        subfolders_with_images.append(item_path)
            
            # Sort alphabetically by folder name
            subfolders_with_images.sort(key=lambda x: os.path.basename(x))
            return subfolders_with_images
            
        except Exception:
            return []

    def find_next_sibling_folder(self, parent_dir, current_folder_name, direction='next'):
        """Find the next or previous sibling folder with images in the parent directory"""
        try:
            # Get all subdirectories in the parent directory
            all_dirs = []
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    all_dirs.append(item)
            
            # Sort directories alphabetically
            all_dirs.sort()
            
            # Find the index of the current folder
            try:
                current_index = all_dirs.index(current_folder_name)
            except ValueError:
                return None  # Current folder not found in parent directory
            
            # Check for image extensions
            image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.enc')
            
            if direction == 'next':
                # Look for next folder with images
                for i in range(current_index + 1, len(all_dirs)):
                    folder_path = os.path.join(parent_dir, all_dirs[i])
                    if self.folder_has_images(folder_path, image_extensions):
                        return folder_path
                # No next folder found
                return None
            
            elif direction == 'prev':
                # Look for previous folder with images
                for i in range(current_index - 1, -1, -1):
                    folder_path = os.path.join(parent_dir, all_dirs[i])
                    if self.folder_has_images(folder_path, image_extensions):
                        return folder_path
                # No previous folder found
                return None
            
            return None
            
        except Exception:
            return None
    
    def next_folder(self):
        """Navigate to the next folder with images"""
        if not self.current_folder:
            messagebox.showwarning("No Folder", "No folder is currently loaded.")
            return
        
        # Check if current folder has subfolders with images
        subfolders = self.get_subfolders_with_images(self.current_folder)
        
        if subfolders:
            # If we're in a parent directory with subfolders, go to first subfolder
            self.load_images_from_folder(subfolders[0])
            folder_name = os.path.basename(subfolders[0])
            self.show_temporary_message(f"→ Moved to subfolder: {folder_name}", 2000)
        else:
            # We're in a subfolder, navigate to sibling folders or back to parent
            parent_dir = os.path.dirname(self.current_folder)
            current_folder_name = os.path.basename(self.current_folder)
            
            next_folder = self.find_next_sibling_folder(parent_dir, current_folder_name, direction='next')
            if next_folder:
                # Found next sibling subfolder
                self.load_images_from_folder(next_folder)
                folder_name = os.path.basename(next_folder)
                self.show_temporary_message(f"→ Moved to folder: {folder_name}", 2000)
            else:
                # No more sibling subfolders, check if parent has images and return to it
                image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.enc')
                if self.folder_has_images(parent_dir, image_extensions):
                    self.load_images_from_folder(parent_dir)
                    folder_name = os.path.basename(parent_dir)
                    self.show_temporary_message(f"→ Returned to parent folder: {folder_name}", 2000)
                else:
                    self.show_temporary_message("No more folders with images found", 2000)
    
    def prev_folder(self):
        """Navigate to the previous folder with images"""
        if not self.current_folder:
            messagebox.showwarning("No Folder", "No folder is currently loaded.")
            return
        
        # Check if current folder has subfolders with images
        subfolders = self.get_subfolders_with_images(self.current_folder)
        
        if subfolders:
            # If we're in a parent directory with subfolders, go to last subfolder
            self.load_images_from_folder(subfolders[-1])
            folder_name = os.path.basename(subfolders[-1])
            self.show_temporary_message(f"← Moved to subfolder: {folder_name}", 2000)
        else:
            # We're in a subfolder, navigate to sibling folders or back to parent
            parent_dir = os.path.dirname(self.current_folder)
            current_folder_name = os.path.basename(self.current_folder)
            
            prev_folder = self.find_next_sibling_folder(parent_dir, current_folder_name, direction='prev')
            if prev_folder:
                # Found previous sibling subfolder
                self.load_images_from_folder(prev_folder)
                folder_name = os.path.basename(prev_folder)
                self.show_temporary_message(f"← Moved to folder: {folder_name}", 2000)
            else:
                # No more sibling subfolders, check if parent has images and return to it
                image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.enc')
                if self.folder_has_images(parent_dir, image_extensions):
                    self.load_images_from_folder(parent_dir)
                    folder_name = os.path.basename(parent_dir)
                    self.show_temporary_message(f"← Returned to parent folder: {folder_name}", 2000)
                else:
                    self.show_temporary_message("No previous folders with images found", 2000)
    
    def find_prev_folder_with_images(self, parent_dir, current_folder_name):
        """Find the previous folder in the parent directory that contains images"""
        try:
            # Get all subdirectories in the parent directory
            all_dirs = []
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    all_dirs.append(item)
            
            # Sort directories
            all_dirs.sort()
            
            # Find the position of the current folder
            current_index = -1
            for i, dir_name in enumerate(all_dirs):
                if dir_name == current_folder_name:
                    current_index = i
                    break
            
            if current_index == -1:
                return None
            
            # Check folders starting from the previous one
            image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.enc')
            
            # Try folders before the current one (going backwards)
            for i in range(current_index - 1, -1, -1):
                folder_path = os.path.join(parent_dir, all_dirs[i])
                if self.folder_has_images(folder_path, image_extensions):
                    return folder_path
            
            # Then, wrap around and try folders after the current one (from the end)
            for i in range(len(all_dirs) - 1, current_index, -1):
                folder_path = os.path.join(parent_dir, all_dirs[i])
                if self.folder_has_images(folder_path, image_extensions):
                    return folder_path
            
            return None
            
        except Exception:
            return None
    
    def zoom_in(self):
        """Increase image zoom"""
        if self.zoom_level < self.max_zoom:
            self.zoom_level = min(self.max_zoom, self.zoom_level + self.zoom_increment)
            self.apply_zoom_and_display()
            zoom_percent = int(self.zoom_level * 100)
            self.status_label.config(text=f"Zoom: {zoom_percent}%")
    
    def zoom_out(self):
        """Decrease image zoom"""
        if self.zoom_level > self.min_zoom:
            self.zoom_level = max(self.min_zoom, self.zoom_level - self.zoom_increment)
            self.apply_zoom_and_display()
            zoom_percent = int(self.zoom_level * 100)
            self.status_label.config(text=f"Zoom: {zoom_percent}%")
    
    def reset_zoom(self):
        """Reset image zoom to fit window"""
        self.zoom_level = 1.0  # Fit to window
        self.image_offset_x = 0  # Reset pan position
        self.image_offset_y = 0
        self.apply_zoom_and_display()
        self.status_label.config(text="Zoom: Fit to window")
    
    def save_current_zoom(self):
        """Save the current zoom level and pan position for this image file"""
        if not self.image_files or self.current_index < 0 or self.current_index >= len(self.image_files):
            return
        
        image_path = self.image_files[self.current_index]
        # Save both zoom level and pan position
        self.image_zoom_memory[image_path] = {
            'zoom': self.zoom_level,
            'offset_x': self.image_offset_x,
            'offset_y': self.image_offset_y
        }
        
        # Save to persistent storage
        self.save_zoom_data()
        
        zoom_percent = int(self.zoom_level * 100)
        self.status_label.config(text=f"Saved zoom: {zoom_percent}% and position")
    
    def load_saved_zoom_and_position(self):
        """Load the saved zoom level and pan position for current image, or use defaults if none saved"""
        if not self.image_files or self.current_index < 0 or self.current_index >= len(self.image_files):
            return 1.0, 0, 0
        
        image_path = self.image_files[self.current_index]
        saved_data = self.image_zoom_memory.get(image_path, None)
        
        if saved_data is None:
            # No saved data, return defaults
            return 1.0, 0, 0
        
        # Handle both old format (just zoom value) and new format (dict with zoom and position)
        if isinstance(saved_data, dict):
            # New format with both zoom and position
            zoom = saved_data.get('zoom', 1.0)
            offset_x = saved_data.get('offset_x', 0)
            offset_y = saved_data.get('offset_y', 0)
            return zoom, offset_x, offset_y
        else:
            # Old format (just zoom value), return default position
            return saved_data, 0, 0
    
    def load_saved_zoom(self):
        """Legacy function for backward compatibility"""
        zoom, _, _ = self.load_saved_zoom_and_position()
        return zoom
    
    def clear_saved_zoom(self):
        """Clear the saved zoom and position for current image"""
        if not self.image_files or self.current_index < 0 or self.current_index >= len(self.image_files):
            return
        
        image_path = self.image_files[self.current_index]
        if image_path in self.image_zoom_memory:
            del self.image_zoom_memory[image_path]
            # Save to persistent storage
            self.save_zoom_data()
            self.status_label.config(text="Cleared saved zoom and position")
    
    def toggle_crop_mode(self):
        """Toggle crop mode on/off"""
        self.is_cropping = not self.is_cropping
        if self.is_cropping:
            self.crop_button.config(text="Exit Crop Mode", bg="#ffcccc")
            self.status_label.config(text="Crop mode: Click and drag to select area")
        else:
            # Reset to default button color
            self.crop_button.config(text="Crop Mode", bg=self.default_button_bg)
            self.status_label.config(text="Crop mode disabled")
            # Clear any existing crop rectangle
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)
                self.crop_rect = None
    
    def start_crop(self, event):
        """Start cropping selection"""
        if not self.is_cropping or not self.current_image:
            return
        
        # Clear any existing crop rectangle
        if self.crop_rect:
            self.canvas.delete(self.crop_rect)
        
        # Store start coordinates
        self.crop_start_x = event.x
        self.crop_start_y = event.y
    
    def update_crop(self, event):
        """Update cropping selection"""
        if not self.is_cropping or not self.current_image or self.crop_start_x is None:
            return
        
        # Clear previous rectangle
        if self.crop_rect:
            self.canvas.delete(self.crop_rect)
        
        # Draw new rectangle
        self.crop_rect = self.canvas.create_rectangle(
            self.crop_start_x, self.crop_start_y, event.x, event.y,
            outline="red", width=2
        )
    
    def end_crop(self, event):
        """End cropping selection and perform crop"""
        if not self.is_cropping or not self.current_image or self.crop_start_x is None:
            return
        
        # Store end coordinates
        self.crop_end_x = event.x
        self.crop_end_y = event.y
        
        # Check if we have a valid selection
        if abs(self.crop_end_x - self.crop_start_x) < 10 or abs(self.crop_end_y - self.crop_start_y) < 10:
            self.status_label.config(text="Crop area too small")
            return
        
        # Convert canvas coordinates to image coordinates
        try:
            # Calculate the coordinates relative to the displayed image
            canvas_crop_x1 = min(self.crop_start_x, self.crop_end_x) - self.image_x
            canvas_crop_y1 = min(self.crop_start_y, self.crop_end_y) - self.image_y
            canvas_crop_x2 = max(self.crop_start_x, self.crop_end_x) - self.image_x
            canvas_crop_y2 = max(self.crop_start_y, self.crop_end_y) - self.image_y
            
            # Ensure coordinates are within image bounds
            canvas_crop_x1 = max(0, min(self.image_width, canvas_crop_x1))
            canvas_crop_y1 = max(0, min(self.image_height, canvas_crop_y1))
            canvas_crop_x2 = max(0, min(self.image_width, canvas_crop_x2))
            canvas_crop_y2 = max(0, min(self.image_height, canvas_crop_y2))
            
            # Calculate scale factor between displayed image and original image
            scale_x = self.original_image.width / self.image_width
            scale_y = self.original_image.height / self.image_height
            
            # Convert to original image coordinates
            orig_x1 = int(canvas_crop_x1 * scale_x)
            orig_y1 = int(canvas_crop_y1 * scale_y)
            orig_x2 = int(canvas_crop_x2 * scale_x)
            orig_y2 = int(canvas_crop_y2 * scale_y)
            
            # Crop the original image
            cropped_image = self.original_image.crop((orig_x1, orig_y1, orig_x2, orig_y2))
            
            # Save cropped image
            self.save_cropped_image(cropped_image)
            
        except Exception as e:
            messagebox.showerror("Crop Error", f"Could not crop image: {str(e)}")
            self.status_label.config(text=f"Crop failed: {str(e)}")
        
        # Clear crop selection
        if self.crop_rect:
            self.canvas.delete(self.crop_rect)
            self.crop_rect = None
        self.crop_start_x = None
        self.crop_start_y = None
    
    def save_cropped_image(self, cropped_image):
        """Save the cropped image as a new file"""
        if not self.image_files or self.current_index < 0:
            return
        
        try:
            # Get current image info
            original_path = self.image_files[self.current_index]
            directory = os.path.dirname(original_path)
            filename = os.path.basename(original_path)
            name, ext = os.path.splitext(filename)
            
            # Create unique filename for cropped image
            counter = 1
            while True:
                cropped_filename = f"{name}_cropped_{counter}{ext}"
                cropped_path = os.path.join(directory, cropped_filename)
                if not os.path.exists(cropped_path):
                    break
                counter += 1
            
            # Save the cropped image
            cropped_image.save(cropped_path)
            self.status_label.config(text=f"Cropped image saved as: {cropped_filename}")
            
            # Ask if user wants to reload folder to see new image
            if messagebox.askyesno("Reload Folder", "Reload folder to include the new cropped image?"):
                current_folder = os.path.dirname(self.image_files[self.current_index])
                self.load_images_from_folder(current_folder)
                
                # Navigate to the newly created cropped image
                try:
                    new_image_index = self.image_files.index(cropped_path)
                    self.current_index = new_image_index
                    self.display_current_image()
                    self.status_label.config(text=f"Now viewing cropped image: {cropped_filename}")
                except ValueError:
                    # If for some reason the new image isn't found, just stay on current image
                    self.status_label.config(text=f"Cropped image saved but not found in list: {cropped_filename}")
                
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save cropped image: {str(e)}")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if not self.is_fullscreen:
            # Store current geometry before going fullscreen
            self.original_geometry = self.root.geometry()
            self.root.attributes('-fullscreen', True)
            # Keep control panel visible in fullscreen mode
            self.is_fullscreen = True
        else:
            self.exit_fullscreen()
    
    def exit_fullscreen(self):
        """Exit fullscreen mode"""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes('-fullscreen', False)
            # Small delay to ensure fullscreen is properly cleared
            self.root.after(10, self._restore_window_geometry)
    
    def _restore_window_geometry(self):
        """Helper method to restore window geometry after exiting fullscreen"""
        # Restore window geometry and ensure it's visible
        self.root.geometry(self.original_geometry)
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        # Redisplay image to adjust to new window size
        if self.current_image:
            self.root.after(100, self.apply_zoom_and_display)

    def toggle_toolbar(self):
        """Toggle toolbar visibility (F9)"""
        if self.is_toolbar_hidden:
            # Show toolbar
            self.control_panel.pack(side=tk.BOTTOM, fill=tk.X)
            self.is_toolbar_hidden = False
        else:
            # Hide toolbar
            self.control_panel.pack_forget()
            self.is_toolbar_hidden = True

    def toggle_slideshow(self):
        """Toggle slideshow mode"""
        if not self.is_slideshow:
            if not self.image_files:
                self.status_label.config(text="No images to show")
                return
            
            self.is_slideshow = True
            self.slideshow_paused = False  # Ensure we start unpaused
            self.slideshow_button.config(text="Stop Slideshow (W)", bg="#ffcccc")
            
            # Enter fullscreen for slideshow (toolbar will remain visible)
            if not self.is_fullscreen:
                self.toggle_fullscreen()
            
            self.status_label.config(text="Slideshow started - Press W to stop, Space to pause")
            self.start_slideshow()
        else:
            # Stop slideshow but remain in fullscreen if we were in fullscreen
            self.stop_slideshow()
    
    def start_slideshow(self):
        """Start the slideshow timer"""
        if self.is_slideshow and self.image_files:
            # Start the slideshow loop (first iteration will advance to next image)
            self.slideshow_loop()
    
    def slideshow_loop(self):
        """Main slideshow loop that handles timing and pause states"""
        if not self.is_slideshow:
            return  # Slideshow was stopped
            
        if not self.slideshow_paused:
            # If not paused, move to next image and schedule next iteration
            self.next_image()
            self.slideshow_timer_id = self.root.after(self.slideshow_interval, self.slideshow_loop)
        # If paused, don't schedule anything - wait for resume
    
    def stop_slideshow(self):
        """Stop slideshow mode"""
        if not self.is_slideshow:
            return  # Already stopped
            
        self.is_slideshow = False
        self.slideshow_paused = False  # Reset pause state
        # Reset to default button color
        self.slideshow_button.config(text="Slideshow (W)", bg=self.default_button_bg)
        
        # Cancel timer
        if self.slideshow_timer_id:
            self.root.after_cancel(self.slideshow_timer_id)
            self.slideshow_timer_id = None
        
        self.status_label.config(text="Slideshow stopped")
    
    def toggle_slideshow_pause(self):
        """Toggle pause state of slideshow while it's running"""
        if not self.is_slideshow:
            self.status_label.config(text="No slideshow running to pause")
            return
        
        if self.slideshow_paused:
            # Resume slideshow
            self.slideshow_paused = False
            self.slideshow_button.config(text="Stop Slideshow (W)", bg="#ffcccc")
            self.animation_button.config(text="⏸️ Pause (Space)", bg=self.default_button_bg, state='normal')
            self.status_label.config(text="Slideshow resumed - Press W to stop, Space to pause")
            # Restart the slideshow timer from current image
            self.slideshow_timer_id = self.root.after(self.slideshow_interval, self.slideshow_loop)
        else:
            # Pause slideshow
            self.slideshow_paused = True
            self.slideshow_button.config(text="Slideshow Paused (W)", bg="#ffffcc")
            self.animation_button.config(text="▶️ Resume (Space)", bg="#e6ffe6", state='normal')
            self.status_label.config(text="Slideshow paused - Press W to stop, Space to resume")
            # Cancel the current timer to truly pause
            if self.slideshow_timer_id:
                self.root.after_cancel(self.slideshow_timer_id)
                self.slideshow_timer_id = None
    
    def handle_space_key(self):
        """Smart space key handler - prioritizes slideshow pause/resume over GIF animation"""
        if self.is_slideshow:
            # If slideshow is running, space controls slideshow pause/resume
            self.toggle_slideshow_pause()
        else:
            # If no slideshow, space controls GIF animation
            self.toggle_animation()
    
    def cycle_background(self):
        """Cycle through background options for transparent images"""
        backgrounds = list(self.background_options.keys())
        current_index = backgrounds.index(self.current_background)
        next_index = (current_index + 1) % len(backgrounds)
        self.current_background = backgrounds[next_index]
        
        # Update canvas background
        if self.current_background == "Checkered":
            # Create a checkered pattern for transparency visualization
            self.create_checkered_background()
        else:
            self.canvas.config(bg=self.background_options[self.current_background])
        
        # Update button text to show current background
        self.background_button.config(text=f"🎨 {self.current_background}")
        
        # Refresh the current image display to apply new background
        if self.current_image:
            self.apply_zoom_and_display()
            
        # Show temporary message
        self.show_temporary_message(f"Background: {self.current_background}", 1500)
    
    def create_checkered_background(self):
        """Create a checkered pattern background for transparency visualization"""
        # This will be implemented as a canvas pattern when image is displayed
        self.canvas.config(bg="#E0E0E0")  # Light gray base for checkered pattern
    
    def create_checkered_image(self, size):
        """Create a checkered pattern image for transparency background"""
        width, height = size
        # Create checkered pattern (like Photoshop/GIMP transparency indicator)
        checker_size = 16  # Size of each checker square
        
        # Create the pattern
        pattern = Image.new('RGB', (checker_size * 2, checker_size * 2), (255, 255, 255))
        # Add dark squares
        for x in range(0, checker_size * 2, checker_size):
            for y in range(0, checker_size * 2, checker_size):
                if (x // checker_size + y // checker_size) % 2:
                    for px in range(x, x + checker_size):
                        for py in range(y, y + checker_size):
                            if px < checker_size * 2 and py < checker_size * 2:
                                pattern.putpixel((px, py), (192, 192, 192))  # Light gray
        
        # Tile the pattern to match image size
        result = Image.new('RGB', size, (255, 255, 255))
        for x in range(0, width, checker_size * 2):
            for y in range(0, height, checker_size * 2):
                result.paste(pattern, (x, y))
        
        return result
    
    def toggle_border(self):
        """Toggle the image border visibility"""
        self.show_image_border = not self.show_image_border
        
        # Refresh the current image display
        if self.current_image:
            self.apply_zoom_and_display()
            
        # Show status message
        status = "ON" if self.show_image_border else "OFF"
        self.show_temporary_message(f"Image border: {status}", 1500)
    
    def on_close(self):
        """Handle application close"""
        # Stop slideshow
        if self.is_slideshow:
            self.stop_slideshow()
        
        # Stop any GIF animation
        self.stop_animation()
        
        # Clean up and close
        self.root.destroy()

# Main function to start the application
def main():
    root = tk.Tk()
    app = ImageViewer(root)
    
    # Check if a file was passed as command line argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.isfile(file_path):
            # Load the folder containing this file
            folder_path = os.path.dirname(os.path.abspath(file_path))
            app.load_images_from_folder(folder_path)
            # Navigate to the specific file
            try:
                file_index = app.image_files.index(os.path.abspath(file_path))
                app.current_index = file_index
                app.display_current_image()
            except (ValueError, AttributeError):
                # File not found in the list, just show the folder
                pass
    
    root.mainloop()

if __name__ == "__main__":
    main()
