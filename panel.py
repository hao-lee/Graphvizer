import sublime
import sublime_plugin
from datetime import datetime


# Use this class as a window command to print text to graphvizer_panel
class PrintToGraphvizerPanelCommand(sublime_plugin.WindowCommand):
	view = None
	def run(self, text):
		if self.view is None:
			self.view = self.window.create_output_panel("graphvizer_panel")
		dt = datetime.now()
		dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
		text =  "[%s] - %s\n" %(dt_str, text)
		self.view.run_command("append", {"characters": text})
		self.view.run_command("move_to", {"to": "eof"})
