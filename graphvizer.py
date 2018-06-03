import sublime
import sublime_plugin
import functools
import os
from . import syntaxchecker
import threading, queue
import subprocess
import tempfile


def get_dot_file():
	tempdir = tempfile.gettempdir()
	return os.path.join(tempdir, "graphvizer.dot")

def get_image_file():
	tempdir = tempfile.gettempdir()
	return os.path.join(tempdir, "graphvizer.png")


# Trigged when user input text
class UserEditListener(sublime_plugin.EventListener):

	def __init__(self):
		super(UserEditListener, self).__init__()
		self.queue_syntaxchecking = queue.Queue(maxsize=9) # For syntax checking
		self.queue_rendering = queue.Queue(maxsize=9) # For graph rendering
		# Start worker thread for syntax checking
		syntax_thread = threading.Thread(target=self.syntax_thread, daemon=True)
		syntax_thread.start()
		# Start worker thread for graph rendering
		dot_thread = threading.Thread(target=self.dot_thread, daemon=True)
		dot_thread.start()
		# These variables will be initialized in on_modified
		self.dot_cmd_path = None
		self.dot_timeout = None

	def dot_thread(self):
		dot_file = get_dot_file()
		while True:
			contents = self.queue_rendering.get(block=True, timeout=None)
			'''
			For purpose of cross-platform, we can't use TemporaryFile class because
			subprocess can't read it directly on Windows. Using a regular file is a
			good choice.
			'''
			with open(file=dot_file, mode="w", encoding="utf-8") as fd:
				fd.write(contents)
			image_file = get_image_file()
			cmd = [self.dot_cmd_path, dot_file, "-Tpng", "-o", image_file]
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
			contents = self.queue_syntaxchecking.get(block=True, timeout=None)
			# Check if the syntax is valid
			syntax_is_valid, log = syntaxchecker.check(contents)
			if syntax_is_valid:
				self.print(log)
				# Put the valid contents into the queue for graph rendering
				self.queue_rendering.put(contents, block=True, timeout=None)
			else:
				self.print(log)

	def on_modified(self, view):
		'''
		Detect language. Only process DOT file.
		self.print() can only be called after this detection.
		Otherwise, the panel's modification will also trigger the on_modified
		function, so the plugin will fall into a infinite recursion and the
		plugin_host will crash.
		'''
		file_syntax = view.settings().get('syntax')
		if "DOT.sublime-syntax" not in file_syntax:
			return

		# Load settings
		if self.dot_cmd_path is None:
			settings = sublime.load_settings("Graphvizer.sublime-settings")
			self.dot_cmd_path = settings.get("dot_cmd_path")
		if self.dot_timeout is None:
			settings = sublime.load_settings("Graphvizer.sublime-settings")
			self.dot_timeout = settings.get("dot_timeout")

		# Get the contents of the whole file
		region = sublime.Region(0, view.size())
		contents = view.substr(region)
		# Put the contents into the queue for syntax checking
		self.queue_syntaxchecking.put(contents, block=True, timeout=None)

	def print(self, text):
		# Get the active window as current main window
		current_window = sublime.active_window()
		current_window.run_command("graphvizer_print_to_panel", {"text": text})


# Open image file in a new window
class GraphvizerOpenImageCommand(sublime_plugin.WindowCommand):

	def __init__(self, window):
		super(GraphvizerOpenImageCommand, self).__init__(window)
		self.image_window = None

	def run(self):
		self.open_or_close_image_window()

	def open_or_close_image_window(self):
		# Check if image has been opened
		if self.image_window is None:
			image_file = get_image_file()
			sublime.run_command("new_window")
			self.image_window = sublime.active_window()
			self.image_window.open_file(image_file)
			self.image_window.set_menu_visible(False)
			self.image_window.set_tabs_visible(False)
			self.image_window.set_minimap_visible(False)
			self.image_window.set_status_bar_visible(False)
		else:
			self.image_window.run_command("close_window")
			self.image_window = None
