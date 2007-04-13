from MoinMoin.security import Permissions

class SecurityPolicy(Permissions):
    def save(self, editor, newtext, rev, **kw):

        # No problem to save if my base class agree
        if Permissions.save(self, editor, newtext, rev, **kw):
            from MoinMoin import wikiutil

            # save to graph file, if plugin available
            graphsaver = wikiutil.importPlugin(self.request.cfg,
                                               'action',
                                               'savegraphdata')

            if not graphsaver:
                return True
            else:
                path = editor.getPagePath()
                # If the page has not been created yet,
                # create its directory and save the stuff there
                if "underlay/pages" in path:
                    import os, re
                    path = re.sub(r'underlay/pages', 'data/pages', path, 1)
                    if not os.path.exists(path):
                        os.makedirs(path)

                graphsaver(editor.page_name, self.request,
                           newtext, path, editor)


                return True

        else:
            return False
