import sublime
import sublime_plugin
from datetime import datetime


# Use this class as a window command to print text to graphvizer_panel
class GraphvizerPrintToPanelCommand(sublime_plugin.WindowCommand):

	def __init__(self, window):
		super(GraphvizerPrintToPanelCommand, self).__init__(window)
		self.view = self.window.create_output_panel("graphvizer_panel")

	def run(self, text):
		dt = datetime.now()
		dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
		text =  "[%s] - %s\n" %(dt_str, text)
		self.view.run_command("select_all")
		self.view.run_command("insert", {"characters": text})
