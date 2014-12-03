# -*- coding: iso-8859-1 -*-
"""
   MoinMoin - MetaTagCloud

   Based on TagCloud.py "Create tagcloud"
   @copyright: 2007 by Christian Groh

   Adapted for use in Graphingwiki to visualise metakeys
   @copyright: 2007 by Juhani Eronen

"""
from graphingwiki.editing import metatable_parseargs
from graphingwiki.util import NO_TYPE

Dependencies = ["namespace"]

def execute(macro, args):
   mode = 'keys'

   request = macro.request

   # get params
   if args:
      args = [x.strip() for x in args.split(',')]
   else:
      args = []

   kw = {}
   for arg in args:
      if '=' in arg:
         key, value = arg.split('=', 1)
         if key == "metaMaxTags":
            kw[str(key.strip())] = value
         if key == "metaShowMode":
            if value in ['keys', 'values']:
               mode = value

   args = filter(lambda x:
                 x.split('=')[0] not in ["metaMaxTags", "metaShowMode"],
                 args)

   try:
      maxTags = int(kw["metaMaxTags"])
   except (KeyError, ValueError):
      maxTags = 50

   #{level:hits , level:hits , ...}
   level = { 0 : 4 , 1 : 7 , 2 : 12 , 3 : 18 , 4 : 25 , 5 : 35 , 6 : 50 , 7 : 60 , 8 : 90 }

   tags = []

   if not args:
      args = ''
   else:
      args = ','.join(args)

   pagelist, metakeys, _ = metatable_parseargs(macro.request, args,
                                               get_all_pages = True)
    
   if not hasattr(request.graphdata, 'keys_on_pages'):
      request.graphdata.reverse_meta()

   for name in pagelist:
      page = request.graphdata.getpage(name)
      if mode == 'keys':
         tags.extend(x for x in page.get('meta', {}).keys())
         tags.extend(x for x in page.get('out', {}).keys() if x != NO_TYPE)
      else:
         for key in page.get('meta', {}).keys():
            if key in ['label', 'URL']:
               continue
#            print key, repr(page['meta'][key])
            tags.extend(x.strip('"') for x in page['meta'][key])
         for key in page.get('out', {}).keys():
            if key == NO_TYPE:
               continue
#            print repr(page['out'][key])
            tags.extend(page['out'][key])

   taglist = frozenset(tags)

   def sort(t):
      return t[1]

   show = []
   for tag in taglist:
      cnt = tags.count(tag)
      show.append((tag, cnt, tag))
   show.sort(key=sort, reverse=True)
   show = show[0:maxTags]
   show.sort()

   html = []

   url = request.script_root + '/' + request.page.page_name + \
         '?action=MetaSearch&amp;q='

   for tag in show:
      title = ""
      if mode == 'keys':
         data = request.graphdata.keys_on_pages.get(tag[2])
         if data:
            title = '\n'.join(x for x in 
                              sorted(request.graphdata.keys_on_pages.get(tag[2]), key=unicode.lower))
      else:
         data = request.graphdata.vals_on_pages.get(tag[2])
         if data:
            title = '\n'.join(x for x in
                              sorted(request.graphdata.vals_on_pages.get(tag[2]), key=unicode.lower))

      pagename = tag[0]
      hits = tag[1]

      #level0
      if hits < level[0]:
         html.append(u'<span style="font-size:0.65em;"><a title="%s" href="%s"> %s</a></span>' % (title, url + pagename, tag[0]))
      #level1
      elif hits < level[1]:
         html.append(u'<span style="font-size:0.75em;"><a title="%s" href="%s"> %s</a></span>' % (title, url + pagename, tag[0]))
      #level2
      elif hits < level[2]:
         html.append(u'<span style="font-size:0.9em;"><a title="%s" href="%s"> %s</a></span>'% (title, url + pagename, tag[0]))
      #level3
      elif hits < level[3]:
         html.append(u'<span style="font-size:1.0em;"><a title="%s" href="%s"> %s</a></span>'% (title, url + pagename, tag[0]))
      #level4
      elif hits < level[4]:
         html.append(u'<span style="font-size:1.05em;"><a title="%s" href="%s"> %s</a></span>'% (title, url + pagename, tag[0]))
      #level5
      elif hits < level[5]:
         html.append(u'<span style="font-size:1.1em;"><a title="%s" href="%s"> %s</a></span>'% (title, url + pagename, tag[0]))
      #level6
      elif hits < level[6]:
         html.append(u'<span style="font-size:1.15em;"><a title="%s" href="%s"> %s</a></span>'% (title, url + pagename, tag[0]))
      #level7
      elif hits < level[7]:
         html.append(u'<span style="font-size:1.2em;"><a title="%s" href="%s"> %s</a></span>'% (title, url + pagename, tag[0]))
      #level8
      elif hits < level[8]:
         html.append(u'<span style="font-size:1.25em;"><a title="%s" href="%s"> %s</a></span>'% (title, url + pagename, tag[0]))
      #level9
      else:
         html.append(u'<span style="font-size:1.3em;"><a title="%s" href="%s"> %s</a></span>'% (title, url + pagename, tag[0]))

   return ''.join(html)
