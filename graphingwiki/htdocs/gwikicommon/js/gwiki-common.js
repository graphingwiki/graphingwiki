/*
 gwiki-common.js
 - Collection of js functions and classes used by graphingwiki.
 License:	MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2011 by Lauri Pokka
 */

/* Add "enable js" cookie */
if (!Cookie.read('js')) {
    Cookie.write('js', true, {
        duration: 100 * 365,
        domain: window.location.hostname
    });

    //Prevent reload loops if cookies are disabled
    if (Cookie.read('js')) {
        window.location.reload();
    }
}

window.dateformat = '%Y-%m-%d';
window.GWIKISEPARATOR = '-gwikiseparator-';


window.addEvent('domready', function() {

    var src = $$('script[src$=gwiki-common.js]')[0].get('src').replace('js/gwiki-common.js', '');

    var loader = new GwikiImport(src);

    // MetaFormEdit improvements
    var fields = $$('.metaformedit');
    if (fields.length > 0) {
        loader.load('MetaFormEdit', function() {
            new MetaFormEdit(fields[0].getParent('form'));
        });
    }

    // Apply MooTools tooltips to elements with .mt-tooltip class
    var tooltips = new Tips('.mt-tooltip', {'className': 'mootip'});

    // Apply MetaTable improvements
    var tables = $$('div.metatable[data-options]');
    if (tables.length > 0) {
        loader.load('MetaTable', function() {
            tables.each(function(div, i) {

                new MetaTable(div.getElement('table'), {
                    tableArguments: JSON.decode(decodeURIComponent(div.getAttribute('data-options'))),
                    separator: GWIKISEPARATOR
                });
            });
        });
    }

    // InterMetaTable
    if ($$('div.InterMetaTable').length) {
        loader.load('MetaTable', function(){
            $$('div.InterMetaTable').each(function(table){
                var opts = JSON.decode(decodeURIComponent(table.getAttribute('data-options')));
                new InterMetaTable(table, opts);
            });
        });
    }

    // Inline Edit
    if ($$('dl:not(.collab_list) dt').length && $$('dl:not(.collab_list) dd').length) {
        loader.load('InlineEditor', function() {
            $$('.gwikiinclude').include(document.body).each(initInlineMetaEdit);
        });
    }

    // AttachTree
    if ($$('.attachtree_area')) {
        loader.load('AttachTree', function() {
            $$('.attachtree_area').each(function(el) {
                new AttachTree(el);
            });
        });
    }

    // DynamicTextareas for textareas with .dynamic
    if ($$('textarea.dynamic')) {
        loader.load('DynamicTextarea', function(){
            $$('textarea.dynamic').setStyles({
                'resize': 'none',
                'overflow': 'hidden'
            });
            
	    document.id(document.body).addEvent('focus:relay(textarea.dynamic)', function(e){
                if (!document.id(e.target).retrieve('dynamic')) {
                    new DynamicTextarea(e.target);
                    document.id(e.target).store('dynamic', true).focus();
                }
            });
        });
    }

    //DnD file attachment upload
    initDnDUpload(document.window);
});

Element.Events.shiftclick = {
    base: 'click', // the base event type
    condition: function(event) {
        if (event.shift) {
            event.preventDefault();
            return true;
        }
    }
};

Request.SetMetas = new Class({
    Extends : Request.JSON,
    options: {
        //onConflict: function(){}
        method: 'post',
        checkArgs: '',
        checkData: {}
    },
    checkAndSend: function() {
        var args = arguments;
        new Request.GetMetas({
            onSuccess: function(json) {
                var failreason = "";
                if (Object.every(this.options.checkData, function(metas, page) {
                    return json[page] && Object.every(metas, function(values, key) {
                        values = values.filter(function(v) {
                            return v != '';
                        });
                        if (!json[page][key]) json[page][key] = [];
                        if (json[page][key].length != values.length || !values.every(function(value) {
                            return json[page][key].contains(value);
                        })){
                            failreason = JSON.encode(values) + " has been changed to " +JSON.encode(json[page][key]);
                        }
                        return failreason === "";
                    });
                }) || confirm("Data has changed after you loaded this page, do you want to overwrite changes? \n " +
                    failreason.slice(0,500))) {
                    this.send(args);
                } else {
                    this.fireEvent('conflict');
                }
            }.bind(this)
        }).get(this.options.checkArgs);
    },

    onSuccess: function (json) {
        if (json.status == "ok") {
            this.fireEvent('complete', arguments).fireEvent('success', arguments).callChain();
        } else {
            if (json.msg && json.msg[0]) alert(json.msg[0]);
            else alert("Save failed for unknown reason.");
        }
    }
});

