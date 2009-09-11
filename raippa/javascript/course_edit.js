/* Script couse_edit.js
 *  A drag&drop user interface to create course/task.
 *  Requires mootools v1.2 with Drag.Move and moocanvas extensions
 */

var courseEditor = new Class({
	Implements : [Options],
	Binds: ['getTasks', 'createUi', 'tasklistAdd', 'tasklistRemove','drawGraph',
	        'addTask', 'drawInfo', 'getParentBox', 'getChildBox', 'error', 'getFreeSpot', 
	        'removeFromTree', 'submitData'],
	tasks: {},
	flow: {},
	errors: [],
	options: {
		errors: true,
		containerStyles: {
			'min-width' : '900px',
			'overflow' : 'hidden'
		},
		tasklistContainerStyles: {
			'float' : 'left',
			'width' : '200px',
			'z-index' : '200'
		},
		tasklistSettings: {
			'class' : 'sortable'
		},
		dragItemStyles: {
			'opacity': '0.7',
			'z-index' : '202',
			'list-style-type': 'none'
		},
		startBoxStyles: { 
			'background-color' :'#6495ED',
			'position' : 'absolute',
			'text-align' : 'center',
			'left' : '40%',
			'z-index' : '202',
			'outline': '10px solid #6495ED'
		},
		elSize: {
			'width' : 75,
			'height' : 25
		},
		elSizeLarge: {
			'width' : 85,
			'height' : 35
		},
		taskCanvasSize: {
			'width' : 75,
			'height' : 25
		},
		graphContainerStyles: {
			'min-width' : '500px',
			'min-height' : '550px',
			'float' :'right',
			'position' :'relative',
			'backgroud-color': 'green',
			'z-inded': '200'			
		},
		infoContainerStyles: {
			'width' :'150px',
			'padding' : '5px 5px 5px 5px',
			'background-color' : '#ECF1EF',
			'font-size': 'small'
		},
		saveContainerStyles: {
			'width' :'150px',
			'padding' : '5px 5px 5px 5px',
			'background-color' : '#ECF1EF',
			'margin-top' : '10px',
			'clear': 'left'
		},
		controllerStyles: {
			'margin-top' : '20px',
			'float' : 'left'
		},
		canvasStyles: {
			'position' : 'absolute',
			'z-index': '200'
		},
		taskStyles : {
			'text-align' : 'center',
			'cursor' : 'move',
			'z-index' : '201',
			'position' : 'absolute'
		},
		taskVerticalDistance : 25
	},
	initialize : function(el, options){
		if (!el) return false;
		this.container = $(el);
		this.container.setStyles(this.options.containerStyles);
		
		this.flow = new Hash({'first': []});
		this.tasks = {
				/* data: { taskname : { title, required, element, deadline, description, list_item} , ...} */
			"data": new Hash(),
			"selected": {},
			"free":{},
			"endPoints" : []
		};
		
		this.setOptions(options);
		this.coursename = window.location.pathname;
		this.getTasks();
		this.createUi();
		//this.restoreCurrent();
		(function(){this.restoreCurrent();}).delay(100, this);
	
	},
	restoreCurrent : function(){
		var sel = this.tasks.selected;
		var tmp = ["first"];
		while (tmp.length > 0) {
			var to = tmp.shift();
			var next = sel[to];
			tmp.extend(next);

			next.each(function(task){
				var title = this.tasks.data[task].title;
				this.addTask(to, task, title);
			}, this);
		}
		this.drawGraph();
	},
	createUi : function(){

		this.tasklist = new Element('ul');
		this.tasklist.set(this.options.tasklistSettings);
		this.tasks.free.each(function(value, key){
			this.taskListAdd(key);
		}, this);
		
		var taskAddForm = new Element('form', {
			'method': 'post',
			'styles': {
				'margin-left' : '10px'
			},
			'events' :{
				'submit': function(e){
					var e = new Event(e).stop();
                    var field = taskAddForm.getElement('input[name=pagename]');
					taskAddForm.set('send',{
                        url : field.get('value') + '?action=editQuestionList&newTask=true',
                        async : false
                        });
					taskAddForm.send();
					this.getTasks();
					
					//add newly created tasks to list: a task without both list_item and element must be new
					this.tasks.data.each(function(value, key){
						if (!value.element && !value.list_item){
							this.taskListAdd(key);
						}
					}, this);
					
                    field.set('value','');
				}.bindWithEvent(this)
			}
		});
		taskAddForm.grab(new Element('input', {'name' : 'pagename', 'maxlength' : '240'}));
		taskAddForm.grab(new Element('input', {'type': 'submit', 'value': 'New Task'}));
		this.graphContainer = new Element('div');
		this.graphContainer.setStyles(this.options.graphContainerStyles);
		
		var first = new Element('div', {'id': 'first', 'text' :'start'});
		first.store('value', 'first');
		this.tasks.data['first'] = {'title' : 'first', 'element' : first};
		first.setStyles(this.options.startBoxStyles);
		first.setStyles(this.options.elSize);
		
		this.graphContainer.grab(first);
		
		this.tasklistContainer = new Element('div').adopt(this.tasklist, taskAddForm);
		this.tasklistContainer.setStyles(this.options.tasklistContainerStyles);
		
		var controllers = new Element('div');
		controllers.setStyles(this.options.controllerStyles);
		
		var saveContainer = new Element('div');
		saveContainer.setStyles(this.options.saveContainerStyles);

		saveContainer.grab(new Element('input',{
			'type': 'button',
			'value' : 'Save',
			'events': {
				'click': function(){
					this.submitData();
				}.bindWithEvent(this)
			}
		})); 
		saveContainer.grab(new Element('span', {html : "&nbsp;&nbsp;&nbsp;"}));
		saveContainer.grab(new Element('input', {
			'type': 'button',
			'value': 'Cancel',
			'events': {
				'click': function(){
					if($('overlay')){
						$('overlay').fireEvent('click');
					}else{
						this.container.destroy();
					}
				}.bindWithEvent(this)
			}
		}));
		this.infoContainer = new Element('div');
		this.infoContainer.setStyles(this.options.infoContainerStyles);

		controllers.adopt(this.infoContainer, saveContainer);
		var clear = new Element('div').setStyle('clear', 'both');
		this.container.adopt(this.tasklistContainer, controllers, this.graphContainer, clear);
		
		this.drawInfo();
	},
	taskListAdd : function(taskname){
		var item = new Element('li');

		var title = this.tasks.data[taskname]["title"];
		item.set('text', taskname);
		item.store('name', taskname);
		this.tasklist.grab(item);
		this.tasks.data[taskname]["list_item"] = item;

	    item.addEvent('mousedown', function(e){
	        
	        var e = new Event(e).stop();
	        
	        /* Create a draggable clone of task li and keep the original one. */
	        var clone = item.clone()
	            .setStyles(item.getCoordinates())
	            .setStyles(this.options.dragItemStyles)
	            .setStyle('top', item.getPosition().y)
	            .addEvent('emptydrop', function(){
	                this.destroy();
	            }).inject(document.body);
	       clone.set('id',"clone");
	
           var draw = function(){
           	this.drawGraph();
           };
           
	       /* Targets where dragged task is allowed to be dropped. */
	       var drag = clone.makeDraggable({
	            droppables :[],

	            onDrag: function(element){
	            	element.setOpacity(0.7);
	            	this.droppables = $$('div[id^=item], #first, div[id^=drop]');
	            },

	            onDrop: function(el, drop){
	                el.destroy();
	                if(drop && drop.tagName == 'DIV'){
						drop.morph(this.options.elSize);

						if(drop.id != 'first'){
							drop.getElement('canvas').morph(this.options.elSize);
						}
	                    this.addTask(drop.retrieve('value'), taskname, title);
	                }else if(drop && drop.tagName == 'CANVAS'){
	                	this.addTask(drop.retrieve('parent'), taskname, title, 'after');	
	                }
           

	                    draw.delay(500, this);
	                    draw.delay(400, this);
	                    draw.delay(200, this);

	            }.bindWithEvent(this),
	            onEnter: function(el, drop){

	            		if(drop.retrieve('parent') && drop.tagName == 'CANVAS'){
	            			this.drawGraph(drop.retrieve('parent'), drop.id);
	            		}else if(drop.tagName == 'DIV'){
	            			if(drop.id != 'first'){
	            				drop.getElement('canvas').morph(this.options.elSizeLarge);
	            			}
							drop.morph(this.options.elSizeLarge);
	            		}
	            }.bindWithEvent(this),
	            onLeave : function(el, drop){
	            	if(drop.tagName == 'DIV'){
	            		drop.morph(this.options.elSize);
	            		if(drop.id != 'first'){
	            			drop.getElement('canvas').morph(this.options.elSize);
	            		}
	            	}else if (drop.tagName == 'CANVAS'){
	            		(function(){ this.drawGraph(drop.retrieve('parent'));}).delay(400, this);
	            	}
	          }.bindWithEvent(this)
	        });
	        drag.start(e);
	    }.bindWithEvent(this));
	    
	    /* Clean ghost task lists when mouse is raised */
	    item.addEvent('click',function(){
	        $$('#clone').destroy();
	        });

	},
	taskListRemove : function(taskname){
		var task = this.tasks.data[taskname]["list_item"];
		if (task){
			task.dispose();
		}
	},
	
	/**
	* Adds task to graph three and sets child relations and end points.
	* @param to			value of task to which task is attached
	* @param value		value of new task
	* @param description label visible to user
	* optional parameters:
	* @param type		random | select
	* @param required	prerequisite (task id)
	* @param posx		x-coordinate
	* @param posy		y-coordinate
	**/
	addTask : function(to, value, description, type, required, posx, posy){
		
		var boxData = this.tasks.data;
		var editor = this;
		
		var enable_text = false;
		if(to === null){
			to = 'first';
		}
		
		//hide task list item
		this.taskListRemove(value);
		
		//stop if parent does not exist
		if (!boxData[to] || !boxData[to].element){
			this.error("parent boxData[" + to+ "] (or its .element) not found");
			return;
		}
		pDiv = boxData[to].element;
		pid = pDiv.id;
		//something has gone wrong and we were trying to attach task to itself
		if(to.toString() == value.toString()) return;
		
		var required = required ? required: [to];
			
		//adding only new connection if both to and value already exist in tree
		if(boxData[value].element && pDiv){
			this.flow.get(to).include(value);
			if(this.tasks.endPoints.contains(to) == true){
				this.tasks.endPoints.erase(to);
				$('ep_'+pid).destroy();
				boxData[value].required.combine(required);
			}
			this.drawGraph();
			return;
		}
		
		boxData[value].required = required;
		
		//remove end point from parent task
		if(this.tasks.endPoints.contains(to) == true){
		    this.tasks.endPoints.erase(to);
		    $('ep_'+pid).destroy();
		}
		
		//initialize new task flow
		this.flow[value] = [];

		//inserting new task after some tasks and attaching its children to new task 
		if(type == "after"){
			this.flow[value]= this.flow[to];
			this.flow[to] =  [value];
			//moving newly acquired children and end points a bit down
			this.getChildBox(value).each(function(value){
				var el = boxData[value].element;
		        if(this.tasks.endPoints.contains(value)){
		            ep = $('ep_'+ el.id);
		            ep.setStyle('top', ep.getPosition(this.graphContainer).y + 40);
		            }
		        el.setStyle('top', el.getPosition(this.graphContainer).y + 40 + this.options.elSize.height);
		        }, this);
		}
		
		
		//add new task to parents flow
		this.flow[to].include(value);

		if(/random|select/.test(type)){
			boxData[to].set('type',type);
		}
		
		//generating container div for task canvas
		lkm = boxData.getLength();
		while($('item'+lkm)!==null){
		    lkm++;
		}
		var id = 'item'+ lkm;
		var box = new Element('div', {
		    'id' : id,
		    'class' : 'l3'
		});
		
		
		boxData[value].element = box;
		box.store('value', value);
		box.setStyles(this.options.taskStyles);

		box.setStyles(this.options.elSize);
		var canv = new Canvas();
	
		canv.set('height', this.options.taskCanvasSize.height + 'px');
		canv.set('width', this.options.taskCanvasSize.width +'px');

		canv.setStyles(this.options.elSize);
		box.grab(canv);
		var ctx = canv.getContext('2d');
		ctx.lineWidth =3;
		ctx.fillStyle = "#81BBF2";
		ctx.beginPath();

		//draw an ellipse (37,0), (75,12), (37,25), (0,12)
		ctx.moveTo(37,0);
		ctx.bezierCurveTo(87,0,87,25,37,25);
		ctx.bezierCurveTo(-12,25,-12,0,37,0);

		ctx.fill();

		//div for text and buttons
		var content = new Element('div',{
		'id' : 'box_content',
		'title' : description,
		'styles' : {
			'height' : (45 - this.options.taskCanvasSize.height) + 'px',
			'width' : (145 - this.options.taskCanvasSize.width)+'px',
			'position' : 'relative',
			'margin-top' : (-50 + this.options.taskCanvasSize.height) +'px',
			'z-index' : '202',
			'font-size':  '10px'
		}});
		
		//show only 10 first characters of title in the task ball
		var descText = document.createTextNode(description.toString().substring(0,10));

		content.appendChild(descText);
		box.grab(content);
		this.graphContainer.grab(box);
		//trying to move box to free space
		
		var position = this.getFreeSpot(pDiv);
		box.setStyle('left', position.x);
		box.setStyle('top', position.y);

		box.addEvent('click',function(){
			this.drawInfo(value);
			box.highlight('#C0FF3E');
		}.bindWithEvent(this));

		box.makeDraggable({
		onDrag: function(){
		        if(this.tasks.endPoints.contains(value)){
		        	var top = box.getPosition(this.graphContainer).y + this.options.taskVerticalDistance 
		        				+ this.options.taskCanvasSize.height - 20;
		        	var left =  box.getPosition(this.graphContainer).x + box.getCoordinates(this.graphContainer).width /2 -10;
		            $('ep_'+box.id).setStyles({
		                'left': left,
		                'top': top
		                });
		        }
		        this.drawGraph(box.id);
		        if(box.getPosition(this.graphContainer).x < 0){
		            box.setStyle('left', 0);
		        }
		        if(box.getPosition(this.graphContainer).y < 0 ){
		            box.setStyle('top', 0);
		        }
		    }.bindWithEvent(this)
		});

		tip = new Tips(content);

		if(type != "after"){
			this.newEndPoint(value);
		}
		this.drawGraph();	
	},
	/* Tries to find good spot near given element, returns a object with x and y coodrinates*/
	getFreeSpot: function(element){
		var result = {};
		var el = $(element);
		var cCnt = 0;
		if (el.retrieve('value')){
			cCnt = this.flow[el.retrieve('value')].length -1 ;
		}
		var ppos = $(element).getCoordinates(this.graphContainer);
		result.x =  ppos.left +Math.ceil(cCnt/2) * 100 * Math.pow( -1, cCnt);
		result.y=  ppos.top + this.options.taskVerticalDistance + this.options.elSize.height;
		if(result.x < 100){
			result.x = Math.abs(result.x - 100)  + 100;
			result.y += 100;
		}
		return result;
	},
	/* Draws lines between task balls*/
	drawGraph : function(id, highlight){
		if(id != null){
			var boxes = [$(id)];
		}else{
			var boxes = $(document.body).getElements('#first, div[id^=item]');
			$$('canvas[id^=canv]').destroy();
		}
		
		var boxData = this.tasks.data;

		var coords = new Array();
		var canvHeight = 0;
		var canvWidth = 0;
		var maxheight = 0;
		var hfixdiv = this.graphContainer;
		var hfix = hfixdiv.getPosition(this.graphContainer);

		for(var i=0;  i < boxes.length; i++){
			c1 = boxes[i].getCoordinates(this.graphContainer);
			pId = boxes[i].id;
			pValue = $(pId).retrieve('value');
			c1y = c1.top + c1.height / 2;
			c1x = c1.left + c1.width / 2;
			var childs_vals = new Array();
			childs_vals = childs_vals.extend(this.flow[pValue]);

			if(id != null){
				childs_vals.combine(this.getParentBox(pValue));
			}else{
				maxheight = Math.max(maxheight, c1.top - hfix.y + 100);
			}
			childs = childs_vals.map(function(value){
				return this.tasks.data[value].element.id;
			}, this);
			
			if(this.tasks.endPoints.contains(pValue)){
				childs = childs.include('ep_'+ boxes[i].id);
		    }else if(childs.length < 1){
		        continue;
		    }
		for(var j = 0 ; j < childs.length ; j++){
		 c = $(childs[j]);
		 c2 = c.getCoordinates($(pId));
		 c2a = c.getCoordinates(this.graphContainer);
		 c2y = c2a.top + 0.5 * c2a.height;
		 c2x = c2a.left + 0.5 * c2a.width;
		 //checking if "child" is actually child or end point
		 is_ep = 'ep_' + pId == childs[j]? true: false;
		 is_child = is_ep || this.flow.get(pValue).contains($(childs[j]).retrieve('value')) ? true:false ; 
		 fix_pid = is_child ? pId :childs[j];
		 fix_cid = is_child ? childs[j] : pId;
		 fix_pid_value = $(fix_pid).retrieve('value');
		 fix_cid_value = $(fix_cid).retrieve('value');
		 if(is_ep || this.tasks.data[fix_cid_value].required.contains(fix_pid_value)){
			color = '#FF0000';
		 }else{
			color = '#000000';
		 }

		 /* destroying old canvas if it's upside down*/
		if($('canv_'+childs[j]+'_'+pId) != null){
			$('canv_'+childs[j]+'_'+pId).destroy();
		}
		if($('canv_'+ pId+'_'+childs[j]) != null){
			canv = $('canv_'+ pId+'_'+childs[j]);
		}else{
			canv = new Canvas({
				'id': 'canv_'+ pId+'_'+childs[j]
			});
			canv.store('parent', fix_pid);
			canv.store('child', fix_cid);
			
			canv.setStyles(this.options.canvasStyles);
			}
			var pad = 10;
			xdiff = Math.max(Math.abs(c1x - c2x),0);//pad *2);
			ydiff = Math.max(Math.abs(c1y - c2y),0);//pad *2);

			canv.setStyle('top' , Math.min(c1y,c2y) - pad);
			canv.setStyle('left',  Math.min(c1x, c2x)- pad);

			canv.height = ydiff + pad *2 ;
			canv.width = xdiff + pad *2;
			yswap = 0;

			if((c2y - c1y) * (c2x - c1x) <= 0){
			yswap = 1;
			}

			this.graphContainer.grab(canv,'top');
			ctx = canv.getContext('2d');
			//drawing lines and leaving padding around
			ctx.translate(pad , pad);
			
			var lineWidth = 3;
			//make stronger lines with green color if highlight matches
			if (canv.id == highlight){
				lineWidth = 5;
				color = "green";
			}
			
			ctx.lineWidth = lineWidth;
			ctx.beginPath();
			ctx.strokeStyle = color;
			var xfrom = 0;
			var yfrom = ydiff * yswap;
			var xto = xdiff;
			var yto = ydiff * Math.abs(yswap -1);
			ctx.moveTo(xfrom, yfrom);
			ctx.lineTo(xto, yto);
			ctx.stroke();

			//draw a beautiful arrow only if we are drawing line between tasks
			if (!is_ep){
				//calculating points for arrow
				var midx = (xto - xfrom)/2;
				var midy = Math.abs(yto - yfrom)/2;
				var vx = xto - xfrom;
				var vy = yto - yfrom;
				//unit vector for line
				var v0x = vx / Math.sqrt(vx*vx + vy*vy) * 15;
				var v0y = vy / Math.sqrt(vx*vx + vy*vy) * 15;
				//determining which way to put arrow
				if(c1x > c2x || c1x == c2x && is_child && c1y > c2y || c1x == c2x && c1y < c2y){
					var reverse = 1;
				}else{
					var reverse = -1;
				}
				//check if c1 is really c2's parent
				if(is_child){
					reverse *= -1;
				}
				midx += v0x * reverse / 2;
				midy += v0y * reverse / 2;
				var ang = Math.PI * (1/2 + reverse * 2/6);
				var a1x = v0x * Math.cos(ang) - v0y * Math.sin(ang) + midx;
				var a1y = v0x * Math.sin(ang) + v0y * Math.cos(ang) + midy;
				var a2x = v0x * Math.cos(-ang) - v0y * Math.sin(-ang) + midx;
				var a2y = v0x * Math.sin(-ang) + v0y * Math.cos(-ang) + midy;
				ctx.fillStyle = color;
				ctx.moveTo(midx,midy);
				ctx.lineTo(a1x, a1y);
				ctx.lineTo(a2x, a2y);
				ctx.fill();
			}
		}
		}
		if(!id){
			hfixdiv.setStyle('height', maxheight + 50);
		}

	},
	drawMenu: function(){
		
	},
	/* Returns parents of given object */
	getParentBox : function (id, all){
	var result = new Array();
	this.flow.each(function(value, key){
	    if(value.contains(id)){
	        result.include(key);
	    }
	});
		if(all === true){
			var tmp = new Array();
			var pars = result.flatten();
			while(pars.length != 0){
				result = result.combine(pars);
				tmp = tmp.empty();
				pars.each(function(el){
					tmp = tmp.combine(this.getParentBox(el)); 
				}, this);
			pars = tmp.flatten();
			pars.filter(function(el){
				return result.flatten().contains(el) != true;
				});
			}
	}
	return result.flatten();
	},
	/* Creates new end point to specified box */
	newEndPoint : function (value){
		var childBoxes = this.flow;
	
		var pDiv = this.tasks.data[value].element;
		this.tasks.endPoints.include(value);
		var top = pDiv.getPosition(this.graphContainer).y + this.options.taskVerticalDistance
				+ this.options.taskCanvasSize.height -20 ;
		var left =  pDiv.getPosition(this.graphContainer).x + 
				pDiv.getCoordinates(this.graphContainer).width /2 -10;

		var ep = new Canvas({
			'id' : 'ep_'+ pDiv.id,
			'title' : 'End point',
			'styles' : {
				'position': 'absolute',
				'cursor': 'move',
				'z-index' : 201,
	            'left': left,
	            'top': top
			} 
		});
		ep.inject(this.graphContainer);

		ep.height = 20;
		ep.width = 20;
		var ctx = ep.getContext('2d');
		ctx.fillStyle = "#ff0000";
		ctx.beginPath();
		ctx.arc(10,10,10,0,Math.PI*2, false);
		ctx.fill();


		ep.addEvent('mousedown', function(e){
			var e = new Event(e).stop();
			var drops =  $$('div[id^=item], #first');
			var drag = ep.makeDraggable({
				droppables : [drops],
				onDrag: function(){
					this.drawGraph(pDiv.id);
				}.bindWithEvent(this),
				onDrop: function(el, drop){
					if(drop){
						var new_parent = drop.retrieve('value');
						//check that we are not going to create loops
						if(this.getParentBox(value, true).contains(new_parent) === false){
							this.flow.get(value).include(new_parent);
							this.tasks.endPoints.erase(value);
							this.tasks.data[new_parent].required.include(value);
							el.destroy();
							this.drawGraph();
						}else{
							el.destroy();
							this.newEndPoint(value);
						}
					}
				}.bindWithEvent(this)
			});
			drag.start(e);
		}.bindWithEvent(this));
		this.drawGraph();
	},

	/* Returns all child nodes of given object */
	getChildBox: function (id){
		var childs = this.flow.get(id);
		var result = new Array();
		var tmp = new Array();
		while(childs.length != 0){
			result.combine(childs);
			tmp.empty();

			childs.each(function(el){
				tmp.combine(this.flow.get(el)); 
			}, this);
			childs = tmp.flatten();
		}
	return result.flatten();
	},
	/* Retrieves available tasks using json ajax query*/
	getTasks: function(){
		var editor = this;
		
		var query = new Request.JSON({
			url: '?action=searchMetasJSON',
			async: false,
			onSuccess: function(json){
				editor.tasks["free"] = $H(json.free);
				editor.tasks["selected"] = $H(json.selected);
				var data = $H(json.data).map(function(value){
							value.element = false;
							value.list_item = false;
							return $H(value);
						});
				//combining new and old data, old data is not overwritten
				editor.tasks.data.combine(data);
			}
		});
		query.get({'args':'tasks'});
	},
	removeFromTree : function(task){
		var task_ob = this.tasks.data[task];
		var parents = this.getParentBox(task);
		var childs = this.getChildBox(task);
		var required = task_ob.required;
		
		//add task children to every parent
		parents.each(function(parent){
			this.flow[parent].erase(task);
			this.flow[parent].extend(childs);
			//adding end points if needed
			if (this.flow[parent].length == 0){
				this.newEndPoint(parent);
			}
		}, this);
		
		//add current task requirements to every child
		childs.each(function(child){
			this.tasks.data[child].required.extend(required);
		}, this);
		
		//removing orphan end points
		this.tasks.endPoints.erase(task);
		var ep = $('ep_'+ task_ob.element.id);
		if (ep){
			ep.destroy();
		}
		//destroy tree element, remove from flow and empty requirements 
		this.flow.erase(task);
		task_ob.element.destroy();
		task_ob.element = false;
		required.empty();
		
		//add task back to task list
		this.taskListAdd(task);
		
		this.drawGraph();
	},
	drawInfo : function(task){
		this.infoContainer.empty();

		if (!task){
			this.infoContainer.grab(new Element('p', {'text' :'Click a task to see more information.'}));
			return;
		}
		
		var data = this.tasks.data[task];
		var info = [];
		var title = new Element('h4', {text : data.title });
		info.push(title);
		
		if (data.description){
			info.push(new Element('p').appendText(data.description));
			
		}
		if (data.deadline){
			info.push(new Element('p').grab(new Element('b', {text : 'deadline: '}))
					.appendText(data.deadline));

		}
		
		var next = this.flow[task];
		if (next.length > 0){
			info.push(new Element('b',{ text : 'Next: '}));
			var nextlist = new Element('ul');
			next.each(function(child){
				var title = this.tasks.data[child].title;
				var li = new Element('li', { 'text' : title});
				li.grab(new Element('a', { 
					'class' : 'jslink',
					'text' : ' detach',
					'events': {
						'click': function(){
							this.flow[task].erase(child);
							if (this.flow[task].length == 0){
								this.newEndPoint(task);
							}
							this.drawGraph();
							this.drawInfo(task);
						}.bindWithEvent(this)
					}
				}));
				info.push(li);
			}, this);
		}
		
		if (! this.tasks.endPoints.contains(task)){
			info.push(new Element('p')
				.grab(new Element('a', {
					'text' : 'new connection',
					'class' : 'jslink',
					'events' : {
						'click' : function(){
							this.newEndPoint(task);
							this.drawInfo(task);
					}.bindWithEvent(this)
				}
			}))
			);
		}
		
		info.push(new Element('input',{
			'type': 'button',
			'value': 'remove',
			'events': {
				'click': function(){
					this.removeFromTree(task);
					this.drawGraph();
				}.bindWithEvent(this)
			}
		}));
		this.infoContainer.adopt(info);
		
	},
	submitData: function(){
		var form = new Element('form', {
			'action' : '?action=editCourseFlow',
			'method': 'post'
		});
		
		sel = this.flow;
		var tmp = ["first"];
		while (tmp.length > 0) {
			var to = tmp.shift();
			var next = sel[to];
			tmp.extend(next);
			next.each(function(task){
				form.grab(new Element('input', {
					'type': 'hidden',
					'name': 'flow_'+to,
					'value': task
				}));
			}, this);
		}

		form.submit();
	},
	error: function(msg){
		if(this.options.errors){
			msg = msg + "\n tasks.data keys: "+ this.tasks.data.getKeys() + "  values: " + this.tasks.data.getValues() 
			+ ") \nflow keys: "+ this.flow.getKeys() +	" values: " + this.flow.getValues();
			
			this.errors.include(msg);
			console.debug(msg);
		}
	}
});