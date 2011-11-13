#!/usr/bin/env python
import os, pwd, shutil, sys

from zeroinstall.injector import model
from zeroinstall.injector.requirements import Requirements
from zeroinstall.injector.driver import Driver
from zeroinstall.injector.config import load_config
from zeroinstall.support import tasks

mydir = os.path.dirname(os.path.abspath(__file__))
site_config = os.path.join(mydir, 'site-config.xml')
if not os.path.exists(site_config):
	print "Copy site-config.xml.template as site-config.xml and edit..."
	sys.exit(1)

drupal = "http://0install.net/tests/Drupal.xml"

config = load_config()
requirements = Requirements(site_config)
requirements.command = None
driver = Driver(config, requirements)
tasks.wait_for_blocker(driver.solve_and_download_impls())
selections = driver.solver.selections.selections

drupal_impl = selections[drupal]
drupal_root = drupal_impl.local_path or config.stores.lookup_any(drupal_impl.digests)

config_impl = selections[site_config]

site_config_settings = {}
for binding in config_impl.bindings:
	site_config_settings[binding.name] = binding.value

doc_root = site_config_settings["doc_root"]
apache_user = pwd.getpwnam(site_config_settings["apache_user"])

print "Selected Drupal", drupal_impl.version, "(" + drupal_root+ ")"
print "Document root:", doc_root
print "Apache user:", apache_user.pw_name

def ensure_dir(path):
	if not os.path.exists(path):
		print "mkdir -p", path
		try:
			os.makedirs(path)
		except OSError as ex:
			print ex
			sys.exit(1)

def ensure_link(impl, target, symlink):
	if os.path.islink(symlink):
		old_target = os.readlink(symlink)
		if old_target == target:
			return
		#print "rm " + symlink
		os.unlink(symlink)
	print "ln -s <{component}-{version}>/{name} {symlink}".format(
			component = os.path.basename(impl.feed),
			version = impl.version,
			name = os.path.basename(target),
			symlink = symlink)
	os.symlink(target, symlink)

def ensure_owner(path, user):
	if os.stat(path).st_uid != user.pw_uid:
		try:
			print "chown", user.pw_name, path
			os.chown(path, user.pw_uid, -1)
		except Exception as ex:
			print "chown failed:", ex

def cp(source, target):
	print "cp .../{name} {target}".format(name = os.path.basename(source), target = target)
	shutil.copyfile(source, target)

def rm(path):
	print "rm", path
	assert os.path.islink(path), path
	os.unlink(path)

ensure_dir(doc_root)

for name in os.listdir(drupal_root):
	full_name = os.path.join(drupal_root, name)
	if name.endswith('.php') or (name != 'sites' and os.path.isdir(full_name)):
		symlink = os.path.join(doc_root, name)
		ensure_link(drupal_impl, full_name, symlink)

sites_dir = os.path.join(doc_root, 'sites')
sites_default_dir = os.path.join(sites_dir, 'default')
ensure_dir(sites_default_dir)

files_dir = os.path.join(sites_default_dir, 'files')
ensure_dir(files_dir)

ensure_link(drupal_impl, 
	    os.path.join(drupal_root, 'sites', 'default', 'default.settings.php'),
	    os.path.join(doc_root, 'sites', 'default', 'default.settings.php'))

htaccess = os.path.join(doc_root, '.htaccess')
if not os.path.exists(htaccess):
	cp(os.path.join(drupal_root, '.htaccess'), htaccess)

settings_file = os.path.join(sites_default_dir, 'settings.php')
if not os.path.exists(settings_file):
	cp(os.path.join(drupal_root, 'sites', 'default', 'default.settings.php'), settings_file)

ensure_owner(files_dir, apache_user)
ensure_owner(settings_file, apache_user)

print "Updating modules..."

modules = {}
site_modules_dir = os.path.join(sites_dir, 'all', 'modules')
ensure_dir(site_modules_dir)

old_modules = set()
for module in os.listdir(site_modules_dir):
	full_path = os.path.join(site_modules_dir, module)
	if os.path.islink(full_path):
		old_modules.add(module)

for impl in selections.values():
	for dep in impl.dependencies:
		dep_impl = selections[dep.interface]
		for binding in dep.bindings:
			if isinstance(binding, model.EnvironmentBinding) and binding.name == 'drupal-modules':
				name = os.path.basename(binding.insert)
				impl_root = dep_impl.local_path or config.stores.lookup_any(dep_impl.digests)
				target = os.path.join(impl_root, binding.insert)
				if not os.path.exists(target):
					print "Module root {target} does not exist (in {interface} {version})".format(
							target = target,
							interface = dep.interface,
							version = dep_impl.version)
				ensure_link(dep_impl, target, os.path.join(site_modules_dir, name))
				if name in old_modules: old_modules.remove(name)

for module in old_modules:
	rm(os.path.join(site_modules_dir, module))

print "Done"
