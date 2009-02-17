# -*- coding: utf-8 -*-"
"""
    MetaAjaxCheck
      - gets meta values from showMetaJSON action

    Usage: MetaAjaxCheck(pages,key,value,loadingtext,oncomplete)

    @param pages=page1;page2;   list of pages to search metas separated with ;
    @param key=string           key from which values shoud be searched from
    @param value=string         value of the key to search
    @param loadingtext="string"     text to show while searching
    @param oncomplete=url/"sring"   page/text to show when match is found

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
import re

def execute(macro, args):
    request = macro.request
    _ = macro.request.getText

    pages = key = value = complete = ''
    loadtext = "&nbsp;"

    if args is not None:
        args = args.split(',')
        exp = re.compile("^(.+)=(.+)$")
        for arg in args:
            match = exp.match(arg)
            opt = match.group(1)
            val = match.group(2)
            if opt == "pages":
                pages = val.replace(';',',')

            elif opt == "key":
                key = val

            elif opt == "value":
                value = val

            elif opt == "loadtext":
                loadtext = val.replace('"','')


            elif opt == "oncomplete":
                complete = val.replace('"',"'");


    html = unicode()
    html += u'''
  <script type="text/javascript" src="%s/gwikicommon/js/mootools-core-yc.js"></script>
    ''' % request.cfg.url_prefix_static

    html += '''
<script type="text/javascript">
window.addEvent('domready', function(){
    var pages = "%s";
    var search_key = "%s".replace(' ','');
    var search_value = "%s".replace(' ','');
    var complete = "%s";
    var loadtext = "%s";
''' %(pages, key, value, complete, loadtext)
    html += '''
    var ajax_result = $('ajax-result');
    ajax_result.set('html', loadtext);
    var getJSON = (function(){
        ajax_result.addClass('ajax_loading');
        var get = new Request.JSON({
            url: '',
            onComplete: function(result){
                var result_html = "";
                var result_match = "";
                result.each(function(pages){
                    for(pagename in pages){
                        result_html += "<h3>"+ pagename + "</h3>";
                       values = pages[pagename];
                       for(key in values){
                           val = values[key];
                           if(val != ""){
                            if(key == search_key && val == search_value){
                              result_match += "Found match for "+key+ "::"+val;
                                ajax_result.removeClass('ajax_loading');
                                $clear(loop);
                                $clear(timeout);
                                if(/'/.test(complete)){
                                   result_match = complete.replace(/'/g,"");
                                }else if(complete != ""){
                                    new Request.HTML({
                                        update : ajax_result
                                        }).post(complete);
                                    return;
                                }
                            }
                            result_html += "&nbsp;&nbsp;<b>"+ key + "</b> : " + values[key] + "<br>";
                           }
                       }
                        }
                    });
                //ajax_result.set('html', result_match + result_html);
                if(result_match == ""){
                    result_match = loadtext;
                    }
                ajax_result.set('html', result_match);
                }
            }).get({'action': 'showMetasJSON', 'args': pages});
        });
   getJSON();
    var loop = getJSON.periodical(10000,this);
    var stop_loop = (function(){
        $clear(loop);
        $('ajax-result').set('html', "<b>Operation timed out, try again later.</b>");
        $('ajax-result').removeClass('ajax_loading');
        });
    var timeout = stop_loop.delay(5*60*1000);
    });
</script>
<div id="ajax-result">
</div>
    '''
    return html
