/**
 * @author Lauri Pokka
 * @requires Mootools 1.2 and Raippa common (Mootools more with fixed Date, Binds and Tips)
 * 
 */

 window.MetaMonthCalendar = new Class({
 	Implements : [Options, Chain],
	Binds: ['generateMonth', 'showMonth'],
	
	//some values for maintaining state
	currentDate : null,
	
	tips: null,
	//container where this calendar is put
	container : null,
	//table element of currently visible month and its container td
	monthTab : null,
	calTd : null,
	calTr : null,
	
	options: {
		startDate : false, //defines what time calenar is initialized (YYYY-MM-DD)
		dateUrl : false, //url to put on date links, supports formatting for dates (%Y, %m, %d etc)
		weekNumbers : true,

		tooltips: true,		
		tipContent : {}, //events to show in tips eg. {'2009-11-1': ['11.30: event1', '12.30 ...' ], ...}
		
		dayNames : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
		
		monthContainerClass : 'month-container',
		emptyClass : 'calendar-empty',
		monthClass : 'calendar-month',
		topicWorkDayClass : 'calendar-topic-workday',
		topicWeekendClass : 'calendar-topic-weekend',
		weekNumClass : 'calendar-weeknumber',
		workDayClass : 'calendar-day',
		weekendClass : 'calendar-weekend',
		todayClass : 'calendar-today',
		
		/* Some necessary stylings */
		containerTableStyles: {
			'overflow': 'hidden',
			'width' : 340,
			'padding': '0 0 0 0',
			'position': 'relative'
		},
		contTdStyles: {
			'margin' : '0 0 0 0',
			'padding': '0 0 0 0',
			'position': 'relative',
			'border': 'none'
		},
		monthTableStyles : {
			'margin' : '0 0 0 0',
			'padding': '0 0 0 0',
			'display' : 'inline',
			'border' : 'none',
			'height': '180px',
			'width' : '100%'
		},
		monthChangerStyles: {
			'margin': '0 5px 0 5px'
		}
		
	},
	
	initialize : function(element, options){
		element = $(element);
		if (!element) return;
		
		this.container = element;
		
		this.setOptions(options);
		
		this.currentDate = this.options.startDate ? new Date(this.options.startDate) : new Date().clearTime();
				
		this.initUi();
		this.showMonth(this.currentDate);
		
	},
	
	/*
	 * Initializes calendar ui.
	 */
	initUi : function(){
		var table = new Element('table',{
			'class' : this.options.monthContainerClass,
			styles : this.options.containerTableStyles
		});
		
		var prev = new Element('a',{
			'class' : 'jslink',
			'styles': this.options.monthChangerStyles,
			'text' : '<'
		}).addEvent('click', function(){
			this.showMonth(this.currentDate.decrement('month'));
		}.bindWithEvent(this));
		
		var next = new Element('a',{
			'class' : 'jslink',
			'styles': this.options.monthChangerStyles,
			'text' : '>'
		}).addEvent('click', function(){
			this.showMonth(this.currentDate.increment('month'));
		}.bindWithEvent(this));
		
		var dateLabel = this.dateLabel = new Element('span');
		
		var tbody = new Element('tbody').grab(new Element('tr').grab(new Element('th',{
			'class': 'calendar-month'
		}).adopt(prev, dateLabel, next))).inject(table);
		
		this.calTr = new Element('tr').inject(tbody);
		this.calTd = new Element('td',{
			'styles': this.options.contTdStyles
		}).inject(this.calTr);
		
		this.container.grab(table);
		
	},
	
	/*
	 * Generates a calendar month and returns it as a table.
	 */
	generateMonth : function(date){
		var table = new Element('table').setStyles(this.options.monthTableStyles);
		var tbody = new Element('tbody').inject(table);
		
		var nameTr = new Element('tr').inject(tbody);
		
		if (this.options.weekNumbers) {
			nameTr.grab(new Element('td', {
				'class': this.options.emptyClass
			}));
		}
		
		this.options.dayNames.each(function(day, index){
			nameTr.grab(new Element('td',{
				'class' : index < 5 ? this.options.topicWorkDayClass : this.options.topicWeekendClass,
				'text': day
			}));
		},this);
		
		//generate a two dimensional array to represent days of month
		var tmpdate = date.clone().set('date', 1);
		var monthDays = $H(), week, month = tmpdate.get('month');
		while (tmpdate.get('month') == month){
			week = tmpdate.getFinWeek();
			if(!monthDays[week]) monthDays[week] = [];
			monthDays[week][tmpdate.getFinDay()] = tmpdate.clone();
			tmpdate.increment('day');
		}
		while(monthDays.getLength() < 6) {
			week ++;
			monthDays[week] = []
		}
		
		
		monthDays.each(function(days, weekNum){
			var tr = new Element('tr').inject(tbody);
			if (this.options.weekNumbers){
				//make sure week numbers do not overflow in december
				lastWeekNum = date.clone().set('month',11).set('date', 31).getFinWeek();
				if(lastWeekNum < weekNum){
					weekNum = weekNum - lastWeekNum;
				}
				//fix week number 0
				if(weekNum == 0){
					weekNum = date.clone().decrement('year').set('month',11).set('date',31).getFinWeek();
				}
				tr.grab(new Element('td',{
					'class' : this.options.weekNumClass,
					'text': weekNum
				}));
			}
			for(var d = 0; d < 7; d++){
				day = days[d];
				tdClass = text = "";
				td = new Element('td');
				if(day){
					if(day.format('%Y%m%d') == new Date().format('%Y%m%d')){
						tdClass = this.options.todayClass;
					}else if(day.getFinDay()<5){
						tdClass = this.options.weekDayClass;
					}else{
						tdClass = this.options.weekendClass;
					}
					td.addClass(tdClass);
					href = this.options.dateUrl ? day.format(this.options.dateUrl) : "";
					a = new Element('a',{
						'text': day.get('date'),
						'href': href
					});
					if(this.options.tooltips){
						var title = day.format('%Y-%m-%d');
						a.store('tip:title', title);
						if (this.options.tipContent[title]){
							td.setStyle('background-color','#FFB6C1');
                            a.addEvents({
                                'mouseenter': function(){
                                    a.setStyle('color', 'green');
                                },
                                'mouseleave': function(){
                                    a.setStyle('color', '');
                                }
                            });

						}
						texts = this.options.tipContent[title] || ["No events."];
						a.store('tip:text', texts.join("<br>"));
					}
					td.grab(a);
				}else{
					td.addClass(this.options.emptyClass);
				}
				tr.grab(td);
			}
		},this);
		
		if(this.options.tooltips){
			if (this.tips) this.tips.detach();
			this.tips = new Tips(tbody.getElements('a'));
		}

		return table;
		
	},
	
	/*
	 * Changes calendar view to given month using fancy slider effect.
	 */
	showMonth: function(date){
		var newMonth = this.generateMonth(date);
		var oldTab = this.monthTab;
		this.dateLabel.set('text', date.format('%Y / %m'));
			
		if (this.monthTab){
			//TODO: fancy slider...
/*			if(date > this.currentDate){
				newMonth.inject(this.monthTab, 'after');
                this.calTd.tween('margin-left', -1 * this.monthTab.getSize().x);

			}else{
				this.calTd.setStyle('margin-left' , -1 * this.monthTab.getSize().x);
				newMonth.inject(this.monthTab, 'before');
				this.calTd.tween('margin-left', 0);
			}
				

			(function(){				
				oldTab.destroy();
				this.calTd.setStyle('margin-left', 0);			
			}).delay(500,this);
*/
			oldTab.destroy();
			newMonth.inject(this.calTd);

		}else{
			//first time
			this.calTd.grab(newMonth);
		}
		
		this.monthTab = newMonth;
	
		this.currentDate = date;
	}
 });
