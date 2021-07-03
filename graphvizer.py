import sublime
import sublime_plugin
import os
import sys
from . import syntaxchecker
import threading, queue
import subprocess
import tempfile
# Although this file don't use modules in command/ directory, we still need to import it.
# Otherwise these commands won't be recognized by Sublime and key bindings will not work.
from .command import *
# import some auxiliary functions
from .lib import *


print(f"Graphvizer runtime env: ST {sublime.version()}, Py {sys.version}")
st_settings = None
def plugin_loaded():
	global st_settings
	st_settings = sublime.load_settings("Graphvizer.sublime-settings")
	add_st_settings_callback()
	# The file views and unsaved views opened during Sublime Text startup won't trigger any member
	# function in CoreListener class. We must scan all views and filter the DOT views. Then
	# we will render the image for each DOT view and set a suitable saving status for it.
	_mod = sys.modules[__name__]
	core_listener = _mod.__plugins__[0]
	for view in sublime.active_window().views():
		if view.settings().get('syntax') != "Packages/Graphviz/DOT.sublime-syntax":
			continue
		core_listener.rendering(view) # Initial rendering
		if view.file_name() is not None: # File exists on disk
			view.settings().set("persistence", True) # Set a suitable saving status for this DOT view

def add_st_settings_callback():
	st_settings.add_on_change("dot_cmd_path", st_settings_changes)
	st_settings.add_on_change("dot_timeout", st_settings_changes)
	st_settings.add_on_change("show_image_with", st_settings_changes)
	st_settings.add_on_change("image_dir", st_settings_changes)
	st_settings.add_on_change("render_in_realtime", st_settings_changes)

def st_settings_changes():
	print("Graphvizer Settings Changed")


# Core code
class CoreListener(sublime_plugin.EventListener):

	def __init__(self):
		super(CoreListener, self).__init__()
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

	def get_cwd(self, view):
		dot_filepath = view.file_name()
		if dot_filepath is None:
			return None
		else:
			return os.path.dirname(dot_filepath)

	def get_layout_engine(self, view):
		layout_engine = view.settings().get("layout_engine")
		if layout_engine is None: # layout engine has not been initialized
			layout_engine = st_settings.get("default_layout_engine")
		return layout_engine

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
					"-K" + self.get_layout_engine(view),
					"-T" + get_output_format(st_settings, view),
					"-o", get_image_filepath(st_settings, view)]
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
											cwd=self.get_cwd(view))
			# Terminate the dot process if it takes too long to complete.
			try:
				stdout, stderr = process.communicate(timeout=st_settings.get("dot_timeout"))
			except subprocess.TimeoutExpired:
				process.kill()
				stdout, stderr = process.communicate()
			if len(stdout) != 0:
				self.print(stdout.decode().strip())
			if len(stderr) != 0:
				self.print(stderr.decode().strip())

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
		if st_settings.get("render_in_realtime"):
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

		# If `render_in_realtime` is enabled, we don't need to render on save as this
		# has been done in on_modified().
		if not st_settings.get("render_in_realtime"):
			self.rendering(view)

	# Trigger rendering if setting the file syntax to DOT
	def on_post_text_command(self, view, command_name, args):
		if command_name == "set_file_type" \
				and args["syntax"] == "Packages/Graphviz/DOT.sublime-syntax":
			if view.file_name() is None:
				pass
			else:
				view.settings().set("persistence", True)
			if st_settings.get("render_in_realtime"):
				self.rendering(view)

	# Called condition: open a *file* while Sublime Text has already been started.
	# The file opened automatically during Sublime Text startup won't trigger this function.
	# New a view won't trigger this function.
	def on_load(self, view):
		file_syntax = view.settings().get('syntax')
		if file_syntax == "Packages/Graphviz/DOT.sublime-syntax":
			view.settings().set("persistence", True)
			if st_settings.get("render_in_realtime"):
				self.rendering(view)

	def print(self, text):
		# Get the active window as current main window
		current_window = sublime.active_window()
		current_window.run_command("print_to_panel", {"text": text})
