import sublime
import sublime_plugin


class ViewSavingStatus():
	def __init__(self):
		self.saving_status = dict()
		for window in sublime.windows():
			for view in window.views():
				file_syntax = view.settings().get('syntax')
				if file_syntax != "Packages/Graphviz/DOT.sublime-syntax":
					continue
				if view.file_name() is None:
					self.saving_status[view.id()] = False
				else:
					self.saving_status[view.id()] = True

	def append(self, view):
		if view.file_name() is None:
			self.saving_status[view.id()] = False
		else:
			self.saving_status[view.id()] = True

	# delete() is not necessary
	def delete(self, view):
		pass

	def exist_on_disk(self, view):
		# corner case: new a empty view and select a exist dot file to overwrite.
		# In this case, on_post_text_command() won't be invoked to append view,
		# but the file syntax is set to DOT. on_pre_save()->exist_on_disk() will raise
		# KeyError. We treat this case as "doesn't exist on disk" and the later call
		# of set_existence() will append the view to dict.
		return self.saving_status.get(view.id(), False)

	def set_existence(self, view):
		self.saving_status[view.id()] = True
