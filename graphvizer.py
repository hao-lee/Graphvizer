import sublime
import sublime_plugin
import functools
import sys, os
top_path = os.path.dirname(__file__) # Plugin directory
sys.path.append(top_path)
import syntaxchecker
import threading, queue
import subprocess
import tempfile


# Trigged when user input text
class UserEditListener(sublime_plugin.EventListener):

	def __init__(self):
		# Get the active window as current main window
		self.window = sublime.active_window()
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
			tempdir = tempfile.gettempdir()
			dot_file = os.path.join(tempdir, "graphvizer.dot")
			with open(file=dot_file, mode="w", encoding="utf-8") as fd:
				fd.write(contents)
			image_file = os.path.join(tempdir, "graphvizer.png")
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
		syntax_is_valid, error = syntaxchecker.check(contents)
		if syntax_is_valid:
			self.queue.put(contents, block=True, timeout=None)
		else:
			self.print(error)

	def print(self, text):
		self.window.run_command("print_to_graphvizer_panel", {"text": text})


#
class GraphvizerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		pass
