installprefix=$HOME/src/gw-install
cd moin-1.8.2
python setup.py install --prefix=$installprefix
cd ..
cd graphingwiki-svn
python setup.py install --prefix=$installprefix
cd ..
mkdir gw-instance
cp -a gw-install/share/moin/{config,data,underlay} gw-instance/
patch config/wikiconfig.py <<EOF
--- ../gw-install/share/moin/config/wikiconfig.py	2009-02-04 10:12:49.000000000 +0200
+++ config/wikiconfig.py	2009-09-25 15:56:54.000000000 +0300
@@ -46,7 +46,7 @@
     #page_front_page = u"MyStartingPage"
 
     # b) if wiki content is maintained in many languages
-    #page_front_page = u"FrontPage"
+    page_front_page = u"FrontPage"
 
     # The interwiki name used in interwiki links
     #interwikiname = u'UntitledWiki'
@@ -81,7 +81,7 @@
     # For Twisted and standalone server, the default will automatically work.
     # For others, you should make a matching server config (e.g. an Apache
     # Alias definition pointing to the directory with the static stuff).
-    #url_prefix_static = '/moin_static182'
+    url_prefix_static = '/moin_static182'
 
 
     # Security ----------------------------------------------------------
@@ -166,3 +166,26 @@
     # Enable graphical charts, requires gdchart.
     #chart_options = {'width': 600, 'height': 300}
 
+    plugin_dirs = ['../gw-install/lib/python2.6/site-packages/graphingwiki/plugin']
+    superuser = [u"SuperFabio"]
+    
+    acl_rights_before = u"SuperFabio:read,write,delete,revert,invite,admin" 
+    
+    actions_excluded = []
+
+    from graphingwiki import install_hooks
+    install_hooks()
+    surge_action_limits = None
+    unzip_single_file_size = 1024 * 1024 * 1024 * 600
+    unzip_attachments_count = 1000
+    unzip_attachments_space = 1024 * 1024 * 1024 * 500
+
+
+    html_head = '' # omit if you already have something
+
+    for script in ['js/mootools-core-yc.js', \
+                   'js/sorttable-moo.js', \
+                   'simile/ajax/simile-ajax-api.js', \
+                   'simile/timeline/timeline-api.js']:
+        html_head += '<script src="%s" type="text/javascript"></script>' \
+            % (url_prefix_static + '/gwikicommon/' + script)
EOF
../gw-install/bin/moin server standalone --config-dir config
