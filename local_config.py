# If you're running Drupal on sf.net then give the sf.net project name here.
# sf.net has a really old Python (2.4) and so can't run 0install. Therefore, we
# run locally with a special cache location and then rsync the whole thing
# across.
sf_project = None
#sf_project = 'zero-install'

from zeroinstall.zerostore import Store

def apply_local_config(config):
	if sf_project:
		sf_store = Store("/home/project-web/{project}/software/implementations".format(project = sf_project))
		# Hack: giving it twice prevents 0install from using the helper process
		config.stores.stores = [sf_store, sf_store]
