import sublime
import sublime_plugin
import functools


# Trigged when user input text
class UserEditListener(sublime_plugin.EventListener):
	def on_modified_async(self, view):
		pass

#
class GraphvizerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		pass
