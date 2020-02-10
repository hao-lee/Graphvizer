import sublime
import sublime_plugin


class SetOutputFormatCommand(sublime_plugin.TextCommand):
	def __init__(self, view):
		super(SetOutputFormatCommand, self).__init__(view)
		self.st_settings = sublime.load_settings("Graphvizer.sublime-settings")

	# Called when menu is checked
	def run(self, edit, output_format):
		self.view.settings().set("output_format", output_format)

	# Called when menu is shown. Used to determine whether a menu should be checked.
	def is_checked(self, output_format):
		# If menus are shown for the first time, we need to set the default engine.
		if self.view.settings().get("output_format") is None:
			self.view.settings().set("output_format", self.st_settings.get("default_output_format"))

		if output_format == self.view.settings().get("output_format"):
			return True
		else:
			return False

	def is_enabled(self):
		return True
		if self.view.settings().get("syntax") == "Packages/Graphviz/DOT.sublime-syntax":
			return True
		else:
			return False
