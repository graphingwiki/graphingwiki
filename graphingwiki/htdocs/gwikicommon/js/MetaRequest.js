define([
    'mootools'
],
    function() {
        /*
         SetMetas using setMetaJSON
         Usage example:
             var metas = {"testisivu":{"foo":["bar"]}}
             new Request.SetMetas({
                 metas: metas
             }).checkAndSend();

         */
        Request.SetMetas = new Class({
            Extends: Request.JSON,
            options: {
                //onConflict: function(){}
                method: 'post',
                metas: {},
                url: '',
                checkArgs: '',
                checkData: {}
            },
            send: function(){
                this.options.data = 'action=setMetaJSON&args=' + encodeURIComponent(JSON.encode(this.options.metas));
                this.parent();
            },
            checkAndSend: function() {
                var args = arguments;
                new Request.GetMetas({
                    collaburl: this.options.url,
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
                                })) {
                                    failreason = JSON.encode(values) + " has been changed to " + JSON.encode(json[page][key]);
                                }
                                return failreason === "";
                            });
                        }) || confirm("Data has changed after you loaded this page, do you want to overwrite changes? \n " +
                            failreason.slice(0, 500))) {
                            this.send(args);
                        } else {
                            this.fireEvent('conflict');
                        }
                    }.bind(this)
                }).get(this.options.checkArgs);
            },

            onSuccess: function(json) {
                if (json.status == "ok") {
                    this.fireEvent('complete', arguments).fireEvent('success', arguments).callChain();
                } else {
                    if (json.msg && json.msg[0]) alert(json.msg[0]);
                    else alert("Save failed for unknown reason.");
                }
            }
        });

 /*
         SetMetas using setMetaJSON2
         Usage example:
             new Request.SetMetas2({
                url: 'page'
             }).send([
                {op: 'add', 'key': 'foo', 'value': 'bar'},
                {op: 'set', 'key': 'foo2', 'value': [1,2,3]},
                {op: 'del', 'key': 'foo3', 'value': ['foo']}
             ]);

  */
        Request.SetMetas2 = new Class({
            Extends: Request.JSON,
            options: {
                ops: [],
                url: '',
                urlEncoded: false,
                onFailure: function(xhr) {
                    if (xhr.responseText) {
                        var json = JSON.parse(xhr.responseText);
                        alert(json.msg);
                    }
                }
            },

            send: function(ops) {
                this.headers['Content-Type'] = "application/json;charset=UTF-8";
                this.options.url += (this.options.url.indexOf('?') == -1 ? '?' : '&') + 'action=setMetaJSON2';
                if (ops && !ops instanceof Array) {
                    ops = [ops];
                }

                this.options.data = JSON.stringify([].concat(this.options.ops || [], ops || []));
                this.parent();

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
                link: "chain",
                collaburl: ""
            },

            get: function(args, onlyvalues) {
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

                if (this.options.collaburl) {
                    opts.url = this.options.collaburl + opts.url;
                    this.options.cacheNamespace += "." + this.options.collaburl;
                }

                if ("localStorage" in window) {
                    var ls = window.localStorage;
                    var namespace = this.options.cacheNamespace;

                    if (this._onlyvalues) namespace += ".values";
                    var cached = JSON.decode(ls[namespace + "_" + this._metaArg]);
                    if (cached && cached.handle && cached.formatted) opts.url += "&handle=" + encodeURIComponent(cached.handle);
                    //try to maintain incGetMeta-cache integrity in case user quits page before we get to save results
                    this.unloadEvent = function() {
                        delete ls[namespace + "_" + this._metaArg];
                    }.bind(this);
                    document.window.addEvent('unload', this.unloadEvent);
                }

                return this.send(opts);
            },

            onSuccess: function(json, text) {
                var handle = json[1];
                var data = json[2];
                var formatted = json.length > 3 ? json[3] : {};

                var results = {};
                var args = this._metaArg, ls, namespace;
                if ("localStorage" in window) {
                    ls = window.localStorage;
                    namespace = this.options.cacheNamespace;
                    if (this._onlyvalues) namespace += ".values";
                    //get stuff from cache only if the incGetMeta session is alive
                    if (json[0]) {
                        results = (JSON.decode(ls[namespace + "_" + args]) || {metas: {}})['metas'];
                        formatted = Object.merge((JSON.decode(ls[namespace + "_" + args]) || {formatted: {}})['formatted'], formatted);
                    }
                }

                var page, i, j;

                //deleted pages
                for (i = 0; i < data[0].length; i++) {
                    page = data[0][i];
                    if (results[page]) delete results[page];
                }

                //new pages/changes
                Object.each(data[1], function(metas, page) {
                    if (!results[page]) results[page] = {};
                    Object.each(metas, function(vals, key) {
                        if (!results[page][key])results[page][key] = [];

                        var deleted = vals[0];
                        for (i = 0; i < deleted.length; i++) {
                            j = results[page][key].indexOf(deleted[i]);
                            if (j >= 0) results[page][key].shift(j, 1);
                        }

                        var added = vals[1];
                        for (i = 0; i < added.length; i++) {
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
                            ls[namespace + "_" + args] = JSON.encode({handle: handle, metas: results, formatted: formatted});
                            items.erase(args).push(args);
                            ls[indexName] = JSON.encode(items);
                            break;

                        } catch (e) {
                            if (items.length > 0) {
                                delete ls[items.shift()];
                            } else {
                                break;
                            }

                        }
                    }
                    ls[indexName] = JSON.encode(items);
                    document.window.removeEvent('unload', this.unloadEvent);

                }

                this.fireEvent('complete', [results, formatted, json, text])
                    .fireEvent('success', [results, formatted, json, text])
                    .callChain();
            }
        });

        return Request;
    });