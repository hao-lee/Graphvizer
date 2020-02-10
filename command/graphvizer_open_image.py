import sublime
import sublime_plugin
import os
from ..lib import *


# Open image file
class GraphvizerOpenImageCommand(sublime_plugin.WindowCommand):

	def __init__(self, window):
		super(GraphvizerOpenImageCommand, self).__init__(window)
		self.st_settings = sublime.load_settings("Graphvizer.sublime-settings")

	def run(self):
		if self.st_settings.get("show_image_with") == "window":
			self.open_image_window()
		elif self.st_settings.get("show_image_with") == "layout":
			self.open_image_layout()
		else:
			self.open_image_tab()

	def open_image_window(self):
		image_filepath = get_image_filepath(self.st_settings, self.window.active_view().file_name())
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
		image_filepath = get_image_filepath(self.st_settings, self.window.active_view().file_name())
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
		image_filepath = get_image_filepath(self.st_settings, self.window.active_view().file_name())
		if os.path.isfile(image_filepath):
			self.window.open_file(image_filepath)
		else:
			sublime.message_dialog("Image has not been rendered!")
