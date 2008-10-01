# -*- coding: utf-8 -*-"
"""
    MetaAjaxCheck
      - gets meta values from showMetaJSON action

    @copyright: 2008  <lauripok@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""
Dependencies = ['showMetaJSON']

def execute(macro, args):
    request = macro.request
    _ = macro.request.getText

    if args is None:
        args = ''

    html = unicode()
    html += u'''
  <script type="text/javascript" src="%s/common/js/mootools-1.2-core-yc.js"></script>
    ''' % request.cfg.url_prefix_static

    html += '''
<script type="text/javascript">
window.addEvent('domready', function(){
    var pages = "%s";
    var ajax_result = $('ajax-result');
    ajax_result.set('text', 'Checking:');
    var getJSON = new function(){
        ajax_result.addClass('ajax_loading');
        var get = new Request.JSON({
            url: '',
            onComplete: function(result){
                var result_html = "";
                result.each(function(pages){
                    for(pagename in pages){
                        result_html += "<h3>"+ pagename + "</h3>";
                       values = pages[pagename];
                       for(key in values){
                           if(values[key] != ""){
                            result_html += "&nbsp;&nbsp;<b>"+ key + "</b> : " + values[key] + "<br>";
                           }
                       }
                        }
                    });
                ajax_result.removeClass('ajax_loading');
                ajax_result.set('html', result_html);
                }
            }).get({'action': 'showMetasJSON', 'args': pages});
        };

    
    });
</script>
<div id="ajax-result">
</div>
    ''' % args
    return html
