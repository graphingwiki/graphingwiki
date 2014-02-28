(function() {
    // Current script file will appear as the last script element on
    // the document when loading scripts synchronously
    var scripts = document.getElementsByTagName('script');
    var currentScript = scripts[scripts.length - 1].src;
    var baseUrl = currentScript.split("gwikicommon")[0];

    requirejs.config({
        baseUrl: baseUrl,
        paths: {
            gwikicommon: 'gwikicommon/js',
            collabcommon: 'collabcommon/js'
        },

        map: {
            '*': {
                'css': 'gwikicommon/css',
                'mootools': 'gwikicommon/mootools-core-yc',
                'mootools-more': 'gwikicommon/mootools-more-yc'
            }

        },
        shim: {
            'gwikicommon/mootools-more-yc': ['gwikicommon/mootools-core-yc'],
            'gwikicommon/mootools-core-yc': [],
            'gwikicommon/DatePicker': {
                deps: ['gwikicommon/mootools-more-yc'],
                init: function() {
                    "use strict";
                    $$('head')[0].grab(new Element('link', {
                        rel: 'stylesheet',
                        href: baseUrl + 'gwikicommon/css/DatePicker/datepicker_dashboard.css',
                        type: 'text/css'
                    }));
                    return this.Picker;
                }
            }
        }
    });

    define('config', function() {
        return {
            'dateformat': '%Y-%m-%d',
            'gwikiseparator': '-gwikiseparator-'
        };
    })
})();