/*
    Retrieves metas using incGetMetaJSON and local storage as cache.
    Usage example:
        new Request.GetMetas({
            args: 'CategoryTest',
            onSuccess: function(metas){
                //do something...
            }
        }).get();
*/
Request.GetMetas = new Class({
    Extends: Request.JSON,

    options: {
        args: "",
        cacheNamespace: "metaCache",
        link: "chain"
    },

    get: function(args, onlyvalues){
        if (!this.check(args, onlyvalues)) return this;
        args = args || this.options.args;
        this._metaArg = args || window.location.pathname;
        this._onlyvalues = onlyvalues;

        var opts = {
            method: 'get',
            url: '?action=incGetMetaJSON&formatted=true&args=' + encodeURIComponent(args)
        };

        if (onlyvalues) {
            opts.url = "?action=incGetMetaJSON&formatted=true&getvalues=" + encodeURIComponent(args);
        }

        if ("localStorage" in window) {
            var ls = window.localStorage;
            var namespace = this.options.cacheNamespace;

            if (this._onlyvalues) namespace += ".values";
            var cached = JSON.decode(ls[namespace +"_" + this._metaArg]);
            if (cached && cached.handle && cached.formatted) opts.url += "&handle=" + encodeURIComponent(cached.handle);
            //try to maintain incGetMeta-cache integrity in case user quits page before we get to save results
            this.unloadEvent = function(){
                delete ls[namespace +"_" + this._metaArg];
            }.bind(this);
            document.window.addEvent('unload',this.unloadEvent);
        }

        return this.send(opts);
    },

    onSuccess: function(json, text) {
        var handle = json[1];
        var data = json[2];
        var formatted = json.length > 3? json[3]: {};

        var results = {};
        var args = this._metaArg, ls, namespace;
        if ("localStorage" in window) {
            ls = window.localStorage;
            namespace = this.options.cacheNamespace;
            if (this._onlyvalues) namespace += ".values";
            //get stuff from cache only if the incGetMeta session is alive
            if (json[0]) {
                results = (JSON.decode(ls[namespace +"_"+args]) || {metas:{}})['metas'];
                formatted = Object.merge((JSON.decode(ls[namespace +"_"+args]) || {formatted:{}})['formatted'], formatted);
            }
        }

        var page, i, j;

        //deleted pages
        for (i=0; i < data[0].length; i++){
            page = data[0][i];
            if (results[page]) delete results[page];
        }

        //new pages/changes
        Object.each(data[1], function(metas, page){
            if (!results[page]) results[page] = {};
            Object.each(metas, function(vals, key){
                if (!results[page][key])results[page][key] = [];

                var deleted = vals[0];
                for (i=0; i < deleted.length; i++) {
                    j = results[page][key].indexOf(deleted[i]);
                    if (j >= 0) results[page][key].shift(j, 1);
                }

                var added = vals[1];
                for (i=0; i < added.length; i++) {
                    results[page][key].push(added[i]);
                }
            });
        });

        //save metas to cache, purge old data if localStorage gets full
        if ("localStorage" in window) {
            var indexName = this.options.cacheNamespace + ".items";

            var items = JSON.decode(ls[indexName]);
            if (!items) items = ls[indexName] = [];

            while (true) {
                try {
                    ls[namespace +"_"+args] = JSON.encode({handle: handle, metas: results, formatted: formatted});
                    items.erase(args).push(args);
                    ls[indexName] = JSON.encode(items);
                    break;

                } catch(e) {
                    if (items.length > 0) {
                        delete ls[items.shift()];
                    } else {
                        break;
                    }

                }
            }
            ls[indexName] = JSON.encode(items);
            document.window.removeEvent('unload',this.unloadEvent);

        }

        this.fireEvent('complete', [results, formatted, json, text])
            .fireEvent('success', [results, formatted, json, text])
            .callChain();
    }
});

var unescapeId = function(id) {
    return id.split(/_([0-9a-f]{2})_/).map(
        function(s) {
            if (s.test(/^[0-9a-f]{2}$/)) {
                return String.fromCharCode(s.toInt(16));
            } else {
                return s;
            }
        }).join("");
};


