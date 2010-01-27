#!/usr/bin/env bash

function fail {
    echo "$@" 1>&2
    exit 1
}

role=$1
if test -z "$role"; then
  fail "usage: $0 <role>"
fi

set -e

umask 002

function rsync-install {
  rsync --exclude=.svn -av "$@"
}

farmdir=/roles/$role/public/secure_access/wikis/moin-farms

# underlays
rsync-install underlay/pages/ $farmdir/../moin-underlay/pages

# theme
rsync-install theme/raippa/ /usr/share/moin/htdocs/raippa
rsync-install src/plugin/ $farmdir/plugin

# javascript

rsync-install javascript/ /usr/share/moin/htdocs/raippajs

