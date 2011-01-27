/*
 gwiki-common.js
	- Collection of js functions and classes used by graphingwiki.
 License:	MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2011 by Lauri Pokka
 */

window.addEvent('domready', function() {
	/* MetaFormEdit improvements */
	var fields = $$('.metaformedit-cloneable');
	if (fields.length > 0) new MetaFormEdit(fields[0].getParent('form'));

	/* */
	var tooltips = new Tips('.mt-tooltip');
});

/*
	MetaFormEdit
		- js improvements for meta edit form.
	Depends: MooTools Core
*/
var MetaFormEdit = new Class({
	initialize: function (form) {
		this.form = document.id(form);
		this.fields = this.getFields();

		this.clean();
		this.build();
	},

	getFields: function(){
		return this.form.getElements('.metaformedit-cloneable, .metaformedit-notcloneable');
	},

	build: function() {
		var self = this;

		this.form.getElements('.metaformedit-cloneable').each(function(dd){
			var dt = dd.getPrevious('dt');
			var siblings = dd.getParent().getChildren();
			if (siblings.indexOf(dd) -1 != siblings.indexOf(dt)) return;
			dt.appendText(' ');
			dt.grab(new Element('a',{
				'class': 'jslink',
				'text': '+',
				'title': 'Add value',
				'events': {
					'click': function() {
						self.clone(dt.getNext('dd'));
					}
				}
			}));
		});
		
		this.fields.each(function(el){
			el.grab(new Element('a', {
				'class': 'jslink',
				'title': 'Remove value',
				'html': 'x',
				'styles': {
					'margin-left': '8px',
					'color': 'red',
					'font-weight': 'bold'
				},
				'events': {
					'click': function() {
						self.remove(this.getParent('dd'))
					}
				}
			}));
		});
	},

	/*
	Tries to group values with same key under one section.
	*/
	clean: function() {
		var keys = [];
		var fields = this.getFields();
		fields.each(function(el) {
			if (!el || el.getElement('input, select, textarea') == null) return;
			var key = el.getElement('input, select, textarea').name;
			if (keys.contains(key)) {
				var values = [];
				el.getElements('input, select, textarea').each(function(input){
					if (input.get('tag') == "select") {
						values.push(input.value);
					} else if (["radio", "checkbox"].contains(input.type)) {
						if (input.checked) values.push(input.value)
					} else {
						values.push(input.value)
					}
				});

				this.remove(el);
				this.clone(this.getFields().filter(function(field) {
					var els =  field.getElements('[name^='+key.split(" ")[0]+']');
					return els.length > 0 && els.some(function(el){ return el.name == key; });
				})[0], values, true);
			} else {
				keys.push(key)
			}
		}, this);
	},

	clone: function(source, values, minimalNew) {
		values = values || [];
		var first = source.getElement('input, select, textarea');
		var type = first.get('tag') == 'select' ? "select" : first.type;

		if (["checkbox"].contains(type)) {
			source.getElements('input[type=checkbox]').each(function(input){
				if (values.contains(input.value)) {
					input.checked = true;
					values.erase(input.value);
				}
			});
			if (source.getElement('input[type=text]') == null || minimalNew) return;
		}

		var cloned = source.clone();
		if (cloned.getElement('a.jslink') != null){
			cloned.getElement('a.jslink').cloneEvents(source.getElement('a.jslink'));
		}

		cloned.getElements('select, input, textarea').each(function(input) {
			input.value = "";
			input.checked = false;
			if (input.get('tag') == "select") {
				input.getElements('option').set("selected", false);//[0].set("selected", true);
				input.getElements('option').each(function(opt){
					if (values.contains(opt.value)){
						opt.set("selected", true);
						values.erase(opt.value);
					}
				});
			}
			if (values.length > 0 && ["textarea", "text"]) {
				input.set('value', values.pop());
			}

		});
		cloned.inject(source, 'before');
		this.fields.splice(this.fields.indexOf(source) +1, 0, cloned);
	},

	remove: function(el) {
		var siblings = el.getParent().getChildren();
		var index = siblings.indexOf(el);
		if (siblings[index-1].get('tag') == "dt" 
			&& (!siblings[index+1] || siblings[index+1].get('tag') == "dt")) {
			siblings[index-1].destroy();
		}
		this.fields.erase(el);
		el.destroy();
	}
});
