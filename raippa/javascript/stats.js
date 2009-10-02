/* Script stats.js
 * Class for showing stats
 * Requires mootools 1.2 with accordion and binds extensions.
 * 'showTotalData' and 'showItemData' methods need to be implemented
 * to show data in human readable way.
 */

var Stats = new Class({
	Implements: [Options],
	Binds: ['getData', 'createUI', 'hideStatBox', 'showStatBox', 'filter', 'showStatBox'],
	options: {
        maxBoxCount : 3,
		query_args: 'stats',
		containerStyles: {
			'width' : '600px',
			'background-color': 'white',
			'border': '1px solid black',
            'overflow' : 'hidden',
            'padding' : '5px 5px 10px 5px',
            'min-height' : '400px'
		},
        searchContainerStyles : {
            'width' : '30%',
            'float' : 'left'
        },
        searchFieldStyles : {
            'display': 'block',
            'width' : '100%'
        },
        searchResultStyles : {
            'width': '100%'
        },
        statsContainerStyles : {
            'width' : '66%',
            'float' : 'right'
        }
	},
	stats: {},
	statBoxes: [],
	initialize: function(el, options){
		if (!el) return false;
		this.container = $(el);
		this.setOptions(options);
		
		this.container.setStyles(this.options.containerStyles);
		this.container.empty();
				
		this.searchContainer = new Element('div');
		this.searchContainer.setStyles(this.options.searchContainerStyles);
		
		this.statsContainer = new Element('div');
		this.statsContainer.setStyles(this.options.statsContainerStyles);
		
		this.searchResults = new Element('div');
        this.searchResults.setStyles(this.options.searchResultStyles);
		
		this.container.adopt(this.searchContainer, this.statsContainer);
		
		this.updateUI();
		this.updateData();

	},
	updateUI: function(){
		this.searchContainer.empty();
		this.statsContainer.empty();
		
        var totaltitle = new Element('h3', {
            'text' : 'Overall',
            'class' : 'statboxtitle'
        });
        var totalbox = new Element('div', {
            'class' : 'statbox',
            'html' : this.showTotalData(this.stats.total)
        });
                
        this.statsContainer.adopt(totaltitle, totalbox);
        
        this.accordion = new RaippaAccordion(this.statsContainer, 'h3.statboxtitle', 'div.statbox',{
            opacity : 0
        });
        
		var search = new Element('input');
        search.setStyles(this.options.searchFieldStyles);
		//search.addEvent('keyup', this.filter(search.get('value')));
		search.addEvent('keyup', function(){
            this.filter(search.get('value'));
        }.bindWithEvent(this));
		this.searchContainer.adopt(search, this.searchResults);
        
        this.filter("");
	},
    
    /* Defines what is shown in overall view */
    showTotalData : function(total){
    
    },
    
    /* Defines what is shown in detailed view */
    showItemData: function(item){

    },
    
	showStatBox: function(id){
        if (this.statBoxes.length >= this.options.maxBoxCount){
            this.accordion.removeSection(this.options.maxBoxCount);
        }
        var data = this.stats.items[id];
        var box = new Element('div', {
            'id' : 'statbox_' + id,
            'class' : 'statbox',
            'html' : this.showItemData(data)
        });
        var title = new Element('h3', {
                'class' : 'statboxtitle',
                'text' : data.name + ' ('+ id+')'
            });
        this.statBoxes.push(id);
        this.accordion.addSectionAt(title,box,1);
        this.accordion.display(box, false);
	},
	filter: function(search){
		var results = $H();
		if(this.stats && this.stats.items){
			results = this.stats.items.filter(function(value, key){
				return key.test(search, "i") || value.name.test(search, "i");
			});
		}
		var resultList = this.searchResults.empty();
		
		results.each(function(value, key){
			var item = new Element('a',{
				'text': value.name,
                'class' : 'jslink'
			});
            item.addEvent('click', function(){
                this.showStatBox(key);
            }.bindWithEvent(this));
			resultList.adopt(new Element('br'), item);
		}, this);
		
	},
	updateData: function(){
		var query = new Request.JSON({
			url: '?action=searchMetasJSON',
			async: true,
			onSuccess: function(json){
				this.stats = this.parseData(json);
				this.updateUI();
			}.bindWithEvent(this)
		});
		query.get({'args': this.options.query_args});
	},
	parseData: function(data){
		var data = $H(data);
		var total = data.total;
		data.erase('total');
		var result = $H({
			'total': total,
			'items':  data
		});
		return result;
		
	}
});

var QuestionStats = new Class({
    Implements : Stats,
    /* Defines what is shown in overall view */
    showTotalData : function(total){
        var total = $H(total);
        var text = "<b>Total time: </b>" + (total.get('time') / 60).round() + "min";
        text += "<br><b>Total tries: </b>" + total.get('count');
        return "<p>" +text +"</p>";
    },
    
    /* Defines what is shown in detailed view */
    showItemData: function(item){
        var text = "<p><b>Total tries:</b> " + item.total.count + "<br>" +
            "<b>Total time: </b> " + (item.total.time / 60).round()  + "min</p>" +
            "<h4>Tries:</h4>";
            $H(item.tries).each(function(value, key){
                text += "<p><b>" + key + "</b>" +
                        "<br>right: <span class='rightAnswer'>" + value.right.toString() 
                        + "</span>" +
                        "<br>wrong: <span class='wrongAnswer'> " + value.wrong.toString() 
                        + "</span>" + 
                        "<br>overall: "+ value.overall +"</p>";
            });
        return text;
    }
});

var TaskStats = new Class({
    Implements: Stats,
    /* Defines what is shown in overall view */
    showTotalData : function(total){
        var total = $H(total);
        var text = "<h4>Questions:</h4>";
        total.each(function(value, key){
            text += "<p><b>" + key + "</b>" +
                    "<br>Total time: "+ (value.time / 60).round() +"min" +
                    "<br>Total tries: "+  value.count +"</p>";

        });
        return "<p>" +text +"</p>";
    },
    
    /* Defines what is shown in detailed view */
    showItemData: function(item){
        var text = "<p><b>Total tries:</b> " + item.total.count + "<br>" +
            "<b>Total time: </b> " + (item.total.time / 60).round()  + "min</p>";

        return text;
    }
    
});