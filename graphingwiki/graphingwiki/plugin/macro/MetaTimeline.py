from graphingwiki.util import url_construct

from time import strptime, strftime, localtime

Dependencies = ['metadata']

time_format = "%b %d %Y %H:%M:%S +0000"

def execute(macro, args):
    focus = ""
    
    arglist = [x.strip() for x in args.split(',') if x]

    urlargs = {u'action': [u'metatimeline']}

    focus = strftime(time_format, localtime())

    for arg in arglist:
        if arg.startswith('timelinefocus='):
            try:
                strptime(arg.split('=')[1], time_format)
                focus = arg.split('=')[1]
            except ValueError:
                pass
        else:
            urlargs.setdefault(u'arg', list()).append(arg)

    source_url = url_construct(macro.request, urlargs)

    return """
    <div id="recentchangestimeline" style="height: 400px; margin: 2em;">
      <script type="text/javascript" src="%s/gwikicommon/simile/recentchangestimeline.js"></script>

      <input type="hidden" id="recentchangestimelinefocus" value="%s" />
      <input type="hidden" id="recentchangestimelinesource" value="%s" />

      <noscript>
        <p>No JavaScript</p>
      </noscript>
    </div>
""" % (macro.request.cfg.url_prefix_static, focus, source_url)
