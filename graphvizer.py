import sublime
import sublime_plugin
import functools
import os
from . import syntaxchecker
import threading, queue
import subprocess
import tempfile

# Image file path
image_filepath = None
# Settings
gvzsettings = None

# load settings when the plugin host is ready
# https://forum.sublimetext.com/t/settings-not-loading-fast-enough/40634
def plugin_loaded():
	global gvzsettings
	gvzsettings = GvzSettings()
	gvzsettings.load()
	gvzsettings.add_callback()

class GvzSettings():
	def __init__(self):
		self.st_settings = sublime.load_settings("Graphvizer.sublime-settings")

	def add_callback(self):
		self.st_settings.add_on_change("dot_cmd_path", self.load)
		self.st_settings.add_on_change("dot_timeout", self.load)
		self.st_settings.add_on_change("show_image_with", self.load)
		self.st_settings.add_on_change("image_dir", self.load)
		self.st_settings.add_on_change("render_in_realtime", self.load)

	def load(self):
		self.dot_cmd_path = self.st_settings.get("dot_cmd_path")
		self.dot_timeout = self.st_settings.get("dot_timeout")
		self.show_image_with = self.st_settings.get("show_image_with")
		self.image_dir = self.st_settings.get("image_dir")
		self.render_in_realtime = self.st_settings.get("render_in_realtime")

