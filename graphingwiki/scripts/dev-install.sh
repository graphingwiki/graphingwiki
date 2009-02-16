#!/usr/bin/env bash
# This shell script will install and run a GraphingWiki instance
# in standalone mode.
# Prerequisites:
# 1. unpacked moinmoin tarball (pointed by by $moinsrc)
# 2. graphingwiki svn checkout like so:
#    svn co http://svn.graphingwiki.python-hosting.com/ gw-svn
# 3. up to date graphviz
# (darwinports moin and graphviz aren't good enough)


moinsrc=$PWD/moin-1.8.2
gwsrc=$PWD/gw-svn/branches/durus-branch/graphingwiki
#gwsrc=$PWD/gw-svn
gwdata=$PWD/gw-data
gwinstall=$PWD/gw-install

function installmoin {
    (cd $moinsrc &&
    python setup.py install --prefix=$gwinstall)
}

function installgw {
    mkdir -p $gwdata 
    (cd $gwsrc &&
    python setup.py install --prefix=$gwinstall)
}

function makewiki {
    template=$gwinstall/share/moin
    cp -r $template/{data,underlay} $gwdata/
    cp $moinsrc/wikiserver{,config}.py $gwdata/
    echo "    docs = '$gwinstall/share/moin/htdocs'" >> $gwdata/wikiserverconfig.py
    cat $gwsrc/wikiconfig-add.txt >> $gwdata/wikiserverconfig.py
#     echo "    actions_excluded = []" >> $gwdata/wikiserverconfig.py
#     echo '    acl_rights_before = u"All:read,write,delete,revert,admin"' >> $gwdata/wikiconfig.py
    sed -e "s!moinmoin_dir =.*!moinmoin_dir = '$gwdata'!" < $moinsrc/wikiconfig.py > $gwdata/wikiconfig.py
    rm -f $gwdata/wiki || true
    ln -s . $gwdata/wiki
    find $gwdata/data/plugin -type l | xargs --no-run-if-empty rm
    python $gwinstall/bin/gwiki-install -v $gwdata

    # replace plugins with symlinks pointing at code
    # in the svn working copy, so your edits will show up in running code
    for pluginsubdir in action macro formatter parser xmlrpc; do
        ln -sf $gwsrc/graphingwiki/plugin/$pluginsubdir/*.py $gwdata/data/plugin/$pluginsubdir/
    done
    
}

set -e

installmoin
spdir=`echo $gwinstall/lib/python?.*/site-packages`

export PYTHONPATH=$gwsrc:$spdir:$gwdata:$PYTHONPATH
echo set PYTHONPATH to $PYTHONPATH
installgw
makewiki
sleep 1
echo start command:
echo "cd $gwdata; env PYTHONPATH=$PYTHONPATH python wikiserver.py"
(cd $gwdata; python wikiserver.py)
