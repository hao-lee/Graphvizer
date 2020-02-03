import sublime
import sublime_plugin
import functools
import os
from . import syntaxchecker
import threading, queue
import subprocess
import tempfile

class GvzSettings():
	def __init__(self):
		self.st_settings = sublime.load_settings("Graphvizer.sublime-settings")
		# Image file path
		self.image_filepath = None

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

	def update_image_filepath(self, dot_filepath):
		if dot_filepath is None: # Current file is not saved, use temp image file
			image_filename = "temp~.png"
		else:
			image_filename = os.path.splitext(os.path.basename(dot_filepath))[0] + ".png"
		# Use the default path
		if self.image_dir == "":
			self.image_filepath = os.path.join(tempfile.gettempdir(), image_filename)
			return
		# Check path existence
		if not os.path.exists(self.image_dir):
			print("%s doesn't exist. Use the default path instead." %self.image_dir)
			self.image_filepath = os.path.join(tempfile.gettempdir(), image_filename)
			return
		# Check path permission
		if not os.access(self.image_dir, os.W_OK):
			print("%s doesn't have permission to write. Use the default path instead." %self.image_dir)
			self.image_filepath = os.path.join(tempfile.gettempdir(), image_filename)
			return
		# OK, use configured image_dir
		self.image_filepath = os.path.join(self.image_dir, image_filename)


class ViewSavingStatus():
	def __init__(self):
		self.saving_status = dict()
		for window in sublime.windows():
			for view in window.views():
				file_syntax = view.settings().get('syntax')
				if file_syntax != "Packages/Graphviz/DOT.sublime-syntax":
					continue
				if view.file_name() is None:
					self.saving_status[view.id()] = False
				else:
					self.saving_status[view.id()] = True

	def append(self, view):
		if view.file_name() is None:
			self.saving_status[view.id()] = False
		else:
			self.saving_status[view.id()] = True

	# delete() is not necessary
	def delete(self, view):
		pass

	def is_saved(self, view):
		# corner case: new a empty view and select a exist dot file to overwrite
		# while saving it. In this case, on_post_text_command() won't be invoked
		# to append view, but the file syntax is set to DOT. on_pre_save()->is_saved()
		# will raise KeyError. We treat this case as "Not Saved" and set_saved()
		# will append the view to dict.
		return self.saving_status.get(view.id(), False)

	def set_saved(self, view):
		self.saving_status[view.id()] = True


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

			cmd = [gvzsettings.dot_cmd_path, self.intermediate_file, "-Tpng", "-o", gvzsettings.image_filepath]
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
			if syntax_is_valid:
				# Put the valid contents into the queue for graph rendering
				self.queue_rendering.put(contents, block=True, timeout=None)

	def rendering(self, view):
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
		if not gvzsettings.render_in_realtime:
			return
		self.rendering(view)

	# Update the image_filepath and trigger rendering when the file is saved
	def on_pre_save(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax != "Packages/Graphviz/DOT.sublime-syntax":
			return
		# The file is saved for the first time
		if not view_saving_status.is_saved(view):
			sublime.message_dialog("You save your dot file, so the image filename " \
				"has been changed according to your filename. Please close temp~.png " \
				"and reopen image again using keyboard shortcuts or menus.")
			view_saving_status.set_saved(view)
			gvzsettings.update_image_filepath(view.file_name())
			self.rendering(view)

	# Trigger rendering if setting the file syntax to DOT
	def on_post_text_command(self, view, command_name, args):
		if command_name == "set_file_type" \
				and args["syntax"] == "Packages/Graphviz/DOT.sublime-syntax":
			view_saving_status.append(view)
			gvzsettings.update_image_filepath(view.file_name())
			self.rendering(view)

	# Trigger rendering if opening a DOT file
	def on_load(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax == "Packages/Graphviz/DOT.sublime-syntax":
			view_saving_status.append(view)
			gvzsettings.update_image_filepath(view.file_name())
			self.rendering(view)

	# Update the image_filepath when switching between tabs
	def on_activated(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax == "Packages/Graphviz/DOT.sublime-syntax":
			gvzsettings.update_image_filepath(view.file_name())
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