var initDnDUpload = function(el){
    if (!window.addEventListener) return;

    function noAction(e) {
        e.stopPropagation();
        e.preventDefault();
    }


    var overlay = null;

    el.addEventListener("dragenter", noAction, false);
    el.addEventListener("dragexit", noAction, false);
    el.addEventListener("dragover", noAction, false);
    el.addEventListener("drop", function(e) {
        e.stopPropagation();
        e.preventDefault();

        if (overlay) overlay.cancel();

        if (typeof(window.FileReader) == 'undefined' || typeof(window.FormData) == 'undefined') {
            // FailBack file uploader using normal form
            if (confirm("Ajax file uploading not supported by your browser, proceed to normal AttachFile action?")) {
                var url = window.location.href;
                var action = "?action=AttachFile";
                window.location.href = window.location.search ? url.replace(window.location.search, action) : url + action;
            }
        } else {
            // Upload using FileReader & xmlhttprequest + formdata
            var files = e.dataTransfer.files;

            if (files.length > 0) {
                overlay = new Overlay({
                    width: '650px',
                    onBuild: function() {
                        this.editor.grab(new Element('h3[text=Attach to page]'));
                        var div = new Element('div').inject(this.editor);
                        var ul = new Element('ul').inject(div);
                        var status = [];
                        var names = [];
                        for (var i = 0; i < files.length; i++) {
                            status.push(new Element('span'));
                            names.push(new Element('span').set('text', files[i].name));
                            ul.grab(new Element('li').adopt(names[i], status[i]));
                        }

                        var overwrite = false;
                        var failed = null;

                        var progress = new Element('div').inject(new Element('div.progress.hidden').inject(div));

                        div.grab(new Element('input[type=button][value=Send]').addEvent('click', function(e) {
                            var xhr = new XMLHttpRequest();
                            xhr.open('POST', '?action=ajaxUtils&util=uploadFile', true);

                            var text = new Element('span[text= ]').inject(progress.empty());
                            progress.getParent().removeClass('hidden');

                            var data = new FormData();
                            xhr.upload.addEventListener('progress', function(event) {
                                var percent = parseInt(event.loaded / event.total * 100, 10);
                                progress.setStyle('width', percent + '%');
                                text.set('text', percent + '%');
                            }, false);
                            
                            xhr.onreadystatechange = function(event) {
                                if (event.target.readyState == 4) {
                                    if (event.target.status == 200) {
                                        text.set('text', ' complete!');
                                        var json = JSON.decode(xhr.responseText);
                                        failed = json.failed;

                                        for (var i = 0; i < files.length; i++) {
                                            new Request.HTML({
                                                data: 'action=ajaxUtils&util=format&text=' + encodeURIComponent("[[attachment:" + files[i].name + "]]"),
                                                update: names[i]
                                            }).send();

                                            if (json.success.contains(files[i].name)) {
                                                status[i].set('text', "success").setStyles({
                                                    'font-style': 'italic',
                                                    'color': 'green',
                                                    'margin-left': '15px'
                                                });
                                            }else if (failed.contains(files[i].name)) {
                                                status[i].set('text', "failed, file already in attachments!").setStyles({
                                                    'font-style': 'italic',
                                                    'color': 'red',
                                                    'margin-left': '15px'
                                                });

                                                document.id(e.target).removeClass('hidden').set('value', 'Overwrite');
                                                overwrite = true;
                                            }
                                            progress.getParent().addClass('hidden');
                                        }
                                    }
                                    else {
                                        text.set('text', ' Upload failed!');
                                    }
                                }
                            };

                            for (var i = 0; i < files.length; i++) {
                                if (failed && !failed.contains(files[i].name)) continue;
                                data.append("file" + i, files[i]);
                            }

                            if (overwrite) data.append("overwrite", 1);
                            
                            xhr.send(data);

                            document.id(e.target).addClass('hidden');

                        }).setStyle('font-size', 'larger'));
                    }
                });
            }
        }
    }, false);



};

Slick.definePseudo('nth-include', function(n){
    var node = this, count = 0;
    while ((node = node.parentNode)) {
        if (node.className && node.className.test("gwikiinclude")) count++;
    }
    return count === +n
});