# Trigged when user input text
class UserEditListener(sublime_plugin.EventListener):

	def __init__(self):
		super(UserEditListener, self).__init__()
		self.queue_syntaxchecking = queue.Queue(maxsize=100) # For syntax checking
		self.queue_rendering = queue.Queue(maxsize=100) # For graph rendering
		# Start worker thread for syntax checking
		syntax_thread = threading.Thread(target=self.syntax_thread, daemon=True)
		syntax_thread.start()
		# Start worker thread for graph rendering
		dot_thread = threading.Thread(target=self.dot_thread, daemon=True)
		dot_thread.start()
		self.intermediate_file = self.get_intermediate_dot_filepath()

	# Temporary file used to generate image
	def get_intermediate_dot_filepath(self):
		tempdir = tempfile.gettempdir()
		return os.path.join(tempdir, "intermediate.dot")

	# Generated image file
	def get_image_filepath(self, image_filename):
		# Use the default path
		if gvzsettings.image_dir == "":
			return os.path.join(tempfile.gettempdir(), image_filename)
		# Check path existence
		if not os.path.exists(gvzsettings.image_dir):
			print("%s doesn't exist. Use the default path instead." %gvzsettings.image_dir)
			return os.path.join(tempfile.gettempdir(), image_filename)
		# Check path permission
		if not os.access(gvzsettings.image_dir, os.W_OK):
			print("%s doesn't have permission to write. Use the default path instead." %gvzsettings.image_dir)
			return os.path.join(tempfile.gettempdir(), image_filename)

		return os.path.join(gvzsettings.image_dir, image_filename)

	def dot_thread(self):
		while True:
			# Clear items before the last item
			while self.queue_rendering.qsize() > 1:
				self.queue_rendering.get()
			contents = self.queue_rendering.get(block=True, timeout=None)

			'''
			For purpose of cross-platform, we can't use TemporaryFile class because
			subprocess can't read it directly on Windows. Using a regular file is a
			good choice.
			'''
			with open(file=self.intermediate_file, mode="w", encoding="utf-8") as fd:
				fd.write(contents)
			global image_filepath
			cmd = [gvzsettings.dot_cmd_path, self.intermediate_file, "-Tpng", "-o", image_filepath]
			# For Windows, we must use startupinfo to hide the console window.
			startupinfo = None
			if os.name == "nt":
				startupinfo = subprocess.STARTUPINFO()
				startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
											stderr=subprocess.PIPE,
											startupinfo=startupinfo)
			# Terminate the dot process if it takes too long to complete.
			try:
				stdout, stderr = process.communicate(timeout=gvzsettings.dot_timeout)
			except subprocess.TimeoutExpired:
				process.kill()
				stdout, stderr = process.communicate()
			if len(stdout) != 0:
				self.print(stdout)
			if len(stderr) != 0:
				self.print(stderr)

	def syntax_thread(self):
		while True:
			# Clear items before the last item
			while self.queue_syntaxchecking.qsize() > 1:
				self.queue_syntaxchecking.get()
			contents = self.queue_syntaxchecking.get(block=True, timeout=None)
			# Check if the syntax is valid
			syntax_is_valid, log = syntaxchecker.check(contents)
			self.print(log)
			if syntax_is_valid and gvzsettings.render_in_realtime:
				# Put the valid contents into the queue for graph rendering
				self.queue_rendering.put(contents, block=True, timeout=None)

	def set_image_filepath(self, view):
		global image_filepath
		filepath = view.file_name()
		if filepath is None: # Current file is not saved, use temp image file
			image_filepath = self.get_image_filepath("temp~.png")
		else:
			filebasename = os.path.splitext(os.path.basename(filepath))[0] + ".png"
			image_filepath = self.get_image_filepath(filebasename)

	def rendering(self, view):
		self.set_image_filepath(view)
		# Get the contents of the whole file
		region = sublime.Region(0, view.size())
		contents = view.substr(region)
		# Put the contents into the queue for syntax checking
		self.queue_syntaxchecking.put(contents, block=True, timeout=None)

	def on_modified(self, view):
		'''
		Detect language. Only process DOT file.
		self.print() can only be called after this detection.
		Otherwise, the panel's modification will also trigger the on_modified
		function, so the plugin will fall into a infinite recursion and the
		plugin_host will crash.
		'''
		file_syntax = view.settings().get('syntax')
		if file_syntax != "Packages/Graphviz/DOT.sublime-syntax":
			return
		self.rendering(view)

	# When the file is saved, update the image_filepath using dot filename
	def on_pre_save(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax != "Packages/Graphviz/DOT.sublime-syntax":
			return
		filepath = view.file_name()
		filebasename = os.path.splitext(os.path.basename(filepath))[0] + ".png"
		global image_filepath
		image_filepath = self.get_image_filepath(filebasename)

	def on_post_save(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax != "Packages/Graphviz/DOT.sublime-syntax":
			return
		# This function is only be used when the realtime rendering is disabled
		if gvzsettings.render_in_realtime:
			return
		region = sublime.Region(0, view.size())
		contents = view.substr(region)
		syntax_is_valid, log = syntaxchecker.check(contents)
		self.print(log)
		if syntax_is_valid:
			self.queue_rendering.put(contents, block=True, timeout=None)

	# Trigger rendering if setting the file syntax to DOT
	def on_post_text_command(self, view, command_name, args):
		if command_name == "set_file_type" \
				and args["syntax"] == "Packages/Graphviz/DOT.sublime-syntax":
			self.rendering(view)

	# Trigger rendering if opening a DOT file
	def on_load(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax == "Packages/Graphviz/DOT.sublime-syntax":
			self.rendering(view)

	def print(self, text):
		# Get the active window as current main window
		current_window = sublime.active_window()
		current_window.run_command("graphvizer_print_to_panel", {"text": text})


# Open image file in a new window
class GraphvizerOpenImageCommand(sublime_plugin.WindowCommand):

	def __init__(self, window):
		super(GraphvizerOpenImageCommand, self).__init__(window)

	def run(self):
		if gvzsettings.show_image_with == "window":
			self.open_image_window()
		elif gvzsettings.show_image_with == "layout":
			self.open_image_layout()
		else:
			self.open_image_tab()

	def check_image_filepath(self):
		global image_filepath
		if image_filepath is None:
			sublime.message_dialog("Image has not been rendered!")
			return False
		if os.path.basename(image_filepath) == "temp~.png":
			sublime.message_dialog("You haven't saved your dot file, " \
				"so the image file is temporarily named temp~.png. " \
				"After your save you dot file later, please close temp~.png "\
				"and reopen image again using keyboard shortcuts or menus. " \
				"Otherwise, you won't see the correct image.")
		return True

	def open_image_window(self):
		if not self.check_image_filepath():
			return
		sublime.run_command("new_window")
		image_window = sublime.active_window()
		image_window.open_file(image_filepath)
		image_window.set_menu_visible(False)
		image_window.set_tabs_visible(False)
		image_window.set_minimap_visible(False)
		image_window.set_status_bar_visible(False)

	def open_image_layout(self):
		if not self.check_image_filepath():
			return
		self.window.set_layout({
			"cols": [0.0, 0.5, 1.0],
			"rows": [0.0, 1.0],
			"cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
		})
		self.window.focus_group(1)
		self.window.open_file(image_filepath)
		self.window.focus_group(0)

	def open_image_tab(self):
		if not self.check_image_filepath():
			return
		self.window.open_file(image_filepath)
