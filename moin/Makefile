# Configuration variables, change these to fit your style
PKGDIR    = /usr/lib/python2.4/site-packages/MoinMoin
WIKIDIR   = $(HOME)/public_access/wiki

# Destination dirs
MOINDIR   = $(WIKIDIR)/config/MoinMoin
PLUGINDIR = $(WIKIDIR)/data/plugin

default:
	@echo "Copying MoinMoin-files"
	@mkdir -p -m 777 $(MOINDIR)
	@sed -e "s!MOINDIR!'$(MOINDIR)'!; s!PKGDIR!'$(PKGDIR)'!" \
	MoinMoin/__init__.py > $(MOINDIR)/__init__.py
	@find MoinMoin -name '[^_]*.py' | xargs -i cp '{}' $(MOINDIR)
	@chmod a+r $(MOINDIR)/*.py

	@echo "Copying plugins"
	@cp -R plugin/* $(PLUGINDIR)
	@find $(PLUGINDIR) -name 'CVS' -exec rm -rf {} +;
	@find $(PLUGINDIR) -name '*~*' -exec rm -rf {} +;
	@find $(PLUGINDIR) -name '*.py' -exec chmod a+r {} +;
	@echo "Make sure that your moin.cgi has cpe in sys.path, and that your"
	@echo "cpe- plugin- and config/MoinMoin dirs have permissions for apache!"
