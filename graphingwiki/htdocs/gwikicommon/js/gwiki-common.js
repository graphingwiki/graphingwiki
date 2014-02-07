require(['config', 'mootools-more'], function(config) {
    "use strict";

    Slick.definePseudo('nth-include', function(n) {
        var node = this, count = 0;
        while ((node = node.parentNode)) {
            if (node.className && node.className.test("gwikiinclude")) count++;
        }
        return count === +n
    });

    Element.Events.shiftclick = {
        base: 'mousedown', // the base event type
        condition: function(event) {
            return (event.shift == true);
        }
    };

//Fixing Date to output week numbers in correct (finnish) way
    Date.implement({
        getFinWeek: function() {
            //if first day of year is before friday (<4) => first week number is 1
            var firstDay = this.clone().set('month', 0).set('date', 1);
            var weeknum = ((this.get('dayOfYear') + firstDay.getFinDay()) / 7).ceil();
            weeknum = (firstDay.getFinDay() < 4) ? weeknum : weeknum - 1;
            return weeknum;
        },
        getFinDay: function() {
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

    var initDnDUpload = function(el) {
        if (!window.addEventListener) return;

        function noAction(e) {
            e.stopPropagation();
            e.preventDefault();
        }


        var overlay = null;

        el.addEventListener("dragenter", function() {
            //preload overlay
            require(['gwikicommon/Overlay'], function() {
            }());
        }, false);
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
                    require(['gwikicommon/Overlay'], function(Overlay) {
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

                                div.grab(new Element('input[type=button][value=Send]').addEvent('click',function(e) {
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
                                                    } else if (failed.contains(files[i].name)) {
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
                    });
                }
            }
        }, false);
    };

    var init = function() {
        // MetaFormEdit improvements
        var fields = $$('.metaformedit');
        if (fields.length > 0) {
            require(['gwikicommon/MetaFormEdit'], function(MetaFormEdit) {
                new MetaFormEdit(fields[0].getParent('form'));
            });
        }

        // Apply MooTools tooltips to elements with .mt-tooltip class
        if ($$('.mt-tooltip').length) {
            require(['mootools-more'], function() {
                new Tips('.mt-tooltip', {'className': 'mootip'});
            })
        }

        // Apply MetaTable improvements
        var tables = $$('div.metatable[data-options]');
        if (tables.length > 0) {
            require(['gwikicommon/MetaTable', 'config'], function(mt, config) {
                tables.each(function(div, i) {
                    new mt.MetaTable(div.getElement('table'), {
                        tableArguments: JSON.decode(decodeURIComponent(div.getAttribute('data-options'))),
                        separator: config.gwikiseparator
                    });
                });
            });
        }

        // InterMetaTable
        if ($$('div.InterMetaTable').length) {
            require(['gwikicommon/MetaTable'], function(mt) {
                $$('div.InterMetaTable').each(function(table) {
                    var opts = JSON.decode(decodeURIComponent(table.getAttribute('data-options')));
                    new mt.InterMetaTable(table, opts);
                });
            });
        }

        // Inline Edit
        if ($$('dl:not(.collab_list) dt').length && $$('dl:not(.collab_list) dd').length) {
            require(['gwikicommon/InlineEditor'], function() {
                $$('.gwikiinclude').include(document.body).each(initInlineMetaEdit);
            });
        }

        // AttachTree
        if ($$('.attachtree_area').length) {
            require(['gwikicommon/AttachTree'], function(AttachTree) {
                $$('.attachtree_area').each(function(el) {
                    new AttachTree(el);
                });
            });
        }

        // DynamicTextareas for textareas with .dynamic
        // Added body check to workaround a weird phantomjs bug
        if ($$('textarea.dynamic').length) {
            require(['gwikicommon/DynamicTextarea'], function(dt) {
                $$('textarea.dynamic').setStyles({
                    'resize': 'none',
                    'overflow': 'hidden'
                });

                if (document.body) {
                    document.id(document.body).addEvent('focus:relay(textarea.dynamic)', function(e) {
                        if (!document.id(e.target).retrieve('dynamic')) {
                            new dt.DynamicTextarea(e.target);
                            document.id(e.target).store('dynamic', true).focus();
                        }
                    });
                }
            });
        }

        //DnD file attachment upload
        initDnDUpload(document.window);
    };

    var initInlineMetaEdit = function(base) {
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

        //do not attach inline edit if MetaFormEdit is running
        if (!base.getElement('dl:not(.collab_list)') || base.getElement('dl').getParent('form')) return;

        var include_level = base.getParents('div.gwikiinclude').length + +base.hasClass('gwikiinclude');
        var metas, formatted, editor, page = "";

        if (base.hasClass('gwikiinclude')) page = unescapeId(base.id).split(config.gwikiseparator)[0];

        base.addEvent('mouseover:relay(dl:nth-include(' + include_level + ')):once', function() {
            require(['gwikicommon/MetaRequest'], function(Request) {
                new Request.GetMetas({
                    args: page,
                    onSuccess: function(results, f) {
                        page = Object.keys(results)[0];
                        metas = results[page];
                        formatted = f;
                        base.getElements('dd:nth-include(' + include_level + ')').each(function(dd) {
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
                            } else if (index != metas[key].indexOf(value)) {
                                //fix order of metas since incMetaGet does not preserve it
                                metas[key].splice(index, 0, value);
                                for (var i = index + 1; i < metas[key].length; i++) {
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
        });

        //add a '+' button for adding values to empty metas (foo::)
        base.getElements('dd:nth-include(' + include_level + ')').each(function(dd) {
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

        base.addEvent('shiftclick:relay(dd:not(.edit):nth-include(' + include_level + '))', function(event) {
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
            require(['gwikicommon/InlineEditor', 'gwikicommon/MetaRequest'], function(InlineEditor, Request) {
                editor = new InlineEditor(dd, {
                    oldValue: oldValue,
                    key: key,
                    inline: true,
                    width: 40,
                    size: 'large',
                    onSave: function(newValue) {
                        var args = {};
                        args[page] = {};

                        var vals = Array.clone(metas[key]);
                        args[page][key] = vals;
                        var oldData = Object.clone(args);
                        vals[index] = newValue;

                        new Request.SetMetas({
                            metas: args,
                            checkArgs: page,
                            checkData: oldData,
                            onSuccess: function() {
                                metas[key] = vals;
                                editor.exit();
                                editor = null;
                            }.bind(this)
                        }).checkAndSend();
                    },
                    onCancel: function() {
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
            });
        };

        base.addEvent('shiftclick:relay(dt:not(.edit):nth-include(' + include_level + '))', function(event) {
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
            require(['gwikicommon/InlineEditor', 'gwikicommon/MetaRequest'], function(InlineEditor, Request) {
                editor = new InlineEditor(dt, {
                    oldValue: key,
                    inline: true,
                    onSave: function(newKey) {
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
                            metas: args,
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
            });
        };

    };

    if (["complete", "interactive"].indexOf(document.readyState) != -1) {
        init();
    } else {
        window.addEventListener('DOMContentLoaded', init, false);
    }
});