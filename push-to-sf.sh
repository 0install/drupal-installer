#!/bin/sh
set -ex
USER=tal197
PROJECT=zero-install
LOCALDIR=/var/www/drupal
rsync -ri /home/project-web/$PROJECT/software/implementations/ $USER,$PROJECT@web.sourceforge.net:/home/project-web/$PROJECT/software/implementations
rsync -ia --exclude 'sites/default' $LOCALDIR/ $USER,$PROJECT@web.sourceforge.net:/home/project-web/$PROJECT/htdocs/drupal
