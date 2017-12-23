import sublime
import sublime_plugin
from datetime import datetime


# Core utility class
class Panel():
	def __init__(self, window):
		self.window = window
		self.view = window.create_output_panel("graphvizer_panel")

	def print(self, text):
		#self.view.run_command("select_all")
		dt = datetime.now()
		dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
		text =  "[%s] - %s\n" %(dt_str, text)
		self.view.run_command("append", {"characters": text})
		#self.window.run_command("show_panel", {"panel": "output.graphvizer_panel"})


# Use this class as a window command to print text
class PrintToGraphvizerPanelCommand(sublime_plugin.WindowCommand):
	panel = None
	def run(self, text):
		if self.panel is None:
			self.panel = Panel(self.window)
		self.panel.print(text)