var initInlineMetaEdit = function (base) {
    //do not attach inline edit if MetaFormEdit is running
    if (!base.getElement('dl:not(.collab_list)') || base.getElement('dl').getParent('form')) return;

    var include_level = base.getParents('div.gwikiinclude').length + +base.hasClass('gwikiinclude');
    var metas, formatted, editor, page = "";

    if (base.hasClass('gwikiinclude')) page = unescapeId(base.id).split(GWIKISEPARATOR)[0];

    base.addEvent('mouseover:relay(dl:nth-include('+include_level+')):once', function() {
        new Request.GetMetas({
            args: page,
            onSuccess: function(results, f) {
                page = Object.keys(results)[0];
                metas = results[page];
                formatted = f;
                base.getElements('dd:nth-include('+include_level+')').each(function(dd) {
                    var dt = dd.getPrevious('dt'),
                        index = getMetaIndex(dt),
                        key = getKey(dt),
                        el = dd.clone(),
                        value;
                    el.getElements('span.anchor').destroy();
                    if (el.getElement('p')) el = el.getElement('p');
                    value = el.get('html').trim();
                    if (value !== "" && metas[key].indexOf(value) === -1) value = Object.keyOf(formatted, value);

                    //add empty string to meta-object to point empty meta values
                    if (value === "" && dd.getElements('img').length === 0) {
                        if (!metas[key]) metas[key] = [];
                        metas[key].splice(index, 0, "");
                    }else if (index != metas[key].indexOf(value)){
                        //fix order of metas since incMetaGet does not preserve it
                        metas[key].splice(index, 0, value);
                        for (var i = index+1; i < metas[key].length; i++) {
                            if (metas[key][i] === value) {
                                metas[key].splice(i, 1);
                                break;
                            }
                        }
                    }
                    if (value === false) alert("fail!")
                });

            }
        }).get();
    });

    //add a '+' button for adding values to empty metas (foo::)
    base.getElements('dd:nth-include('+include_level+')').each(function(dd) {
        if (dd.get('text').clean() === "" && dd.getElements('img').length === 0) {

            var dt = dd.getPrevious('dt');

            dt.grab(new Element('a', {
                'class': 'jslink plus',
                'events': {
                    'click': function() {
                        this.addClass('hidden');
                        dd.set('html', '&nbsp;');
                        editValue(dd);
                    }
                }
            }));

        }
    });

    var getKey = function(dt) {
        return dt.get('text');
    };

    var DtKeyCache = null;
    var DtElCache = null;

    var getMetaIndex = function(dt) {
        var key = getKey(dt);

        if (!DtKeyCache) {
            DtElCache = base.getElements('dt:nth-include(' + include_level + ')');
            DtKeyCache = DtElCache.map(getKey);
        }
        var dts = [];
        DtKeyCache.each(function(dtKey, i) {
            if (dtKey === key) dts.push(DtElCache[i])
        });

        return dts.indexOf(dt);
    };

    base.addEvent('shiftclick:relay(dd:not(.edit):nth-include('+include_level+'))', function(event) {
        event.preventDefault();

        var dd = event.target;
        if (dd.get('tag') != "dd") dd = dd.getParent('dd');
        editValue(dd);
    });

    var editValue = function(dd) {
        if (metas == null) {
            editValue.delay(100, this, dd);
            if (dd.getElements('.waiting').length == 0)
                dd.grab(new Element('span.waiting').set('html', '&nbsp;'), 'top');
            return;
        } else {
            dd.getElements('.waiting').destroy();
        }

        var keyEl = dd.getPrevious('dt');
        var key = getKey(keyEl);
        var index = getMetaIndex(keyEl);

        var oldValue = metas[key][index];

        if (editor) editor.cancel();

        dd.addClass('edit');

        editor = new InlineEditor(dd, {
            oldValue: oldValue,
            key: key,
            inline: true,
            width: 40,
            size: 'large',
            onSave: function (newValue) {
                var args = {};
                args[page] = {};

                var vals = Array.clone(metas[key]);
                args[page][key] = vals;
                var oldData = Object.clone(args);
                vals[index] = newValue;

                new Request.SetMetas({
                    data: 'action=setMetaJSON&args=' + encodeURIComponent(JSON.encode(args)),
                    checkArgs: page,
                    checkData: oldData,
                    onSuccess: function() {
                        metas[key] = vals;
                        editor.exit();
                        editor = null;
                    }.bind(this)
                }).checkAndSend();
            },
            onCancel: function(){
                if (oldValue == "") {
                    dd.set('html', '');
                    keyEl.getElement('.plus.hidden').removeClass('hidden');
                }
            },
            onExit: function() {
                dd.removeClass('edit');
                editor = null;
            }
        });
    };

    base.addEvent('shiftclick:relay(dt:not(.edit):nth-include('+include_level+'))', function(event) {
        event.preventDefault();

        var dt = event.target;
        if (dt.get('tag') != "dt") dt = dt.getParent('dt');

        editKey(dt);
    });

    var editKey = function(dt) {
        if (metas == null) {
            editValue.delay(100, this, dt);
            if (dt.getElements('.waiting').length == 0)
                dt.grab(new Element('span.waiting').set('html', '&nbsp;'), 'top');
            return;
        } else {
            dt.getElements('.waiting').destroy();
        }
        var key = getKey(dt);
        var index = getMetaIndex(dt);

        if (!metas[key] || metas[key][index] == "") return;

        if (editor) editor.cancel();

        dt.addClass('edit');

        editor = new InlineEditor(dt, {
            oldValue: key,
            inline: true,
            onSave: function (newKey) {
                var args = {};
                args[page] = {};

                var oldData = Object.clone(args);
                oldData[page][key] = Array.clone(metas[key]);
                oldData[page][newKey] = Array.clone(metas[newKey] || []);

                var val = metas[key].splice(index, 1);
                args[page][key] = metas[key];
                args[page][newKey] = (metas[newKey] || []).combine(val);
                metas[newKey] = args[page][newKey];

                new Request.SetMetas({
                    data: 'action=setMetaJSON&args=' + encodeURIComponent(JSON.encode(args)),
                    checkArgs: page,
                    checkData: oldData,
                    onSuccess: function() {
                        editor.exit();
                        editor = null;
                    }.bind(this)
                }).checkAndSend();
            },
            onExit: function() {
                dt.removeClass('edit');
                editor = null;
            }
        });
    };

};

