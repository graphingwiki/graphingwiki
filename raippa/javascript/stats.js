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
            'width' : '88%'
        },
        searchResultStyles : {
            'width': '100%',
            'height' : '400px',
            'overflow' : 'auto',
            'margin' : '10px 0px 10px 5px'
        },
        statsContainerStyles : {
            'width' : '66%',
            'float' : 'right'
        },
		srcname : "stats.js"
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
		
		if (typeof(Raphael) == "undefined"){
			var path = document.getElement('script[src$='+this.options.srcname+']').get('src')
			.replace(this.options.srcname, "raphael.js");
			var raphaeljs = new Asset.javascript(path);
		}

	},
	updateUI: function(){
		this.searchContainer.empty();
		this.statsContainer.empty();
		
        var totaltitle = new Element('h3', {
            'text' : 'Overall',
            'class' : 'statboxtitle'
        });
        var totalbox = new Element('div', {
            'class' : 'statbox'
			});
        var totalcontent =  this.showTotalData(this.stats);
		if (["element","array"].contains($type(totalcontent))) {
			totalbox.adopt(totalcontent);
		}else{
			totalbox.set('html', totalcontent);
		}
                
        this.statsContainer.adopt(totaltitle, totalbox);
        
		var tmpdisplay = this.container.getStyle('display');
		this.container.setStyle('display','');
		
        this.accordion = new RaippaAccordion(this.statsContainer, 'h3.statboxtitle', 'div.statbox',{
            opacity : 0
        });
		
		this.container.setStyle('display', tmpdisplay);
        
		var search = new Element('input');
        search.store('default', 'Search name or id...');
        search.set('value', search.retrieve('default'));
        search.setStyles(this.options.searchFieldStyles);
		//search.addEvent('keyup', this.filter(search.get('value')));
		search.addEvent('keyup', function(){
            var val = search.get('value');
            if (val == search.retrieve('default')){
                val = "";
            }
            this.filter(val);
        }.bindWithEvent(this));
        
        search.addEvent('focus', function(){
            if( search.get('value') == search.retrieve('default')){
                search.set('value', '');
            }
        });
        search.addEvent('blur', function(){
            if (this.get('value') == ""){
                this.set('value', this.retrieve('default'));
            }
        });
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
        if (this.statBoxes.contains(id)){
            this.accordion.display(this.statBoxes.indexOf(id) +1);
            return;
        }
    
        if (this.statBoxes.length >= this.options.maxBoxCount){
            this.accordion.removeSection(1);
            this.statBoxes.shift();
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
        this.accordion.addSection(title,box);
        this.accordion.display(box);
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
			var item = this.formatItem(value,key);

            item.addEvent('click', function(){
                this.showStatBox(key);
            }.bindWithEvent(this));
			resultList.adopt(item, new Element('br'));
		}, this);
		
	},
	formatItem: function(value,key){
		var item = new Element('a',{
				'text': value.name,
                'class' : 'jslink'
			});
		return item;
	},
	updateData: function(){
        
        var spinner = new Element('span', { 
            "html" : "&nbsp;&nbsp;&nbsp;&nbsp;",
            'class' : 'ajax_loading',
            'styles' : {
                'display' : 'box',
                'width': '100%'
            }
        });
        this.statsContainer.grab(spinner);

		var query = new Request.JSON({
			url: '?action=searchMetasJSON',
			async: true,
			onSuccess: function(json){
				this.stats = this.parseData(json);
                spinner.destroy();

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
	formatItem : function(value,key){
		var item = new Element('a', {
				'text': value.name,
                'class' : 'jslink'
		});
		if($H(value.tries).getLength() > 10){
			item.setStyle('color', 'red');
		}
		
		return item;
		
	},
    /* Defines what is shown in overall view */
    showTotalData : function(data){
		if (!data.total) return;
        var total = $H(data.total),
        	user_cnt = $H(data.items).getLength() || 1,
        	users = $H(data.items),
			maxtries = maxtime = 0,
			ans_stats = $H(),
		 	result = [],
			type = data.total.type,
			starttime = new Date();

		users.each(function(userdata, user){
			$H(userdata.tries).each(function(trydata){
				var answers = $A(trydata.wrong).extend(trydata.right);
				answers.each(function(ans){
					if (ans_stats.has(ans)){
						ans_stats[ans]++;
					}else{
						ans_stats[ans] = 1;
					}
				});
			});
			maxtries = Math.max(maxtries, userdata.total.count);
			maxtime = Math.max(maxtime, userdata.total.time);
	    });
		
        var avg_time = (total.get('time') / (60 * user_cnt)).round(1); 
        var avg_tries = (total.get('count') /user_cnt).round(1);
		maxtime = (maxtime / 60).round(1);
		if(type == "file"){
			avg_tries = (avg_tries/3).round();
			maxtries = (maxtries/3).round();	
		}
        result.push(new Element('p', { 
			'html' : "<b>Avg time: </b>" + avg_time + "min" +
        			"<br><b>Avg tries: </b>" + avg_tries +
					"<br><b>Max time: </b>"+ maxtime +"min" +
					"<br><b>Max tries: </b>" + maxtries
					}));
					
		result.push(new Element('h4',{
			'html' : "Popularity of answers:"
			}));
		var popularity = $H();
		ans_stats.each(function(count,ans){
			value = $A(total.answers.right).contains(ans) ? "<span class='rightAnswer'>right</span>":
				 "<span class='wrongAnswer'>wrong</span>";
			if (!popularity[count]) popularity[count] = "";
			popularity[count] += "<b>"+ans+"</b>: "+ (count * 100/total.get("count")).round(1)+ 
							"% ("+value+")<br>";
		});
		var top10 = popularity.getKeys().sort().reverse().slice(0,10);
		var toptext = "";
		top10.each(function(key){
			toptext += popularity[key] || "";
		});
		result.push(new Element('p',{
			'html' : toptext
		}));

		var duration = (new Date().getTime() - starttime.getTime())/1000;
        return result;
    },
    
    /* Defines what is shown in detailed view */
    showItemData: function(item){
		var answers = this.stats.total.answers,
			userid = this.stats.items.keyOf(item),
		 	type = this.stats.total.type,
			count = $H(item.tries).getLength();
		
        var text = "<p><b>Total tries:</b> " + count + "<br>" +
            "<b>Total time: </b> " + (item.total.time / 60).round(1)  + "min</p>" +
            "<h4>Tries:</h4>";
            
            var tries = $H(item.tries);

            var keys = tries.getKeys().sort().reverse();
            keys.each(function(key){
                var value = tries.get(key);
				var missed = value.overall == "success" ? []: $A(answers.right).filter(function(ans){
					return !$A(value.right).contains(ans);
				});
				var files = value.files, fileurls = "";
				if (files.length > 0){
					$each(files, function(value){
						page = document.location.href.split("/");
						page.splice(page.length-1,0,userid);
						histpage = page.join("/");
						fileurls += '<br>file: <a target="_blank" href="'+histpage+'?action=AttachFile&do=get&target='+value+'">' +value + '</a>';
					});
				}

                text += "<p><b>" + key + "</b>" + fileurls + 
                        "<br>right: <em>" + value.right.toString() + "</em>" +
						"<br>missing right: <span class='missingAnswer'>" + missed.toString() + "</span>" +
                        "<br>wrong: <span class='wrongAnswer'> " +
                        value.wrong.toString() + "</span>";
                        
                var overall = value.overall; 
                if (overall== "success") overall =  '<span class="rightAnswer">' + overall + '</span>';
                if (overall== "failure") overall =  '<span class="wrongAnswer">' + overall + '</span>';
  
                text += "<br>overall: "+ overall +"</p>";
            });
        return text;
    }
});

var TaskStats = new Class({
    Implements: Stats,
    /* Defines what is shown in overall view */
    showTotalData : function(data){
        if (!data.total) return;

		var result = [],
			starttime = new Date(),
			type = data.total.type,
        	questions = $H(data.total.questions),
			order = $A(data.total.order);
		
        var users = $H(data.items),
        	user_cnt = users.getLength() || 1;

        result.push(new Element('h4', {
			text: "Questions:"
		}));
		var graph_times = [], graph_tries = [], graph_labels = [];
        order.each(function(question){
			var value = questions[question];
            var users_doing = users_done = maxtime = maxtries = 0;
               
            users.each(function(userdata, user){
				var tries = time = 0;
                if ($H(userdata.doing).has(question)) {
					users_doing++;
					time = userdata.doing[question].time || 0;
					tries = userdata.doing[question].count || 0;
				}
                if ($H(userdata.done).has(question)) {
					users_done++;
					time = userdata.done[question].time || 0;
					tries = userdata.done[question].count || 0;
				}
				maxtries = Math.max(maxtries, tries);
				maxtime = Math.max(maxtime, time);
				
            });
            
            var avg_time = (value.time / (60*(users_done+users_doing))).round(2);
            var avg_tries = (value.count / (users_done+users_doing)).round(2);
			var maxtime = (maxtime / 60).round(2);
            result.push(new Element('p', {
				'html' : "<b>" + question + " </b><a href='" + question+"'>(link)</a>" +
                    "<br>Average duration: <em>"+ avg_time +"</em> min and <em>" + avg_tries + "</em> tries"+
                    "<br>Users doing / total: <em>"+ users_doing + " / " + (users_doing + users_done) +"</em>" +
					"<br>Max duration: <em>" + maxtime + "</em> min and <em>" + maxtries + "</em> tries"
					}));
					
			graph_tries.push(avg_tries);
			graph_times.push(avg_time);
			graph_labels.push((graph_labels.length +1) +". ");

        });
			
					
		if (typeof(Raphael) != "undefined") {
			var graph = new Element('div').inject(document.body);
			var r = Raphael(graph, 410, 260),
            fin2 = function(){
                var y = [], res = [];
                for (var i = this.bars.length; i--;) {
                    y.push(this.bars[i].y);
                    res.push(this.bars[i].value || "0");
                }
				var text = "Questionx: \nAvg time: "+res[0] + "mins\nAvg tries: " + res[1];
                this.flag = r.g.popup(this.bars[0].x, Math.min.apply(Math, y), text).insertBefore(this);
            }, fout2 = function(){
                this.flag.animate({
                    opacity: 0
                }, 300, function(){
                    this.remove();
                });
            };
			r.g.txtattr.font = "12px bold, 'Fontin Sans', Fontin-Sans, sans-serif";
			r.g.text(200, 10,'Average tries and time usage:');

			r.g.barchart(30, 40, 340, 220, [graph_tries, graph_times],
			 {stacked: true, type: "soft"}).hoverColumn(fin2, fout2);//.label(graph_labels)
			result.push(graph);
		}
		
		var stoptime = new Date();
        var exectime = (stoptime.getTime() - starttime.getTime())/ 1000;
        //console.debug('calculation took ' + exectime + 's');

        return result;
    },
    
    /* Defines what is shown in detailed view */
    showItemData: function(item){
        var text = "<p><b>Total tries:</b> " + item.total.count + "<br>" +
            "<b>Total time: </b> " + (item.total.time / 60).round()  + "min</p>";
        
        var done = $H(item.done);
        var doing = $H(item.doing);
        if(done.getLength() > 0){
            text += "<h4>Done:</h4>";
            done.each(function(value, key){
                text += "<p><b>"+key+":</b> " + value.count + " tries, " + 
                (value.time / 60).round(1) + " mins</p>";
            });
        }
        if(doing.getLength() > 0){
            text += "<h4>Doing:</h4>";
            $H(item.doing).each(function(value, key){
                text += "<p><b>"+key+":</b> " + value.count + " tries, " + 
                (value.time / 60).round(1) + " mins</p>";
            });
        }
        
        return text;
    }
    
});