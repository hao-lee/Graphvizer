import sublime
import sublime_plugin


class Panel():
	def __init__(self, window):
		self.window = window
		self.view = window.create_output_panel("graphvizer_panel")

	def print(self, text):
		self.view.run_command("select_all")
		self.view.run_command("insert", {"characters": text})
		self.window.run_command("show_panel", {"panel": "output.graphvizer_panel"})

class TestPanelCommand(sublime_plugin.WindowCommand):
	def run(self):
		panel = Panel(self.window)
		panel.print("test")