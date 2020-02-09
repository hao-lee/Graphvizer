import sublime
import sublime_plugin


class SetLayoutEngineCommand(sublime_plugin.TextCommand):
	def run(self, edit, layout_engine):
		self.view.settings().set("layout_engine", layout_engine)

	def is_checked(self, layout_engine):
		# Showing at the first time
		if self.view.settings().get("layout_engine") is None:
			self.view.settings().set("layout_engine", "dot") # Set default engine
			if layout_engine == "dot":
				return True

		if layout_engine == self.view.settings().get("layout_engine"):
			return True
		return False
