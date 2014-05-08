/**
 * @author Lauri Pokka
 *
 */

define(['mootools-more'], function() {
    "use strict";


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

    return new Class({
        Implements: [Options, Chain],

        //some values for maintaining state
        currentDate: null,

        tips: null,
        //container where this calendar is put
        container: null,
        //table element of currently visible month and its container td
        monthTab: null,
        calTd: null,
        calTr: null,

        options: {
            startDate: false, //defines what time calenar is initialized (YYYY-MM-DD)
            dateUrl: false, //url to put on date links, supports formatting for dates (%Y, %m, %d etc)
            weekNumbers: true,

            tooltips: true,
            tipContent: {}, //events to show in tips eg. {'2009-11-1': ['11.30: event1', '12.30 ...' ], ...}

            dayNames: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],

            topicWorkDayClass: 'calendar-topic-workday',
            topicWeekendClass: 'calendar-topic-weekend',
            workDayClass: 'calendar-day',
            weekendClass: 'calendar-weekend',
            todayClass: 'calendar-today'
        },

        initialize: function(element, options) {
            this.container = document.id(element);

            this.setOptions(options);

            this.currentDate = this.options.startDate ? new Date(this.options.startDate) : new Date().clearTime();

            this.build();
            this.showMonth(this.currentDate);
        },

        /*
         * Initializes calendar ui.
         */
        build: function() {
            var table = new Element('table.month-container');

            var prev = new Element('a.jslink', {
                'text': '<'
            }).addEvent('click', function() {
                    this.showMonth(this.currentDate.decrement('month'));
                }.bind(this));

            var next = new Element('a.jslink', {
                'text': '>'
            }).addEvent('click', function() {
                    this.showMonth(this.currentDate.increment('month'));
                }.bind(this));

            var dateLabel = this.dateLabel = new Element('span');

            var tbody = new Element('tbody').grab(
                new Element('tr').grab(
                    new Element('th.calendar-month').adopt(
                        prev,
                        dateLabel,
                        next)
                )).inject(table);

            this.calTr = new Element('tr').inject(tbody);
            this.calTd = new Element('td').inject(this.calTr);

            this.container.grab(table);
        },

        /*
         * Generates a calendar month and returns it as a table.
         */
        generateMonth: function(date) {
            var table = new Element('table');
            var tbody = new Element('tbody').inject(table);

            var nameTr = new Element('tr').inject(tbody);

            if (this.options.weekNumbers) {
                nameTr.grab(new Element('td'));
            }

            this.options.dayNames.each(function(day, index) {
                nameTr.grab(new Element('td', {
                    'class': index < 5 ? this.options.topicWorkDayClass : this.options.topicWeekendClass,
                    'text': day
                }));
            }, this);

            //generate a two dimensional array to represent days of month
            var tmpdate = date.clone().set('date', 1);
            var monthDays = $H(), week, month = tmpdate.get('month');
            while (tmpdate.get('month') == month) {
                week = tmpdate.getFinWeek();
                if (!monthDays[week]) monthDays[week] = [];
                monthDays[week][tmpdate.getFinDay()] = tmpdate.clone();
                tmpdate.increment('day');
            }
            while (monthDays.getLength() < 6) {
                week++;
                monthDays[week] = []
            }


            monthDays.each(function(days, weekNum) {
                var tr = new Element('tr').inject(tbody), day, tdClass, text, td,
                    href, a, texts, lastWeekNum;
                if (this.options.weekNumbers) {
                    //make sure week numbers do not overflow in december
                    lastWeekNum = date.clone().set('month', 11).set('date', 31).getFinWeek();
                    if (lastWeekNum < weekNum) {
                        weekNum = weekNum - lastWeekNum;
                    }
                    //fix week number 0
                    if (weekNum == 0) {
                        weekNum = date.clone().decrement('year').set('month', 11).set('date', 31).getFinWeek();
                    }
                    tr.grab(new Element('td.calendar-weeknumber', {
                        'text': weekNum
                    }));
                }
                for (var d = 0; d < 7; d++) {
                    day = days[d];
                    tdClass = text = "";
                    td = new Element('td');
                    if (day) {
                        if (day.format('%Y%m%d') == new Date().format('%Y%m%d')) {
                            tdClass = this.options.todayClass;
                        } else if (day.getFinDay() < 5) {
                            tdClass = this.options.workDayClass;
                        } else {
                            tdClass = this.options.weekendClass;
                        }
                        td.addClass(tdClass);
                        href = this.options.dateUrl ? day.format(this.options.dateUrl) : "";
                        a = new Element('a', {
                            'text': day.get('date'),
                            'href': href
                        });
                        if (this.options.tooltips) {
                            var title = day.format('%Y-%m-%d');
                            a.store('tip:title', title);
                            if (this.options.tipContent[title]) {
                                td.addClass('hastip');
                            }
                            texts = this.options.tipContent[title] || ["No events."];
                            a.store('tip:text', texts.join("<br>"));
                        }
                        td.grab(a);
                    }
                    tr.grab(td);
                }
            }, this);

            if (this.options.tooltips) {
                if (this.tips) this.tips.detach();
                this.tips = new Tips(tbody.getElements('a'), {
                    className: 'mootip',
                    title: function(element) {
                        element.store("title_backp", element.get("title"));
                        return element.get("title") ? element.get("title").split("::")[0] || element.get("title") : "";
                    },
                    text: function(element) {
                        var txt = element.retrieve("title_backp") ? element.retrieve("title_backp") : "";
                        return txt.split("::")[1] || element.get("rel") || element.get("href");
                    }
                });
            }

            return table;
        },

        /*
         * Changes calendar view to given month using fancy slider effect.
         */
        showMonth: function(date) {
            var newMonth = this.generateMonth(date);
            var oldTab = this.monthTab;
            this.dateLabel.set('text', date.format('%Y / %m'));

            if (this.monthTab) {
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

            } else {
                //first time
                this.calTd.grab(newMonth);
            }

            this.monthTab = newMonth;

            this.currentDate = date;
        }
    });
});