var InlineEditor = new Class({
    Implements: [Events, Options],

    options: {
        //onSave: function(value){},
        //onExit: function(){}
        //onCancel: function(){}
        oldValue: "",
        inline: true, //puts all controls on the same row if enabled
        key: null,
        autoFormat: true,
        field: null,
        width: 20,
        size: 'compact'
    },

    _keyProperties: {
        hint: 'text',
        constraint: null
    },

    initialize: function(element, options) {
        this.setOptions(options);


        this.element = document.id(element);

        if (this.options.key) {
            new Request.JSON({
                url: '?action=ajaxUtils&util=getProperties&key=' + encodeURIComponent(this.options.key),
                onComplete: function(json) {
                    this._keyProperties = Object.merge(this._keyProperties, json);
                    this.build();
                }.bind(this)
            }).get();
        } else {
            this.build();
        }
    },

    build: function() {
        this.element.store('html', this.element.get('html'));
        this.element.addClass('edit');

        this.element.empty();

        if (this.options.inline) this.element.addClass('inline nowrap');

        var oldVal = this.options.oldValue;
        var type = this._keyProperties.hint;
        if (type == "date") {
            this.input = new Element('input',{
                value: oldVal,
                size: 11
            }).inject(this.element);
            new Picker.Date(this.input, {
                format: dateformat,
                pickerClass: 'datepicker_dashboard'
            });

            this.input.select();

        } else if (this._keyProperties.constraint == "existing") {
            var input = this.input = new Element('select.waiting').inject(this.element);
            new Request.GetMetas({
                onSuccess: function(json) {
                    input.removeClass('waiting');
                    var vals = [];
                    Object.each(json, function(metas, page) {
                        Object.each(metas, function(values, key){
                            vals.combine(values);
                        });
                    });

                    vals.each(function(value){
                       input.grab(new Element('option',{
                           value: value,
                           text: value,
                           selected: (value == oldVal)
                       }));
                    });
                }
            }).get(this.options.key, true);
        } else {
            this.input = new Element('textarea', {
                text: oldVal,
                cols: this.options.width
            }).inject(this.element);

            this.input.addEvent('keydown', function(e) {
                if (e && e.key == "esc") this.cancel();
            }.bind(this));

            var field = this.options.size == "compact" ? DynamicTextarea: GwikiDynamicTextarea;
            new field(this.input).addEvent('resize', function() {
                this.input.fireEvent('resize');
            }.bind(this));

            if (this.options.key) {
                this.suggestions = new MetaSuggestions(this.input, {
                    key: this.options.key
                });
            }

            this.input.select();
        }
        

        this.element.adopt(
            new Element('input', {
                type: 'button',
                value: 'save',
                events: {
                    click: this.save.bind(this)
                }
            }),
            new Element('input', {
                type: 'button',
                value: 'cancel',
                events: {
                    click: this.cancel.bind(this)
                }
            }));
    },

    save: function() {
        this.value = this.input.get('value');
        if (this.value !== this.options.oldValue) {
            this.fireEvent('save', this.value);
        } else {
            this.cancel();
        }
    },

    _clean: function() {
        this.element.removeClass('edit');
        this.element.removeClass('inline');
        this.element.removeClass('nowrap');
    },

    exit: function() {
        if (this.suggestions) this.suggestions.exit();

        if (this.options.autoFormat) {
            new Request.HTML({
                data: 'action=ajaxUtils&util=format&text=' + encodeURIComponent(this.value),
                update: this.element,
                onSuccess: function() {
                    this._clean();
                }.bind(this)
            }).send();
        } else {

            this.element.empty();
            this.element.set('text', this.value);
            this._clean();
        }
        this.fireEvent('exit');
    },

    cancel: function() {
        if (this.suggestions) this.suggestions.exit();

        this.element.empty();
        this.element.set('html', this.element.retrieve('html'));
        this._clean();
        this.fireEvent('cancel');
        this.fireEvent('exit');
    }
});

