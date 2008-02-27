#!/usr/bin/env bash
# This shell script will install and run a GraphingWiki instance
# in standalone mode.
# Prerequisites:
# 1. unpacked moinmoin tarball (pointed by by $moinsrc)
# 2. graphingwiki svn checkout like so:
#    svn co http://svn.graphingwiki.python-hosting.com/branches/moin-1.6-branch/moin gw-svn
# 3. up to date graphviz
# (darwinports moin and graphviz aren't good enough)


moinsrc=$PWD/moin-1.6.0
gwsrc=$PWD/gw-svn
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
    sed < $moinsrc/moin.py > $gwdata/moin.py \
        "s!docs = os.path.join.*!docs = '$gwinstall/share/moin/htdocs'!"
    cp $template/config/wikiconfig.py $gwdata/wikiconfig.py 

    cat $gwsrc/wikiconfig-add.txt >> $gwdata/wikiconfig.py
    echo "    actions_excluded = []" >> $gwdata/wikiconfig.py
    python $gwinstall/bin/gwiki-install -v $gwdata

    # replace plugins with symlinks pointing at code
    # in the svn working copy, so your edits will show up in running code
    for pluginsubdir in action macro formatter parser xmlrpc; do
        ln -sf $gwsrc/graphingwiki/plugin/$pluginsubdir/*.py $gwdata/data/plugin/$pluginsubdir/
    done

}

installmoin
spdir=`echo $gwinstall/lib/python?.*/site-packages`

export PYTHONPATH=$gwsrc:$spdir:$gwdata:$PYTHONPATH
echo set PYTHONPATH to $PYTHONPATH
installgw
makewiki
sleep 1
echo start command:
echo "cd $gwdata; env PYTHONPATH=$PYTHONPATH python moin.py"
(cd $gwdata; python moin.py)
