import sublime
import sublime_plugin
import os
import tempfile


class GvzSettings():
	def __init__(self):
		self.st_settings = sublime.load_settings("Graphvizer.sublime-settings")
		# Image file path
		self.image_filepath = None
		# Dot file directory
		self.dot_file_dirname = None

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
		if dot_filepath is None: # Current file doesn't exist on disk, use temp image file
			image_basename = "temp~.png"
		else: # Current file exist on disk
			image_basename = os.path.splitext(os.path.basename(dot_filepath))[0] + ".png"
		image_dirname = self.image_dir
		# Default location is the same directory as the dot file if it exist on disk.
		if image_dirname == "" and dot_filepath is not None:
			image_dirname = os.path.dirname(dot_filepath)
		elif image_dirname == "" and dot_filepath is None: # file doesn't exist on disk
			image_dirname = tempfile.gettempdir()
		elif image_dirname == "tmp":
			image_dirname = tempfile.gettempdir()
		else: # User custom directory
			pass
		# Check path existence
		if not os.path.exists(image_dirname):
			print("%s doesn't exist." %image_dirname)
		# Check path permission
		if not os.access(image_dirname, os.W_OK):
			print("%s doesn't have permission to write." %image_dirname)
		self.image_filepath = os.path.join(image_dirname, image_basename)

	def update_dot_file_dirname(self, dot_filepath):
		if dot_filepath is not None:
			self.dot_file_dirname = os.path.dirname(dot_filepath)
		else:
			self.dot_file_dirname = None
