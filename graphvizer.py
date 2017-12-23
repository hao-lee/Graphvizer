import sublime
import sublime_plugin
import functools
import sys, os
top_path = os.path.dirname(__file__) # Plugin directory
sys.path.append(top_path)
import syntaxchecker


# Trigged when user input text
class UserEditListener(sublime_plugin.EventListener):
	def on_modified(self, view):
		# Detect language. Only process DOT file.
		file_syntax = view.settings().get('syntax')
		if "DOT.sublime-syntax" not in file_syntax:
			return
		# Get the contents of the whole file
		region = sublime.Region(0, view.size())
		contents = view.substr(region)
		# Check if the syntax is valid
		syntax_is_valid, error = syntaxchecker.check(contents)
		if syntax_is_valid:
			pass
		else:
			self.print(error)

	def print(self, text):
		window = sublime.active_window()
		window.run_command("print_to_graphvizer_panel", {"text": text})


#
class GraphvizerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		pass
