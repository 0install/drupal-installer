#!/usr/bin/env python
import os, pwd, shutil, sys

from zeroinstall.injector import model
from zeroinstall.injector.requirements import Requirements
from zeroinstall.injector.driver import Driver
from zeroinstall.injector.config import load_config
from zeroinstall.support import tasks

doc_root = None
apache_user = None

from config import *

if not doc_root or not apache_user:
	print "Edit config.py with your local settings and try again"
	sys.exit(1)

apache_user = pwd.getpwnam(apache_user)

print "Document root:", doc_root

drupal = "http://0install.net/tests/Drupal.xml"

config = load_config()
requirements = Requirements(drupal)
requirements.command = None
driver = Driver(config, requirements)
tasks.wait_for_blocker(driver.solve_and_download_impls())

drupal_impl = driver.solver.selections.selections[drupal]
drupal_root = drupal_impl.local_path or config.stores.lookup_any(drupal_impl.digests)

print "Selected Drupal", drupal_impl.version
print "(" + drupal_root+ ")"

def ensure_dir(path):
	if not os.path.exists(path):
		print "mkdir -p", path
		try:
			os.makedirs(path)
		except OSError as ex:
			print ex
			sys.exit(1)

def ensure_link(target, symlink):
	if os.path.islink(symlink):
		old_target = os.readlink(symlink)
		if old_target == target:
			return
		#print "rm " + symlink
		os.unlink(symlink)
	print "ln -s .../{name} {symlink}".format(name = os.path.basename(target), symlink = symlink)
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

ensure_dir(doc_root)

for name in os.listdir(drupal_root):
	full_name = os.path.join(drupal_root, name)
	if name.endswith('.php') or (name != 'sites' and os.path.isdir(full_name)):
		symlink = os.path.join(doc_root, name)
		ensure_link(full_name, symlink)

sites_dir = os.path.join(doc_root, 'sites')
sites_default_dir = os.path.join(sites_dir, 'default')
ensure_dir(sites_default_dir)

files_dir = os.path.join(sites_default_dir, 'files')
ensure_dir(files_dir)

ensure_link(os.path.join(drupal_root, 'sites', 'default', 'default.settings.php'),
	    os.path.join(doc_root, 'sites', 'default', 'default.settings.php'))

htaccess = os.path.join(doc_root, '.htaccess')
if not os.path.exists(htaccess):
	cp(os.path.join(drupal_root, '.htaccess'), htaccess)

settings_file = os.path.join(sites_default_dir, 'settings.php')
if not os.path.exists(settings_file):
	cp(os.path.join(drupal_root, 'sites', 'default', 'default.settings.php'), settings_file)

ensure_owner(files_dir, apache_user)
ensure_owner(settings_file, apache_user)

print "Done"
