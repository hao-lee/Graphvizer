import sublime
import sublime_plugin
import sys


class SetLayoutEngineCommand(sublime_plugin.TextCommand):
	def __init__(self, view):
		super(SetLayoutEngineCommand, self).__init__(view)
		self.st_settings = sublime.load_settings("Graphvizer.sublime-settings")

	# Called when menu is checked
	def run(self, edit, layout_engine):
		old_layout_engine = self.view.settings().get("layout_engine")
		if old_layout_engine != layout_engine:
			self.view.settings().set("layout_engine", layout_engine)
			# https://github.com/sublimehq/sublime_text/issues/5#issuecomment-17322337
			_mod = sys.modules["Graphvizer.graphvizer"] # print(__name__) in graphvizer.py give us this string
			core_listener = _mod.__plugins__[0]
			core_listener.rendering(self.view) # render image

	# Called when menu is shown. Used to determine whether a menu should be checked.
	def is_checked(self, layout_engine):
		# If menus are shown for the first time, we need to set the default engine.
		if self.view.settings().get("layout_engine") is None:
			self.view.settings().set("layout_engine", self.st_settings.get("default_layout_engine"))

		if layout_engine == self.view.settings().get("layout_engine"):
			return True
		else:
			return False

	def is_enabled(self):
		if self.view.settings().get("syntax") == "Packages/Graphviz/DOT.sublime-syntax":
			return True
		else:
			return False
