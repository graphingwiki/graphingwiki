if(MooTools){


   window.addEvent('domready',function(){
		var tables = $$('.metatable table');
		if(tables){
			tables.each(function(tab){
				new sortableTable(tab,{
					overCls: 'over',
					oddRowClass: 'metatable-odd-row',
					evenRowClass: 'metatable-even-row',
					sortOn: -1
				});
			});
		}
    });


/**************************************************************

	Script		: Sortable Table
	Version		: 1.4
	Authors		: Samuel Birch
	Desc			: Sorts and filters table elements
	Licence		: Open Source MIT Licence

**************************************************************/

var sortableTable = new Class({
	Implements: [Events, Options],
			  
	getOptions: function(){
		return {
			overCls: false,
			onClick: false,
			sortOn: 0,
			sortBy: 'ASC',
			filterHide: true,
			filterHideCls: 'hide',
			filterSelectedCls: 'selected',
			oddRowClass: 'altRow',
			evenRowClass: 'evenRow'

		};
	},

	initialize: function(table, options){
		this.setOptions(this.getOptions(), options);
		this.table = $(table);
		this.tHead = this.table.getElement('thead');
		this.tBody = this.table.getElement('tbody');
		this.tFoot = this.table.getElement('tfoot');
		this.filtered = false;
		
		/* Moving first tr to thead is thead is empty */
		if( !this.tHead || ! this.tHead.getElements('tr')){
			if(!this.tHead){
				this.tHead =  new Element('thead');
				this.table.grab(this.tHead, 'top');
			}
			var frow = this.tBody.getFirst('tr').dispose();
			this.tHead.grab(frow);
		}
			this.elements = this.tBody.getElements('tr');

		this.elements.each(function(el,i){
			el.addEvent('click', function() {
				this.fireEvent('click', el)
			}.bind(this));

			if(this.options.overCls){
				el.addEvent('mouseover', function(){
					el.addClass(this.options.overCls);
				}.bind(this));
				el.addEvent('mouseout', function(){
					el.removeClass(this.options.overCls);
				}.bind(this));
			}
		}, this);
		//setup header
		this.tHead.getElements('th, td').each(function(el,i){
					
				el.grab(new Element('a',{
						'html' : '&#171;',
						'id': 'hide',
						'styles': {
							'color': 'green',
							'cursor': 'hand',
							'margin-left' : '2px'
						}
					}).addEvent('click', this.hide.bind(this,[i,el]))
				);	
				el.addEvent('click', this.sort.bind(this,i));
				el.addEvent('mouseover', function(){
					el.addClass('tableHeaderOver');
				});
				el.addEvent('mouseout', function(){
					el.removeClass('tableHeaderOver');
				});
				el.getdate = function(str){
					// inner util function to convert 2-digit years to 4
					function fixYear(yr) {
						yr = +yr;
						if (yr<50) { yr += 2000; }
						else if (yr<100) { yr += 1900; }
						return yr;
					};
					var ret;
					//
					if (str.length>12){
						strtime = str.substring(str.lastIndexOf(' ')+1);
						strtime = strtime.substring(0,2)+strtime.substr(-2)
					}else{
						strtime = '0000';
					}
					//
					// YYYY-MM-DD
					if (ret=str.match(/(\d{2,4})-(\d{1,2})-(\d{1,2})/)) {
						return (fixYear(ret[1])*10000) + (ret[2]*100) + (+ret[3]) + strtime;
					}
					// DD/MM/YY[YY] or DD-MM-YY[YY]
					if (ret=str.match(/(\d{1,2})[\/-](\d{1,2})[\/-](\d{2,4})/)) {
						return (fixYear(ret[3])*10000) + (ret[2]*100) + (+ret[1]) + strtime;
					}
					return 999999990000; // So non-parsed dates will be last, not first
				};
				//
				el.findData = function(elem){
				/*	
					var child = elem.getFirst();
					if(child){
						return el.findData(child);
					}else{
						return elem.innerHTML.trim();
					}
					*/
						return elem.innerHTML.trim();
				};
				//
				
				el.getFloat = function(val){
					val = val.toFloat();
					if(!val){
						return -99999999000;
					}
					return val;
				}
				/*  We must first guess the type of the content if it's not set. */
				if(!el.axis){
					DATE_RE = /^(\d\d?)[\/\.-](\d\d?)[\/\.-]((\d\d)?\d\d)$/;
					this.elements.each(function(tr){
						var value = el.findData(tr.getChildren()[i]);
						if(el.axis != 'string' && value && value != ""){
							var date_match = value.match(DATE_RE);
							var num_match = value.match(/^-?[\d,.]+%?$/);
							if(date_match && (!el.axis || el.axis == 'date')){
									el.axis = 'date';
							}else if(num_match && (!el.axis || el.axis == 'number')){
								el.axis = 'number';
							}else{
								el.axis = 'string';
							}
						}
					});
				}
				el.compare = function(a,b){
					var1 = el.findData(a.getChildren()[i]);
					var2 = el.findData(b.getChildren()[i]);
					//var1 = a.getChildren()[i].firstChild.data;
					//var2 = b.getChildren()[i].firstChild.data;
					
						
					if(el.axis == 'number'){
						var1 = el.getFloat(var1);
						var2 = el.getFloat(var2);
							
						if(el.sortBy == 'ASC'){
							return var1-var2;
						}else{
							return var2-var1;
						}
						
					}else if(el.axis == 'string'){
						var1 = var1.toUpperCase();
						var2 = var2.toUpperCase();
						
						if(var1==var2){return 0};
						if(el.sortBy == 'ASC'){
							if(var1<var2){return -1};
						}else{
							if(var1>var2){return -1};
						}
						return 1;
						
					}else if(el.axis == 'date'){
						var1 = parseFloat(el.getdate(var1));
						var2 = parseFloat(el.getdate(var2));
						
						if(el.sortBy == 'ASC'){
							return var1-var2;
						}else{
							return var2-var1;
						}
						
					}else if(el.axis == 'currency'){
						var1 = parseFloat(var1.substr(1).replace(',',''));
						var2 = parseFloat(var2.substr(1).replace(',',''));
						
						if(el.sortBy == 'ASC'){
							return var1-var2;
						}else{
							return var2-var1;
						}
						
					}
					
				}
				
				if(i == this.options.sortOn){
					el.fireEvent('click');
				}
		}, this);
	},
	hide : function(index,el){
		el.store('normHTML', el.get('html'));
		el.empty();
		el.grab(new Element('a',{
			'html':'&#8250;',
			'class':'jslink'
		}).addEvent('click',this.unhide.bind(this,[index,el])));
		this.elements.each(function(row){
			col = row.getElements('td')[index];
			col.store('normHTML',col.get('html')).empty();
		});
	return false;
	},
	unhide : function(index,el){
		el.empty();
		el.set('html', el.retrieve('normHTML'));
		el.getLast('a#hide').addEvent('click',this.hide.bind(this,[index,el]));
		this.elements.each(function(row){
			col = row.getElements('td')[index];
			col.set('html',col.retrieve('normHTML'));
		});
		return false;
	},
	sort: function(index){
		if(this.options.onStart){
			this.fireEvent('onStart');
		}
		//
		this.options.sortOn = index;
		var header = this.tHead.getElements('th, td');
		var el = header[index];
	    
		el.clearClasses = function(elm){
			elm.removeClass('sortedASC');
			elm.removeClass('sortedDESC');
			ar = elm.getElements('.arrow');
			if(ar.length>0){
				ar.destroy();
			}
		};
		el.addStyle = function(elm,asc){
			if(asc == "asc"){
				elm.addClass('sortedASC');
				elm.sortBy = 'ASC';
				elm.grab(new Element('span',{
					'class':'arrow',
					'html': '&nbsp;&#8595;'
				}));
			}else{
				elm.addClass('sortedDESC');
				elm.sortBy = 'DESC';
				elm.grab(new Element('span',{
					'class':'arrow',
					'html': '&nbsp;&#8593;'
				}));
		}
		};
		header.each(function(e,i){
			if(i != index){
				el.clearClasses(e);
			}
		});
		
		if(el.hasClass('sortedASC')){
			el.clearClasses(el);
			el.addStyle(el,'desc');
		}else if(el.hasClass('sortedDESC')){
			el.clearClasses(el);
			el.addStyle(el,'asc');
		}else{
			if(this.options.sortBy == 'ASC'){
				el.clearClasses(el);
				el.addStyle(el,'asc');
			}else if(this.options.sortBy == 'DESC'){
				el.clearClasses(el);
				el.addStyle(el,'desc');
			}
		}
		//
		this.elements.sort(el.compare);
		this.elements.injectInside(this.tBody);
		//
		if(this.filtered){
			this.filteredAltRow();
		}else{
			this.altRow();
		}
		
		//
		if(this.options.onComplete){
			this.fireEvent('onComplete');
		}
	},
	
	altRow: function(){
		var oddC = this.options.oddRowClass;
		var evenC = this.options.evenRowClass;
		this.elements.each(function(el,i){
			if(i % 2){
				el.removeClass(oddC);
				el.addClass(evenC);
			}else{
				el.removeClass(evenC);
				el.addClass(oddC);
			}
		});
	},
	
	filteredAltRow: function(){
		var oddC = this.options.oddRowClass;
		var evenC = this.options.evenRowClass;
		this.table.getElements('.'+this.options.filterSelectedCls).each(function(el,i){
			if(i % 2){
				el.removeClass(oddC);
				el.addClass(evenC);
			}else{
				el.removeClass(evenC);
				el.addClass(oddC);
			}
		});
	},
	
	filter: function(form){
		var form = $(form);
		var col = 0;
		var key = '';
		
		form.getChildren().each(function(el,i){
			if(el.id == 'column'){
				col = Number(el.value);
			}
			if(el.id == 'keyword'){
				key = el.value.toLowerCase();
			}
			if(el.type == 'reset'){
				el.addEvent('click',this.clearFilter.bind(this));
			}
		}, this);
		
		if(key){
		this.elements.each(function(el,i){
			if(this.options.filterHide){
				el.removeClass(this.options.oddRowClass);
				el.removeClass(this.options.evenRowClass);
			}
			if(el.getChildren()[col].firstChild.data.toLowerCase().indexOf(key) > -1){
				el.addClass(this.options.filterSelectedCls);
				if(this.options.filterHide){
					el.removeClass(this.options.filterHideCls);
				}
			}else{
				el.removeClass(this.options.filterSelectedCls);
				if(this.options.filterHide){
					el.addClass(this.options.filterHideCls);
				}
			}
		}, this);
		if(this.options.filterHide){
			this.filteredAltRow();
			this.filtered = true;
		}
		}
	},
	
	clearFilter: function(){
		this.elements.each(function(el,i){
			el.removeClass(this.options.filterSelectedCls);
			if(this.options.filterHide){
				el.removeClass(this.options.filterHideCls);
			}
		}, this);
		if(this.options.filterHide){
			this.altRow();
			this.filtered = false;
		}
	}

});

/*************************************************************/


}
