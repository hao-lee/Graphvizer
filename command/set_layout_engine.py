import sublime
import sublime_plugin


class SetLayoutEngineCommand(sublime_plugin.TextCommand):
	def __init__(self, view):
		super(SetLayoutEngineCommand, self).__init__(view)
		self.st_settings = sublime.load_settings("Graphvizer.sublime-settings")

	# Called when menu is checked
	def run(self, edit, layout_engine):
		self.view.settings().set("layout_engine", layout_engine)

	# Called when menu is shown. Used to determine whether a menu should be checked.
	def is_checked(self, layout_engine):
		# If menus are shown for the first time, we need to set the default engine.
		if self.view.settings().get("layout_engine") is None:
			self.view.settings().set("layout_engine", self.st_settings.get("default_layout_engine"))

		if layout_engine == self.view.settings().get("layout_engine"):
			return True
		return False