//Adds horizontal growing to dynamic text areas
var GwikiDynamicTextarea = function(textarea, options) {
    if (!window.GwikiDynamicTextarea_) {
        window.GwikiDynamicTextarea_ = new Class({
            Extends: DynamicTextarea,
            options: {
                horizontalGrow: true,
                maxWidth: 650,
                onResize: function() {
                    var x = this.textarea.getSize().x - 2 * this.textarea.getStyle('paddingLeft').toInt() - 2 * this.textarea.getStyle('borderWidth').toInt();
                    if (this.textarea.getStyle('width').toInt() != this.options.maxWidth && this.options.minRows * this.options.lineHeight < this.textarea.getScrollSize().y) {
                        if (!this.origWidth) this.origWidth = x;
                        this.textarea.setStyle('width', this.options.maxWidth);
                        this.checkSize(true);
                    }
                },
                onBlur: function() {
                    if (this.origWidth)  this.textarea.setStyle('width', this.origWidth);
                    this.checkSize(true);
                }
            }
        });
    }

    return new GwikiDynamicTextarea_(textarea, options);
};

//Fixing Date to output week numbers in correct (finnish) way
Date.implement({
    getFinWeek : function() {
        //if first day of year is before friday (<4) => first week number is 1
        var firstDay = this.clone().set('month', 0).set('date', 1);
        var weeknum = ((this.get('dayOfYear') + firstDay.getFinDay()) / 7).ceil();
        weeknum = (firstDay.getFinDay() < 4) ? weeknum : weeknum - 1;
        return weeknum;
    },
    getFinDay : function() {
        return (this.getDay() + 6) % 7;
    }
});


Object.extend({
    sortedKeys: function(object) {
        return Object.keys(object).sort();
    },

    sortedValues: function(object) {
        var keys = Object.keys(object).sort();
        return keys.map(
            function(key) {
                return object[key];
            }).flatten();
    }
});

/**
 * Overlay
 * - Customizable overlay widget with nice opacity
 */
var Overlay = new Class({
    Implements: [Events, Options],
    options: {
        width: '80%',
        onBuild: function(){}
    },

    initialize: function(options) {
        this.setOptions(options);
        this.build();
    },

    build: function() {
        this.bg = new Element('div.alphabg').setStyles({
            'position': 'absolute',
            'left': 0,
            'top': 0,
            'width': document.id(window).getScrollSize().x,
            'min-height': document.id(window).getScrollSize().y,
            'z-index': '999'
        }).inject(document.body);

        this.positioner = new Element('div').setStyles({
            'position': 'absolute',
            'left': 0,
            'top': 0,
            'width': '100%',
            'z-index': '999'
        }).inject(document.body);
        this.container = new Element('div').setStyles({
            'position': 'relative',
            'margin': 'auto',
            'top': document.id(window).getScroll().y + 100,
            'padding': '15px',
            'width': this.options.width,
            'background': 'white',
            'border': '2px black solid',
            'border-radius': '5px'
        }).inject(this.positioner);

        var close = new Element('div.close-button[text=x]')
            .addEvent('click', this.cancel.bind(this))
            .inject(this.container);

        this.editor = new Element('div').setStyles({
            'min-height': '200px'
        }).inject(this.container);

        this.fireEvent('build');
    },

    cancel: function() {
        this.bg.destroy();
        this.positioner.destroy();
    }
});

