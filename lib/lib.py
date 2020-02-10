import tempfile
import os


def get_image_filepath(st_settings, view):
	dot_filepath = view.file_name()
	# image path
	image_dirname = None
	if st_settings.get("image_dir") == "same": # want to use the same directory as the dot file
		if dot_filepath is None: # file doesn't exist on disk
			image_dirname = tempfile.gettempdir()
		else: # file exist on disk
			image_dirname = os.path.dirname(dot_filepath)
	elif st_settings.get("image_dir") == "tmp":
		image_dirname = tempfile.gettempdir()
	else: # custom path
		image_dirname = st_settings.get("image_dir")

	# Check path existence
	if not os.path.exists(image_dirname):
		print("%s doesn't exist." %image_dirname)
	# Check path permission
	if not os.access(image_dirname, os.W_OK):
		print("%s doesn't have permission to write." %image_dirname)

	# image basename
	if dot_filepath is None: # Current file doesn't exist on disk, use temp image file
		image_basename = "temp~.png"
	else: # Current file exist on disk
		image_basename = os.path.splitext(os.path.basename(dot_filepath))[0] + ".png"

	return os.path.join(image_dirname, image_basename)
