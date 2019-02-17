import sublime
import sublime_plugin
import functools
import os
from . import syntaxchecker
import threading, queue
import subprocess
import tempfile

# Temporary file used to generate image
def get_dot_file():
	tempdir = tempfile.gettempdir()
	return os.path.join(tempdir, "graphvizer.dot")

# Generated image file
def get_image_file():
	image_dir = None
	settings = sublime.load_settings("Graphvizer.sublime-settings")
	image_dir = settings.get("image_dir")
	# Use the default path
	if image_dir is None:
		image_dir = tempfile.gettempdir()
	# Check path existence
	if not os.path.exists(image_dir):
		print("%s doesn't exist. Use the default path instead." %image_dir)
		image_dir = tempfile.gettempdir()
	# Check path permission
	if not os.access(image_dir, os.W_OK):
		print("%s doesn't have permission to write. Use the default path instead." %image_dir)
		image_dir = tempfile.gettempdir()

	return os.path.join(image_dir, "graphvizer.png")

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
		# These variables will be initialized in rendering()
		self.dot_cmd_path = None
		self.dot_timeout = None
		self.dot_file = None
		self.image_file = None

		self.setting_loaded = False

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
			with open(file=self.dot_file, mode="w", encoding="utf-8") as fd:
				fd.write(contents)

			cmd = [self.dot_cmd_path, self.dot_file, "-Tpng", "-o", self.image_file]
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
				stdout, stderr = process.communicate(timeout=self.dot_timeout)
			except TimeoutExpired:
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
			if syntax_is_valid:
				self.print(log)
				# Put the valid contents into the queue for graph rendering
				self.queue_rendering.put(contents, block=True, timeout=None)
			else:
				self.print(log)

	def rendering(self, view):
		# Load settings
		if not self.setting_loaded:
			settings = sublime.load_settings("Graphvizer.sublime-settings")
			self.dot_cmd_path = settings.get("dot_cmd_path")
			self.dot_timeout = settings.get("dot_timeout")
			self.image_file = get_image_file()
			self.dot_file = get_dot_file()
			self.setting_loaded = True

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
		self.show_image_with = None

	def run(self):
		if self.show_image_with is None:
			settings = sublime.load_settings("Graphvizer.sublime-settings")
			self.show_image_with = settings.get("show_image_with")

		if self.show_image_with == "window":
			self.open_image_window()
		elif self.show_image_with == "layout":
			self.open_image_layout()
		else:
			self.open_image_tab()

	def open_image_window(self):
		image_file = get_image_file()
		sublime.run_command("new_window")
		image_window = sublime.active_window()
		image_window.open_file(image_file)
		image_window.set_menu_visible(False)
		image_window.set_tabs_visible(False)
		image_window.set_minimap_visible(False)
		image_window.set_status_bar_visible(False)

	def open_image_layout(self):
		image_file = get_image_file()
		self.window.set_layout({
			"cols": [0.0, 0.5, 1.0],
			"rows": [0.0, 1.0],
			"cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
		})
		self.window.focus_group(1)
		self.window.open_file(image_file)
		self.window.focus_group(0)

	def open_image_tab(self):
		image_file = get_image_file()
		self.window.open_file(image_file)
