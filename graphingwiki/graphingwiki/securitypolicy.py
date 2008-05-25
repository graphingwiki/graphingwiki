# -*- coding: utf-8 -*-
import os

from MoinMoin.security import Permissions
from MoinMoin.util.antispam import SecurityPolicy as AntiSpam

class SecurityPolicy(AntiSpam):
    def save(self, editor, newtext, rev, **kw):
        if getattr(self.request.cfg, 'antispam', False) and not AntiSpam.save(self, editor, newtext, rev, **kw):
          return False
        # No problem to save if my base class agree
        if Permissions.save(self, editor, newtext, rev, **kw):
            from MoinMoin.wikiutil import importPlugin,  PluginMissingError

            try:
                # save to graph file, if plugin available
                graphsaver = importPlugin(self.request.cfg,
                                          'action',
                                          'savegraphdata')
            except PluginMissingError:
                return True

            if not graphsaver:
                return True
            else:
                underlaydir = self.request.cfg.data_underlay_dir
                pagedir = os.path.join(self.request.cfg.data_dir, 'pages')

                path = editor.getPagePath()
                # If the page has not been created yet,
                # create its directory and save the stuff there
                if underlaydir in path:
                    path = pagepath.replace(underlaydir, pagedir)
                    if not os.path.exists(path):
                        os.makedirs(path)

                graphsaver(editor.page_name, self.request,
                           newtext, path, editor)
                
                return True

        else:
            return False
