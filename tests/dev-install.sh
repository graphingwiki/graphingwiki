#!/usr/bin/env bash
# This shell script will install and run a GraphingWiki instance
# in standalone mode.
# Prerequisites:
# 1. unpacked moinmoin tarball (pointed by by $moinsrc)
# 2. graphingwiki svn checkout like so:
#    svn co http://svn.graphingwiki.python-hosting.com/trunk/moin gw-svn
# 3. up to date graphviz

# (darwinports moin and graphviz aren't good enough)

# Warning!:
#    $gwdata and $gwinstall directories are removed before new install. 
#    So if you have some data there, it will be lost 
#    This is done because you might have there something that does not work


PWD=/Users/prikula/asennukset

moinsrc=$PWD/moin-1.6.3
gwsrc=$PWD/branches/moin-1.6-branch/graphingwiki
gwdata=$PWD/gw-data
gwinstall=$PWD/gw-install



function installmoin {

    mkdir -p $gwinstall

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
#    sed < $template/server/moin.py > $gwdata/moin.py \
#     "s!docs = '/usr/share/moin/htdocs'!docs = '$gwinstall/share/moin/htdocs'!"
    sed < $template/server/moin.py > $gwdata/moin.py \
      "s!docs = os.path.join(moinpath, 'wiki', 'htdocs')!docs = '$gwinstall/share/moin/htdocs'!"
    cp $template/config/wikiconfig.py $gwdata/wikiconfig.py
    echo "    actions_excluded = []" >> $gwdata/wikiconfig.py
    echo "    xmlrpc_putpage_trusted_only = 0" >> $gwdata/wikiconfig.py
    echo "    acl_rights_before = u\"All:read,write,delete,revert,admin\"" >> $gwdata/wikiconfig.py
    cat $gwsrc/wikiconfig-add.txt >> $gwdata/wikiconfig.py
    python $gwinstall/bin/gwiki-install -v $gwdata
}

#remove this, if you do not want to erase $gwinstall before every install
rm -rf $gwinstall

#remove this, if you do not want to erase $gwdata before every install
rm -rf $gwdata 

installmoin
spdir=`echo $gwinstall/lib/python?.*/site-packages`

#this is for mac install
gvdir=/usr/local/lib/graphviz/python

export PYTHONPATH=$spdir:$gvdir:$gwdata
echo set PYTHONPATH to $PYTHONPATH
installgw
makewiki
sleep 1
echo start command:
echo "cd $gwdata; env PYTHONPATH=$PYTHONPATH python moin.py"
(cd $gwdata; python moin.py)
