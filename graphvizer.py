import sublime
import sublime_plugin
import os
from . import syntaxchecker
import threading, queue
import subprocess
import tempfile
from .command import *
from .lib import *


# Settings
gvzsettings = None
# view saving status
view_saving_status = ViewSavingStatus()

# load settings when the plugin host is ready
# https://forum.sublimetext.com/t/settings-not-loading-fast-enough/40634
def plugin_loaded():
	global gvzsettings
	gvzsettings = GvzSettings()
	gvzsettings.load()
	gvzsettings.add_callback()


# Trigged when user input text
class UserEditListener(sublime_plugin.EventListener):

	def __init__(self):
		super(UserEditListener, self).__init__()
		self.queued_view = []
		self.lock = threading.Lock()
		self.semaphore = threading.Semaphore(value=0) # list is empty
		# Start worker thread for graph rendering
		dot_thread = threading.Thread(target=self.dot_thread, daemon=True)
		dot_thread.start()
		self.intermediate_file = self.get_intermediate_dot_filepath()

	# Temporary file used to generate image
	def get_intermediate_dot_filepath(self):
		tempdir = tempfile.gettempdir()
		return os.path.join(tempdir, "intermediate.dot")

	def dot_thread(self):
		while self.semaphore.acquire():
			self.lock.acquire()
			view = self.queued_view.pop(0)
			self.lock.release()

			# Get the contents of the whole file
			region = sublime.Region(0, view.size())
			contents = view.substr(region)
			# Check if the syntax is valid
			syntax_is_valid, log = syntaxchecker.check(contents)
			self.print(log)
			if not syntax_is_valid:
				continue

			'''
			For purpose of cross-platform, we can't use TemporaryFile class because
			subprocess can't read it directly on Windows. Using a regular file is a
			good choice.
			'''
			with open(file=self.intermediate_file, mode="w", encoding="utf-8") as fd:
				fd.write(contents)

			cmd = [gvzsettings.dot_cmd_path, self.intermediate_file, "-Tpng", "-o", gvzsettings.image_filepath]
			# For Windows, we must use startupinfo to hide the console window.
			startupinfo = None
			if os.name == "nt":
				startupinfo = subprocess.STARTUPINFO()
				startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			# Default cwd is Sublime Text installation directory, such as `D:\Sublime Text`
			# We change it to the directory the same as dot file. See issue #16.
			process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
											stderr=subprocess.PIPE,
											startupinfo=startupinfo,
											cwd=gvzsettings.dot_file_dirname)
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

	def rendering(self, view):
		self.lock.acquire()
		try:
			for v in self.queued_view:
				if view.id() == v.id():
					return
			self.queued_view.append(view)
		finally:
			self.lock.release()

		self.semaphore.release()

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
		if not gvzsettings.render_in_realtime:
			return
		self.rendering(view)

	# Update the image_filepath and trigger rendering when the file is saved on disk for the first time.
	def on_pre_save(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax != "Packages/Graphviz/DOT.sublime-syntax":
			return
		# The file is saved for the first time
		if not view_saving_status.exist_on_disk(view):
			sublime.message_dialog("This is the first time the file is saved, "\
								"so the image filename has been changed according to the filename. "\
								"Please close temp~.png and reopen image again using keyboard shortcuts or menus.")
			view_saving_status.set_existence(view)
			gvzsettings.update_image_filepath(view.file_name())
			gvzsettings.update_dot_file_dirname(view.file_name())
			self.rendering(view)

	# Trigger rendering if setting the file syntax to DOT
	def on_post_text_command(self, view, command_name, args):
		if command_name == "set_file_type" \
				and args["syntax"] == "Packages/Graphviz/DOT.sublime-syntax":
			view_saving_status.append(view)
			gvzsettings.update_image_filepath(view.file_name())
			gvzsettings.update_dot_file_dirname(view.file_name())
			self.rendering(view)
		# Corner case: Copy the content from a dot file and paste to a plain text view,
		# the view will be set to `DOT` syntax automatically and on_modified() will be
		# triggered. We must set the image path before on_modified() is called. Otherwise,
		# image path will be None and subprocess will raise an list2cmdline error.
		if command_name == "paste" \
			and view.settings().get('syntax') == "Packages/Graphviz/DOT.sublime-syntax":
			gvzsettings.update_image_filepath(view.file_name())
			gvzsettings.update_dot_file_dirname(view.file_name())

	# Trigger rendering if opening a DOT file
	def on_load(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax == "Packages/Graphviz/DOT.sublime-syntax":
			view_saving_status.append(view)
			gvzsettings.update_image_filepath(view.file_name())
			gvzsettings.update_dot_file_dirname(view.file_name())
			self.rendering(view)

	# Update the image_filepath when switching between tabs
	def on_activated(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax == "Packages/Graphviz/DOT.sublime-syntax":
			gvzsettings.update_image_filepath(view.file_name())
			gvzsettings.update_dot_file_dirname(view.file_name())
			# No need to render as the image has been rendered when loading or modifying

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
		if gvzsettings.image_filepath is None:
			sublime.message_dialog("Image has not been rendered!")
			return False
		return True

	def open_image_window(self):
		if not self.check_image_filepath():
			return
		sublime.run_command("new_window")
		image_window = sublime.active_window()
		image_window.open_file(gvzsettings.image_filepath)
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
		self.window.open_file(gvzsettings.image_filepath)
		self.window.focus_group(0)

	def open_image_tab(self):
		if not self.check_image_filepath():
			return
		self.window.open_file(gvzsettings.image_filepath)
