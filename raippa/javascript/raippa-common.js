/**
 * Raippa specific extensions
 * requires mootools and more extensions: Accordition, Date, Drag.Move,
 *  Sortables, Assets and Tips and Fx.reveal 
 */



/*
 * A custom accordion class with support for removing sections.
 */

var RaippaAccordion = new Class({
    Extends : Fx.Accordion,
    removeSection : function(index){
        index = ($type(index) == 'element') ? this.elements.indexOf(index) : index;
        var toggler = this.togglers[index];
        var el = this.elements[index];
        this.togglers.erase(toggler);
        this.elements.erase(el);
        toggler.destroy();
        el.destroy();
        //if (index == this.previous)
        this.previous = -1;
        
        return this;
    },
    addSectionAt: function(toggler, element, index){
        this.addSection(toggler, element);
        
        this.togglers.erase(toggler);
        this.togglers.splice(index, 0, toggler);
        
        this.elements.erase(element);
        this.elements.splice(index, 0, element);

        toggler.dispose().inject(this.elements[index-1], 'after');
        element.dispose().inject(toggler, 'after');
        this.previous = -1;
        return this;
    },

	injectSection: function(toggler, element){
		toggler = $(toggler);
		element = $(element);
		var test = this.togglers.contains(toggler);
		var len = this.togglers.length;
		if (this.container && !test){
			toggler.inject(this.container);
			element.inject(this.container);
		}

		this.togglers.include(toggler);
		this.elements.include(element);
		var idx = this.togglers.indexOf(toggler);
		var displayer = this.display.bind(this, element);
		toggler.store('accordion:display', displayer);
		toggler.addEvent(this.options.trigger, displayer);
		if (this.options.height) element.setStyles({'padding-top': 0, 'border-top': 'none', 'padding-bottom': 0, 'border-bottom': 'none'});
		if (this.options.width) element.setStyles({'padding-left': 0, 'border-left': 'none', 'padding-right': 0, 'border-right': 'none'});
		element.fullOpacity = 1;
		if (this.options.fixedWidth) element.fullWidth = this.options.fixedWidth;
		if (this.options.fixedHeight) element.fullHeight = this.options.fixedHeight;
		element.setStyle('overflow', 'hidden');
		if (!test){
			for (var fx in this.effects) element.setStyle(fx, 0);
		}
		return this;
		
		
	}
});

/*
 * Modalizer with tabbing support. Takes an array of elements as argument and
 * puts them into tabbed modal window.
 */
var modalizer = new Class({
	Implements : [Options, Events],
	Binds : ['click', 'close', 'showTab'],
	options :{
		tabTitles : [], //array of titles to show as tab names
		defTab : 0, //index of tab to open as default
		overlayTween : {
			'duration' : 'short'
		},
		overlayStyles: {
            'width' : '100%',
            'height' : '100%',
            'opacity' : 0.8,
            'z-index' : 99,
            'background' : '#333333',
            'position' : 'fixed',
            'top' : 0,
            'left' : 0
		},
		outerContainerStyles:{
            'left' : '50%',
            'position' : 'absolute',
            'top' : 0,
            'z-index' : 100
		},
		containerStyles:{
			'background' :'white',
			'marginTop' : '50px'
		},
		tabSettings: {
			'class': 'tabMenu',
			'styles' :{
				'margin' : '2px 2px 2px 2px'
			}
		},
		tabContainerStyles: {
			'background-color': 'gray'
		},
		destroyOnExit: true
	},

	initialize : function(els, options){
	
		if (!els) return;
		this.els = $$(els);
		this.setOptions(options);
		this.tab_selected = this.options.defTab || 0;
		this.overlay = new Element('div', { id : 'overlay'});
		this.overlay.set('tween', this.options.overlayTween);
		this.overlay.setStyles(this.options.overlayStyles);
		this.overlay.addEvent('click', this.click.bind(this));
		
		this.outerContainer = new Element('div',{id : 'lightContainer'});
	    this.outerContainer.setStyles(this.options.outerContainerStyles);
		
		this.container = new Element('div');
		this.container.setStyles(this.options.containerStyles);
		this.els.dispose();
		this.container.adopt(this.els);
		this.outerContainer.grab(this.container);
		
		if (!Browser.Engine.trident){
	        this.overlay.setStyle('opacity', 0.2);
	        this.overlay.tween('opacity', 0.8);
	    }
		
		if (this.els.length > 1) {
			this.tab = new Element('ul');
			this.tab.set(this.options.tabSettings);
			
			this.els.each(function(el,i){
				var t = new Element('li');
				var text = this.options.tabLabels[i] || el.get('ref') || el.get('id');
				t.set('text', text);
				var clk = function(){
					this.tab.getElements('li').removeClass('selected');
					t.addClass('selected');
					this.showTab(i);
				};
				t.addEvent('click', function(event, index){
					this.tab_selected = index;
					this.showTab();
				}.bindWithEvent(this,i));
				this.tab.grab(t);			
				
			}, this);

			this.tabContainer = new Element('div').grab(this.tab);
			this.tabContainer.setStyles(this.options.tabContainerStyles);
			
			this.container.grab(this.tabContainer, 'top');
		}
	    
	    this.els.setStyle('display', 'none');
	    this.els.removeClass('hidden');
	    $(document.body).adopt(this.overlay, this.outerContainer);
	    
	    //this.showTab();
	    //this.periodical = this.showTab.periodical(100, this);
		this.showTab.delay(100, this);
	},
	showTab : function(tab){
		var tab = tab || this.tab_selected;
		var el = this.els[tab];
		if(this.tab){
			var tabs = this.tab.getElements('li');
			tabs.removeClass('selected');
			tabs[tab].addClass('selected');
		}
		this.els.setStyle('display', 'none');
		this.container.setStyle('width','100px');
		

		el.setStyle('display','');
		var width = el.getSize().x;
		this.container.setStyle('width', width);
		this.container.setStyle('width', 'auto');

		if (!el.retrieve('margin')) el.store('margin', el.getStyle('margin'));
		el.setStyle('margin', '');
		el.setStyle('border-top','');
		
		this.container.setStyle('margin-left', -0.5 * el.getCoordinates().width);

	},
    click : function(e){
		this.close();
 
        },
	close : function(){
        	this.overlay.tween('opacity', 0.2);
            (function(){
            	if(!this.options.destroyOnExit){
            		this.els.dispose();
            		this.els.setStyle('display', 'none');
            		$(document.body).adopt(this.els);
            	}
                this.overlay.destroy();
                var l = this.outerContainer;
                //$clear(this.periodical);
                if(l) l.destroy();
            }).delay(150, this);
		
	}
	
});

window.Tips = new Class({
	Extends: Tips,
	initialize: function(elements, options){
		options = $merge(options,{
		className: 'mootip',
		title: function(element){
			element.store("title_backp", element.get("title"));
			return element.get("title") ? element.get("title").split("::")[0] || element.get("title") :"";
		},
		text: function(element){
			var txt = element.retrieve("title_backp") ? element.retrieve("title_backp") : "";
			return txt.split("::")[1] || element.get("rel")||element.get("href");
		}
		});
		this.parent(elements,options);
	}
});
