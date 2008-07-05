from time import strptime, strftime, localtime

Dependencies = ['metadata']

time_format = "%b %d %Y %H:%M:%S %z"

def execute(macro, args):
    focus = ""
    
    if args:
        focus = args[1]
        try:
            strptime(time_format, focus)
        except ValueError:
            focus = ""

    focus = strftime(time_format, localtime())

    source_url = macro.request.page.url(macro.request) + \
                 "?action=recentchangestimeline"

    return """
    <div id="recentchangestimeline" style="height: 400px; margin: 2em;">
      <script type="text/javascript" src="%s/simile/recentchangestimeline.js"></script>

      <input type="hidden" id="recentchangestimelinefocus" value="%s" />
      <input type="hidden" id="recentchangestimelinesource" value="%s" />

      <noscript>
        <p>No JavaScript</p>
      </noscript>
    </div>
""" % (macro.request.cfg.url_prefix, focus, source_url)
