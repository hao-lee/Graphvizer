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
		# Start worker thread
		self.queue = queue.Queue(maxsize=9)
		thread = threading.Thread(target=self.dot_thread, daemon=True)
		thread.start()

	def dot_thread(self):
		while True:
			contents = self.queue.get(block=True, timeout=None)
			'''
			For purpose of cross-platform, we can't use TemporaryFile class because
			subprocess can't read it directly on Windows. Using a regular file is a
			good choice.
			'''
			dot_file = get_dot_file()
			with open(file=dot_file, mode="w", encoding="utf-8") as fd:
				fd.write(contents)
			image_file = get_image_file()
			cmd = ["dot", dot_file, "-Tpng", "-o", image_file]
			# For Windows, we must use startupinfo to hide the console window.
			startupinfo = None
			if os.name == "nt":
				startupinfo = subprocess.STARTUPINFO()
				startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
											stderr=subprocess.PIPE,
											startupinfo=startupinfo)
			stdout, stderr = process.communicate()
			if len(stdout) != 0:
				self.print(stdout)
			if len(stderr) != 0:
				self.print(stderr)

	def on_modified(self, view):
		# Detect language. Only process DOT file.
		file_syntax = view.settings().get('syntax')
		if "DOT.sublime-syntax" not in file_syntax:
			return
		# Get the contents of the whole file
		region = sublime.Region(0, view.size())
		contents = view.substr(region)
		# Check if the syntax is valid
		syntax_is_valid, log = syntaxchecker.check(contents)
		if syntax_is_valid:
			self.queue.put(contents, block=True, timeout=None)
			self.print(log)
		else:
			self.print(log)

	def print(self, text):
		# Get the active window as current main window
		current_window = sublime.active_window()
		current_window.run_command("graphvizer_print_to_panel", {"text": text})


# Open image file in a new window
class GraphvizerOpenImageCommand(sublime_plugin.WindowCommand):

	def run(self):
		image_file = get_image_file()
		sublime.run_command("new_window")
		image_window = sublime.active_window()
		image_window.open_file(image_file)
		image_window.set_menu_visible(False)
		image_window.set_tabs_visible(False)
		image_window.set_minimap_visible(False)
		image_window.set_status_bar_visible(False)