/**
 * ActionSelector
 * - creates a select element with events bound to options
 *
 *  usage: elem.grab(new ActionSelector({"option1": func}, this))
 */
var ActionSelector = new Class({
    initialize: function(opts, context) {
        this.opts = opts;
        this.context = context;
        this.build();
        this.attach();
    },

    build: function() {
        this.element = new Element('select');
        Object.each(this.opts, this.add, this);
    },

    add: function(func, name) {
        this.element.grab(new Element('option', {
            text: name,
            value: name
        }));
    },

    attach: function() {
        this.element.addEvent('change', function(event) {
            var val = event.target.get('value');
            this.opts[val].apply(this.context);
        }.bind(this));
    },

    detach: function(){
        this.element.removeEvents('change');
    },

    toElement: function() {
        return this.element;
    }
});

/**
 * GwikiImport
 * - dynamic js importer for gwiki's javacript modules
 * License: MIT <http://www.opensource.org/licenses/mit-license.php>
 * Copyright: 2011 by Lauri Pokka
 * Depends: MooTools
 */

(function() {
    var DEPS = {
        AttachTree: {
            files: ['js/AttachTree.js'],
            depends: [],
            styles: ['img/Expand.png']
        },
        InlineEditor: {
            files: ['js/gwiki-common.js'],
            depends: ['DynamicTextarea', 'MetaSuggestions', 'DatePicker']
        },
        DynamicTextarea: {
            files: ['js/DynamicTextarea.js'],
            depends: []
        },
        MetaTable: {
            files: ['js/MetaTable.js'],
            depends: ['InlineEditor']
        },
        MetaFormEdit: {
            files: ['js/MetaFormEdit.js'],
            depends: ['DynamicTextarea', 'DatePicker']
        },
        MetaSuggestions: {
            files: ['js/MetaSuggestions.js'],
            depends: []
        },
        DatePicker: {
            files: ['js/DatePicker.js'],
            styles: [
                'css/DatePicker/datepicker_dashboard.css'
            ],
            depends: []
        }
    };

    this.GwikiImport = new Class({
        initialize: function(baseUrl) {
            this.baseUrl = baseUrl;
            this.requests = [];
            this.queue = [];
            this.loaded = [];
            Object.each(DEPS, function(module, name) {
                if (module.files.every(function(file) {
                    return $$('script[src=' + this.baseUrl + file + ']').length != 0;
                }, this)) {
                    this.loaded.push(name);
                }
            }, this);

            this.bound = {
                load: this._load.bind(this)
            };
        },

        load: function(modules, callback) {
            var missing = this.missingDeps(modules);
            if (missing.length == 0) {
                callback.apply();
            } else {
                this.requests.push({modules: missing, callback: callback});
                missing.each(this.bound.load);
            }
        },

        _load: function(mod) {
            if (this.queue.contains(mod)) return;

            var module = DEPS[mod];
            this.queue.include(mod);

            module.files.each(function(file) {
                new Asset.javascript(this.baseUrl + file, {
                    onLoad: function() {
                        this.loaded.include(mod);
                        this.queue.erase(mod);
                        this.requests = this.requests.filter(function(req) {
                            req.modules.erase(mod);
                            if (req.modules.length > 0) {
                                return true;
                            } else {
                                req.callback.apply();
                                return false;
                            }
                        });
                    }.bind(this)
                });
            }, this);

            if (module.styles) module.styles.each(function(file) {
                if (file.test("css$")) new Asset.css(this.baseUrl + file);
                else new Asset.image(this.baseUrl + file);
            }, this);
        },
        missingDeps: function() {
            var deps = Array.prototype.slice.call(arguments).flatten(), missing = [];
            while (deps.length > 0) {
                mod = deps.shift();
                deps.append(DEPS[mod].depends);
                if (!this.loaded.contains(mod)) missing.include(mod);
            }

            return missing;
        }
    });
})();
