import sublime
import sublime_plugin
import os
from . import syntaxchecker
import threading, queue
import subprocess
import tempfile
from .command import *


st_settings = None
def plugin_loaded():
	global st_settings
	st_settings = sublime.load_settings("Graphvizer.sublime-settings")
	add_callback()

def add_callback():
	st_settings.add_on_change("dot_cmd_path", reload_settings)
	st_settings.add_on_change("dot_timeout", reload_settings)
	st_settings.add_on_change("show_image_with", reload_settings)
	st_settings.add_on_change("image_dir", reload_settings)
	st_settings.add_on_change("render_in_realtime", reload_settings)

def reload_settings():
	print("Graphvizer Settings Changed")

def get_image_filepath(dot_filepath):
	# image path
	image_dirname = None
	if st_settings.get("image_dir") == "": # want to use the same directory as the dot file
		if dot_filepath is None: # file doesn't exist on disk
			image_dirname = tempfile.gettempdir()
		else: # file exist on disk
			image_dirname = os.path.dirname(dot_filepath)
	elif st_settings.get("image_dir") == "tmp":
		image_dirname = tempfile.gettempdir()
	else: # custom path
		image_dirname = st_settings.get("image_dir")

	# Check path existence
	if not os.path.exists(image_dirname):
		print("%s doesn't exist." %image_dirname)
	# Check path permission
	if not os.access(image_dirname, os.W_OK):
		print("%s doesn't have permission to write." %image_dirname)

	# image basename
	if dot_filepath is None: # Current file doesn't exist on disk, use temp image file
		image_basename = "temp~.png"
	else: # Current file exist on disk
		image_basename = os.path.splitext(os.path.basename(dot_filepath))[0] + ".png"

	return os.path.join(image_dirname, image_basename)

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

	def get_cwd(self, dot_filepath):
		if dot_filepath is None:
			return None
		else:
			return os.path.dirname(dot_filepath)

	def get_layout_engine(self):
		layout_engine = view.settings().get("layout_engine")
		if layout_engine is None: # layout engine has not been initialized
			layout_engine = st_settings.get("default_layout_engine")

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

			cmd = [st_settings.get("dot_cmd_path"), self.intermediate_file,
					"-K"+self.get_layout_engine(),
					"-Tpng", "-o", get_image_filepath(view.file_name())]
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
											cwd=self.get_cwd(view.file_name()))
			# Terminate the dot process if it takes too long to complete.
			try:
				stdout, stderr = process.communicate(timeout=st_settings.get("dot_timeout"))
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
		if not st_settings.get("render_in_realtime"):
			return
		self.rendering(view)

	# Update the image_filepath and trigger rendering when the file is saved on disk for the first time.
	def on_pre_save(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax != "Packages/Graphviz/DOT.sublime-syntax":
			return
		# The file is saved for the first time
		if view.settings().get("persistence") is None:
			sublime.message_dialog("This is the first time the file is saved, "\
								"so the image filename has been changed according to the filename. "\
								"Please close temp~.png and reopen image again using keyboard shortcuts or menus.")
			view.settings().set("persistence", True)
			self.rendering(view)

	# Trigger rendering if setting the file syntax to DOT
	def on_post_text_command(self, view, command_name, args):
		if command_name == "set_file_type" \
				and args["syntax"] == "Packages/Graphviz/DOT.sublime-syntax":
			if view.file_name() is None:
				pass
			else:
				view.settings().set("persistence", True)
			self.rendering(view)

	# Trigger rendering if opening a DOT file
	def on_load(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax == "Packages/Graphviz/DOT.sublime-syntax":
			view.settings().set("persistence", True)
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
		if st_settings.get("show_image_with") == "window":
			self.open_image_window()
		elif st_settings.get("show_image_with") == "layout":
			self.open_image_layout()
		else:
			self.open_image_tab()

	def open_image_window(self):
		image_filepath = get_image_filepath(self.window.active_view().file_name())
		if os.path.isfile(image_filepath):
			sublime.run_command("new_window")
			image_window = sublime.active_window()
			image_window.open_file(image_filepath)
			image_window.set_menu_visible(False)
			image_window.set_tabs_visible(False)
			image_window.set_minimap_visible(False)
			image_window.set_status_bar_visible(False)
		else:
			sublime.message_dialog("Image has not been rendered!")

	def open_image_layout(self):
		image_filepath = get_image_filepath(self.window.active_view().file_name())
		if os.path.isfile(image_filepath):
			self.window.set_layout({
				"cols": [0.0, 0.5, 1.0],
				"rows": [0.0, 1.0],
				"cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
			})
			self.window.focus_group(1)
			self.window.open_file(image_filepath)
			self.window.focus_group(0)
		else:
			sublime.message_dialog("Image has not been rendered!")

	def open_image_tab(self):
		image_filepath = get_image_filepath(self.window.active_view().file_name())
		if os.path.isfile(image_filepath):
			self.window.open_file(image_filepath)
		else:
			sublime.message_dialog("Image has not been rendered!")
