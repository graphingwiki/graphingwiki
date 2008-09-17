/* Script dragui.js
 *  A drag&drop user interface to create course/task.
 *  Requires mootools v1.2 with Drag.Move and moocanvas extensions
 */


/* Initializing some values after page is ready. boxData includes data of 
 * boxes structured in following way:
 * <id>         : box value
 * <id>_desc	: value description
 * <id>_type    : random | select
 * <id>_wrong   : where to go after a wrong answer
 * <id>_required : boxes that need to be completed before continuing
 * <id>_expires : expiration date/deadline of task
 * lkm          : count of boxes created
 * endPoints    : list of boxes without child
 */
window.addEvent('domready', function(){
 childBoxes = new Hash();
 boxData = new Hash({
     'lkm': 1,
     'endPoints': new Array()
     });

$$('#start').each(function(drag){  

    childBoxes.set(drag.id, new Array());
    drag.makeDraggable({
        onDrag: function(){
           drawline('start'); 
           }
        });
	drag.setStyles({
		'background-color' :'#6495ED',
		'cursor' : 'move',
		'text-align' : 'center',
		'left' : '800px',
		'top': '175px',
		'width': '150px',
		'height': '50px'
		});
    });

/* Making all course items draggable*/
$$('.dragItem').each(function(item){
    item.addEvent('mousedown', function(e){
        var hfix = 0;
        var drop =  $$('div[id^=item], #start');
        var e = new Event(e).stop();
        var input = this.getChildren('input')

		var value = input.get('value');
		var description = input.get('name');
        var clone = this.clone()
            .setStyles(this.getCoordinates())
            .setStyles({'opacity' : 0.7})
            .addEvent('emptydrop', function(){
                this.destroy();
            }).inject(document.body);
            clone.id = "clone";
       var drag = clone.makeDraggable({
            droppables :[drop],

            onDrag: function(element){
            element.setOpacity(0.7);
            },

            onDrop: function(el, drop){
                el.destroy();
                if(drop){
                drop.morph({
                    'height' : (50+hfix) + 'px',
                    'width' : '150px'
                });
				if(drop.id != 'start'){
				drop.getElements('canvas').morph({
                    'height' : (50 + hfix) + 'px',
                    'width' : '150px'
                });

				}
                    if(childBoxes.get(drop.id).length ==0){
                    newBox(drop.id, value.toString(), description);
                    setTimeout("drawline()", 500);
                    setTimeout("drawline()", 400);
                    setTimeout("drawline()", 200);
                    }else{
                        createMenu(drop, value, description);
                    }
                }
            },
            onEnter: function(el, drop){
						 if(drop.id == 'start'){
                         hfix = 0;
                         }else{

						 hfix = boxData.get(drop.id+'_desc').toString().length > 18 ? 15 : 0;
						 drop.getElements('canvas').morph({
							'height' : (60+ hfix) + 'px',
							'width' : '170px'
						 });
						 }
                        hfix[0]= drop.id;
						drop.morph({
							'height' : (60+hfix) + 'px',
							'width' : '170px'
						});
            },
            onLeave : function(el, drop){
			if(drop.id != 'start'){
			drop.getElements('canvas').morph({
                    'height' : (50 + hfix) + 'px',
                    'width' : '150px'
                });
			}
                drop.morph({
                    'height' : (50 + hfix) + 'px',
                    'width' : '150px'
                });
          }
        });
        drag.start(e);
    });
    item.addEvent('click',function(){
        $('clone').destroy();
        });
	item.setStyles({
	'margin-bottom' :'3px',
	'background-color' : '#E7E7E7',
	'cursor' : 'move',
	'z-index': '1'
		});


	});
var canvDiv = new Element('div',{
	'styles' :{
		'position':'absolute',
		'z-index' : '0'
	}
});
canvDiv.set('left', 0);
canvDiv.set('top' , 0);
	//$(document.body).grab(canvDiv.grab(canv),'top');
try{
loadData();
}catch(E){}
drawline();

var typesel = $('ttypesel');
typesel.addEvent('change',function(){
	selectTaskType();
});
selectTaskType();

});//domready

function selectTaskType(){
var typesel = $('ttypesel');
var value = typesel.value;
var lists = $$('div[id^=t_type_]');
lists.setStyle('display', 'none');
var selected = $(value);
if(selected){
	selected.setStyle('display', '');
}

}


/* Draws lines between all boxes and endpoints */
function drawline(id){
if(id != null){
var boxes = [$(id)];
}else{
var boxes = $(document.body).getElements('div[id^=item], #start');
$$('canvas[id^=canv]').destroy();
}
var coords = new Array();
var canvHeight = 0;
var canvWidth = 0;
for(var i=0;  i < boxes.length; i++){
	c1 = boxes[i].getCoordinates();
	pId = boxes[i].id;
	c1y = c1.top + c1.height / 2;
	c1x = c1.left + c1.width / 2;
	var childs = new Array();
	childs = childs.extend(childBoxes.get(pId));

	if(id != null){
		childs.combine(getParentBox(id));
	}

	if(boxData.get('endPoints').contains(pId)){
    childs = childs.include('ep_'+ boxes[i].id);
    }else if(childs.length < 1){
        continue;
    }
for(var j = 0 ; j < childs.length ; j++){
 c2 = $(childs[j]).getCoordinates($(pId));
 c2a = $(childs[j]).getCoordinates();
 c2y = c2a.top + 0.5 * c2a.height;
 c2x = c2a.left + 0.5 * c2a.width;
 fix_pid = getParentBox(pId).contains(childs[j]) ? childs[j] : pId;
 if(boxData.get(pId+'_wrong') == $(childs[j]).id){
color = '#FF0000';
 }else if(boxData.get(fix_pid+'_type') == 'select' &&
 childBoxes.get(fix_pid).length >1){
color = '#00FF00';
 }else if(boxData.get(fix_pid+'_type') == 'random' &&
 childBoxes.get(fix_pid).length >1){
color = '#FFFF00';
 }else{
color = '#000000';
 }


if($('canv_'+childs[j]+'_'+pId) != null){
	$('canv_'+childs[j]+'_'+pId).destroy();
}
if($('canv_'+ pId+'_'+childs[j]) != null){
	canv = $('canv_'+ pId+'_'+childs[j]);
}else{
	canv = new Canvas({
		'id': 'canv_'+ pId+'_'+childs[j],
		'styles' : {
			'position' : 'absolute'
			}
	});
	}
	xdiff = Math.max(Math.abs(c1.width/2 + c1.left - c2a.width / 2-c2a.left),4);
	ydiff = Math.max(Math.abs(c1.height/2 + c1.top - c2a.height / 2-c2a.top),4);
	
	canv.setStyle('top' , Math.min(c1y,c2y) - 2);
	canv.setStyle('left',  Math.min(c1x, c2x)- 2);

	canv.height = ydiff + 4;
	canv.width = xdiff+4;
	yswap = 0;

	if((c2y - c1y) * (c2x - c1x) < 0){
	yswap = 1;
	}

	$(document.body).grab(canv,'top');
	ctx = canv.getContext('2d');
	ctx.lineWidth = 4;
	ctx.beginPath();
	ctx.strokeStyle = color;
	ctx.moveTo(2, ydiff * yswap +2 - yswap * 4);
	ctx.lineTo(xdiff - 2, ydiff * Math.abs(yswap -1) -2 + yswap * 4);
	ctx.stroke();
}
}

}

/* Returns parents of given object */
function getParentBox(id, all){
var result = new Array();
childBoxes.each(function(value, key){
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
				tmp = tmp.combine(getParentBox(el)); 
			});
		pars = tmp.flatten();
		pars.filter(function(el){
			return result.flatten().contains(el) != true;
			});
		}
}
return result.flatten();
}


/* Returns all child nodes of given object */
function getChildBox(id){
var childs = childBoxes.get(id);
var result = new Array();
var tmp = new Array();
while(childs.length != 0){
result.combine(childs);
tmp.empty();

childs.each(function(el){
tmp.combine(childBoxes.get(el)); 
        });
childs = tmp.flatten();
}
return result.flatten();
}

/* Creates menu to edit box*/
function editMenu(button){
try{
    $('boxMenu').destroy();
}catch(e){}
    var pDiv = $(button).parentNode.parentNode;
    var menu = new Element('div', {
    'id' : 'boxMenu',
    'styles' :{
        'position' : 'absolute',
        'text-align' : 'center',
        'width' : 100,
        'height' : 50,
        'background' : '#caffee',
        'z-index' : 5,
        'top' : button.getPosition().y,
        'left' : button.getPosition().x,
        'opacity' : 0.7
            }
    });
var cancel = new Element('a', {
    'text': 'X',
    'title': 'Cancel',
    'href':'javascript:  ;',
    'styles' : {
            'color': '#FF0000',
            'position': 'absolute',
            'right' : 0,
            'text-decoration': 'none'
    },
    'events' : {'click' : function(){
                menu.destroy();
                }
    }
});

cancel.inject(menu);
createMenuButtons(menu,pDiv);

var reqMenu  = new Element('input', {
'type' : 'button',
'value' : 'Prerequisites',
'events' : { 'click' : function(){
dropMenu(pDiv);
menu.destroy();
        }
    }
});

if(getParentBox(pDiv.id).length > 1){
reqMenu.inject(menu);
}

menu.inject(document.body);
}

function createMenuButtons(menu,pDiv){
var menu = $(menu);
var pDiv = $(pDiv);

var detach = new Element('input', {
        'type' : 'button',
        'value' : 'Detach',
        'events' : {'click': function(){
				cId = childBoxes.get(pDiv.id);
				cId.each(function(c){
					boxData.get(c+'_required').erase(pDiv.id);
					if(getParentBox(c).length > 1){
						childBoxes.get(pDiv.id).erase(c);
					}
				});
                newEndPoint(pDiv);
                menu.destroy();
        }}
});
var newep = new Element('input', {
        'type' : 'button',
        'value' : 'New endpoint',
        'events' : {'click': function(){
                newEndPoint(pDiv);
                menu.destroy();
        }}
});
var delep = new Element('input', {
        'type' : 'button',
        'value' : 'Remove endpoint',
        'events' : {'click': function(){
                $('ep_'+pDiv.id).destroy();
				boxData.get('endPoints').erase(pDiv.id);
				menu.destroy();
				drawline();
        }}
});

var setExp = new Element('input', {
		'type' : 'button',
		'value' : 'Deadline',
		'events' : { 'click' : function(){
				setExpiration(pDiv);
				menu.destroy();
		}}
});

var type = new Element('input');
var del = new Element('input', {
'type' : 'button',
'value' : 'Delete box',
'events' : {'click' : function(){
if(confirm('Delete box?')){
deleteBox(pDiv);
}
menu.destroy();
        }
    }
});

menu.grab(new Element('br'));
del.inject(menu);
if(boxData.get('endPoints').contains(pDiv.id) == false){
menu.grab(new Element('br'));
newep.inject(menu);
}else if(childBoxes.get(pDiv.id).length > 0){
menu.grab(new Element('br'));
delep.inject(menu);
}
var childs  = childBoxes.get(pDiv.id);
if(childs.length == 1){
    if(childs.filter(function(c){
		return getParentBox(c).length > 1;
		}).length >0){
		menu.grab(new Element('br'));
        detach.inject(menu);
    }
}
var button_count = menu.getElements('input').length;
menu.addEvents({
    mouseenter: function(){
        this.morph({
                'opacity': 1,
                'height': 65 + button_count * 20,
                'width' : 100
            });
        },
    mouseleave : function(){
        this.morph({
                'height' : 60 + button_count * 20,
                'width' : 100,
                'opacity' : 0.9
            });
        }
    });


menu.grab(setExp);
}


/* Creates selector with caledar to set expiration date */
function setExpiration(pDiv){
var pDiv = $(pDiv);
var menu = new Element('div', {
'styles' : {
		'background-color' : '#caffee',
		'position' : 'absolute',
		'text-align' : 'center',
        'border' : '1px solid black',
		'padding' : '2px',
		'z-index' : 5,
        'top' : pDiv.getPosition().y,
        'left' : pDiv.getPosition().x + 25
}
});

var cancel = new Element('a', {
    'text': 'X',
    'title': 'Cancel',
    'href':'javascript:  ;',
    'styles' : {
            'color': '#FF0000',
            'position': 'absolute',
            'right' : 0,
            'text-decoration': 'none'
    },
    'events' : {'click' : function(){
                menu.destroy();
                }
    }
});


var cur_date = new Date();
month = cur_date.getMonth() +1;
month = month < 10 ? '0' + month : month;
day = cur_date.getDate() < 10 ? '0' + cur_date.getDate(): cur_date.getDate();
cur_date = cur_date.getFullYear() + '-' + month + '-' + day;

var def_value = boxData.get(pDiv.id +'_expires');
def_value = def_value ? def_value : cur_date;

var expdate = new Element('input',{
		'type' : 'textfield',
		'id' : 'expdate',
		'name' : 'expdate',
		'value' : def_value,
		'styles':{
			'width' : '75px'
		}
});
menu.grab(new Element('b',{
'text' : 'Deadline:'
}));
menu.grab(cancel);
menu.grab(new Element('br'));
menu.grab(expdate);

var save = new Element('input', {
		'type' : 'button',
		'value' : 'Save',
		'events' : {
			'click' : function(){
			boxData.set(pDiv.id + '_expires', expdate.value);
			//calendar.destroy()
			menu.destroy();
			}
		}
});
var remove = new Element('input',{
		'type' : 'button',
		'value' : 'Unset',
		'events' : {'click': function(){
			boxData.set(pDiv.id + '_expires', '');
			//calendar.destroy()
			menu.destroy();
		}
	}
});

menu.grab(new Element('br'));
menu.grab(save);
menu.grab(remove);
menu.grab(new Element('br'));
menu.inject(document.body);

var calendar = new Calendar({
	expdate : 'Y-m-d'
	},
	{
	draggable : false,
	direction : 1
	}
);
}


/* Menu that gives chace to select what to do when box allready has one or
   more childs. Posible actions: replace old box or add new one to tree*/
function createMenu(pDiv, value, desc){
var pDiv = $(pDiv);
    var menu = new Element('div', {
    'id' : 'boxMenu',
    'styles' :{
        'position' : 'absolute',
        'text-align' : 'center',
        'border' : '2px solid black',
        'width' : 160,
        'background' : '#caffee',
        'z-index' : 5,
        'top' : pDiv.getPosition().y,
        'left' : pDiv.getPosition().x
            }
    });

var cancel = new Element('a', {
    'text': 'X',
    'title': 'Cancel',
    'href':'javascript:  ;',
    'styles' : {
            'color': '#FF0000',
            'position': 'absolute',
            'right' : 0,
            'text-decoration': 'none'
    },
    'events' : {'click' : function(){
                menu.destroy();
                }
    }

        });

var replBut = new Element('input', {
        'type': 'button',
        'value' : 'Replace',
        'events' : {'click' : function(){
        c = pDiv.getChildren('div')[0].childNodes;
		for(i in c){
			if($type(c[i])== "textnode") c[i].nodeValue = desc;
		}
		hfix = desc.toString().length > 18? 15 : 0;
		pDiv.getChildren('div')[0].setStyle('margin-top',(-45 -hfix) + 'px');
		pDiv.getElements('canvas').setStyle('height',(50 + hfix)+ 'px');
		boxData.set(pDiv.id,value);
        menu.destroy();
        }}
 });

var randomRadio = new Element('input', {
        'type' : 'radio',
        'id' : 'rradio',
        'name' : 'typeSelect',
        'value' : 'random',
        'title' : 'Randomly selected'
        });

var selectRadio = new Element('input', {
        'type' : 'radio',
        'id' : 'sradio',
        'name' : 'typeSelect',
        'value' : 'select',
        'title' : 'Selectable',
        'checked': 'checked'
        });
var wrongRadio = new Element('input', {
        'type' : 'radio',
        'id' : 'wradio',
        'name' : 'typeSelect',
        'value' : 'wrong',
        'title' : 'After wrong answer'
        });


var newBut = new Element('input', {
        'type': 'button',
        'value' : 'New Box',
        'events' : {'click' : function(){
        var type = menu.getElements('input[name=typeSelect]');
        type = type.filter(function(el){
            return el.checked;
            }).get('value');
        newBox(pDiv.id, value, desc, type);
        menu.destroy();
        }}

});
var insAfter = new Element('input', {
        'type' : 'button',
        'value' : 'Insert after',
        'events' : {'click': function(){
        newBox(pDiv.id, value, desc,'after');
        menu.destroy();
        }}
});

var radioTab = new Element('tbody');
cancel.inject(menu);
menu.grab(new Element('br'));
radioTab.grab(new Element('tr').adopt(
                new Element('td').grab(selectRadio), 
                new Element('td').grab(new Element('label', {
                'for' : 'sradio',
                'text' :'Selectable'
            }))));

radioTab.grab(new Element('tr').adopt(
                new Element('td').grab(randomRadio), 
                new Element('td').grab(new Element('label', {
                'for' : 'rradio',
                'text' :'Random',
				'title' : 'Randomly Selected'
            }))));

/*
radioTab.grab(new Element('tr').adopt(
                new Element('td').grab(wrongRadio), 
                new Element('td').grab(new Element('label', {
                'for' : 'wradio',
                'text' :'After wrong answer'
            }))));
*/
menu.grab(new Element('table').grab(radioTab));

menu.getElements('tr, td').setStyles({'border':'none'})
menu.getElements('table').setStyles({'border':'none', 'margin':'0'})

newBut.inject(menu);
    menu.adopt(new Element('br'), new Element('hr'));
if(pDiv.id != 'start'){
replBut.inject(menu);
}
if(childBoxes.get(pDiv.id).length == 1){
menu.adopt(new Element('br'), insAfter);
}
menu.inject(document.body);
}


/*Deletes given element and corrects child relations. Checks also 
 if corrections in end points are needed*/
function deleteBox(pDiv){
var pDiv = $(pDiv);
getChildBox(pDiv.id).each(function(id){
if(boxData.get('endPoints').contains(id)){
     ep = $('ep_'+id);
     ep.setStyle('top', Math.max(ep.getPosition().y - 75, 17));
}
el = $(id);
pos = Math.max(el.getPosition().y -75, 100);
el.setStyle('top', pos);

        });
boxData.erase(pDiv.id);
childBoxes.each(function(value, key){
/* Inserting child data to parent*/
if(value.contains(pDiv.id)){
    value.erase(pDiv.id);
    value.extend(childBoxes.get(pDiv.id));

    if(value.length<1){
        boxData.get('endPoints').include(key);
        newEndPoint($(key));
    }
}
});
if(boxData.get('endPoints').contains(pDiv.id)){
    $('ep_'+pDiv.id).destroy();
}
childBoxes.erase(pDiv.id);
pDiv.destroy();
drawline();
}


/* Deletes whole child tree of given element*/
function deleteTree(){
var pDiv = $(pDiv);
//TODO: delete every child box
pDiv.destroy();
drawline();
}


/* Creates new endpoint to specified box */
function newEndPoint(pDiv){
var pDiv = $(pDiv);
boxData.get('endPoints').include(pDiv.id);

var ep = new Canvas({
    'id' : 'ep_'+ pDiv.id,
    'title' : 'End point',
    'styles' : {'position': 'absolute',
                'cursor': 'move',
                'z-index' : 1,
                'left': pDiv.getPosition().x + pDiv.getCoordinates().width /2 -10,
                'top': pDiv.getPosition().y + 75
                } 
});
ep.inject(document.body);

ep.height = 20;
ep.width = 20;
var ctx = ep.getContext('2d');
ctx.fillStyle = "#ff0000";
ctx.beginPath();
ctx.arc(10,10,10,0,Math.PI*2, false);
ctx.fill();


ep.addEvent('mousedown', function(e){
    var e = new Event(e).stop();
    var drops =  $$('div[id^=item], #start');
    var drag = ep.makeDraggable({
        droppables : [drops],
        onDrag: function(){
            drawline(pDiv.id);
        },
        onDrop: function(el, drop){
            if(drop){
				if(getParentBox(pDiv.id, true).contains(drop.id) === false){
					var p_id = el.id.replace('ep_','');
					childBoxes.get(p_id).include(drop.id);
					boxData.get('endPoints').erase(p_id);
					el.destroy();
					drawline();
				}else{
				el.destroy();
				newEndPoint(pDiv);
				}
            }
        }
    });
drag.start(e);
});
drawline();
}

/* Menu that is shown after end point has been dropped to element.
 * Used to choose which questions/courses must be completed before
 * advansing.
 */
function dropMenu(pDiv){
var menu = new Element('div', {
'styles' :{
        'position' : 'absolute',
        'text-align' : 'center',
        'border' : '2px solid black',
        'width' : 160,
        'background' : '#caffee',
        'z-index' : 5,
        'top' : pDiv.getPosition().y,
        'left' : pDiv.getPosition().x
            }

        });
var cancel = new Element('a', {
    'text': 'X',
    'title': 'Cancel',
    'href':'javascript:  ;',
    'styles' : {
            'color': '#FF0000',
            'position': 'absolute',
            'right' : 0,
            'text-decoration': 'none'
    },
    'events' : {'click' : function(){
                menu.destroy();
                }
    }
 });

menu.grab(cancel);
var tab = new Element('tbody');
menu.grab(new Element('table').grab(tab));
tab.grab(new Element('tr').adopt(new Element('td',{'colspan' : '2'}).grab(
new Element('b',{
		'text':'Required:'}
		))));
var parents = getParentBox(pDiv.id);
parents = parents.filter(function(el){
	return el != 'start';
	});
parents.each(function(id){
        var el = new Element('input', {
            'type': 'checkbox',
            'id': 'req_'+id,
            'name' : 'req_'+id,
            'value' : id
            });
    if(boxData.get(pDiv.id+'_required').contains(boxData.get(id))){
    el.set('checked','checked');
    }
        tab.grab(new Element('tr').adopt(new Element('td').grab(el),
            new Element('td').grab(new Element('label',{
                    'for' : 'req_' + id,
                    'text' :  boxData.get(id+'_desc')
                    }))));
        });
var submit = new Element('input',{
        'type' : 'button',
        'value' : 'set',
        'events' : {'click': function(){
                var req = new Array();
                menu.getElements('input[name^=req]').each(function(chk){
                    if(chk.checked){
                        req.include(boxData.get(chk.value));
                    }
                    });
                boxData.set(pDiv.id+'_required',req);
                menu.destroy();
        }}
        });

menu.getElements('tr, td').setStyles({'border':'none'})
menu.getElements('table').setStyles({'border':'none', 'margin':'0'})

menu.grab(new Element('hr'));
menu.grab(submit);
$(document.body).grab(menu);
}

/* Creates new box and sets child relations and end points. Parameters:
* to			: Element which after box should be placed (either html 
*					element id or value it's carrying)
* value			: calue to carry
* description	: label visible to user
* optional parameters:
* type			: random | select
* required		: required value (task id)
* posx			: x-coordinate
* posy			: y-coordinate
**/
function newBox(to, value, description, type, required, expires,  posx, posy){
if(to === null){
to = 'start';
}
var pDiv = $(to);

if(pDiv === null){
pid = boxData.keyOf(to);
if(to.toString() == value.toString()) return;
if(!pid) return;
pDiv = $(pid);
required = required ? required.toString().split(',') : new Array();
cid = boxData.keyOf(value);
//adding only new connection if both to and value allready exists
	if(cid && pid){
		childBoxes.get(pid).include(cid);
		if(boxData.get('endPoints').contains(pid) == true){
			boxData.get('endPoints').erase(pid);
			$('ep_'+pid).destroy();
			boxData.get(pid+'_required').combine(required);
		}
		drawline();
		return;
	}
}
lkm = boxData.get('lkm');
while($('item'+lkm)!==null){
    lkm++;
}
var id = 'item'+ lkm;
boxData.set('lkm', lkm);
boxData.set(id, value);
boxData.set(id+'_desc', description);

expires = expires ? expires.toString() : "";
boxData.set(id+'_expires', expires);

var req = required ? required : new Array();
boxData.set(id+'_required', req);
if(boxData.get('endPoints').contains(pDiv.id) == true){
    boxData.get('endPoints').erase(pDiv.id);
    $('ep_'+pDiv.id).destroy();
}
    childBoxes.set(id , new Array());

if(type == "after"){
childBoxes.set(id, childBoxes.get(pDiv.id));
childBoxes.set(pDiv.id, new Array());
getChildBox(id).each(function(id){
        if(boxData.get('endPoints').contains(id)){
            ep = $('ep_'+id);
            ep.setStyle('top', ep.getPosition().y + 75);
            }
        el = $(id);
        el.setStyle('top', el.getPosition().y + 75);
        });
}

cLkm = childBoxes.get(pDiv.id).length;

childBoxes.set(pDiv.id , childBoxes.get(pDiv.id).include(id));

if(/random|select/.test(type)){
boxData.set(pDiv.id+'_type',type);
}
if(type == "wrong"){
boxData.set(pDiv.id + '_wrong', id);
}
var box = new Element('div', {
    'id' : id,
    'class' : 'l3'
});
hfix = description.toString().length > 18 ? 15 : 0;
box.setStyles({
		'text-align' : 'center',
		'cursor' : 'move',
		'width' : '150px',
		'height' : (50 + hfix) +'px'
		});
//box.height = 50 + hfix;
//box.widht = 150;
var canv = new Canvas();
canv.setStyles({'position': 'relative'});
canv.height = 50 + hfix;
canv.width = 150;
box.adopt(canv);
var ctx = canv.getContext('2d');
ctx.lineWidth =3;
ctx.fillStyle = "#81BBF2";
ctx.beginPath();
ctx.moveTo(75,0);
ctx.bezierCurveTo(175,0,175,50 + hfix,75,50 + hfix);
ctx.bezierCurveTo(-25,50 + hfix,-25,0,75,0);
ctx.fill();

//div for text and buttons
var content = new Element('div',{
'id' : 'content',
'styles' : {
	'height' : (45+hfix) + 'px',
	'widht' : '145px',
	'position' : 'relative',
	'margin-top' : (-45 - hfix) +'px',
	'margin-left' : '3px',
	'z-index' : '2'
}});
var descText = document.createTextNode(description.toString().substring(0,30));
content.appendChild(descText);
content.grab(new Element('br'));

//box.style.background = '#' + color;
var but = new Element('input', {
        'type' : 'button',
        'value' : 'Edit'
        });
but.inject(content);
but.addEvent('click', function(){ editMenu(this);});
box.grab(content);
box.inject(document.body);

//trying to move box to free space
bX =  $(pDiv).getPosition().x + Math.ceil(cLkm/2) * 200 * Math.pow( -1, cLkm); 
bY =  $(pDiv).getPosition().y+75;
if(bX < 100){
	bX = Math.abs(bX - 100)  + 100 ;
	bY += 25;
}
if(posx){ bX = posx; }
if(posy){ bY = posy;}
box.setStyle('left', bX);
box.setStyle('top',bY);

box.addEvent('mouseenter',function(){
	showInfo(id);
});

box.makeDraggable({
onDrag: function(){
        if(boxData.get('endPoints').contains(box.id)){
            $('ep_'+box.id).setStyles({
                'left': box.getPosition().x + box.getCoordinates().width /2 -10,
                'top': box.getPosition().y + 75
                });
        }
        drawline(box.id);
        if(box.getPosition().x < 0){
            box.setStyle('left', 0);
        }
        if(box.getPosition().y < 0 ){
            box.setStyle('top', 0);
        }
    }
});
//IE hack 
canv.morph({
                    'height' : (50+hfix) + 'px',
                    'width' : '150px'
                });

if(type != "after"){
newEndPoint(box);
}
drawline();
}

/*function to show an info div about specified element*/
function showInfo(id){

if($('infodiv')){
	$('infodiv').destroy();
}

var required = boxData.get(id + '_required');
var expires = boxData.get(id + '_expires');
var type = boxData.get(id + '_type');
var childs = childBoxes.get(id);

var infodiv = new Element('div', {
'id' : 'infodiv',
'styles' : {
	'width' : '200px',
	'left' : '450px',
	'top' : '180px',
	'position' : 'absolute',
	'border' : 'solid black 1px',
	'span' : '1em',
	'background-color' : '#ffffee'
	}
});
infodiv.grab(new Element('b',{
	'html': 'Info:<br>'
}));
infodiv.grab(document.createTextNode('Id: ' + boxData.get(id)));
infodiv.grab(new Element('br'));
infodiv.grab(document.createTextNode('Name: ' + boxData.get(id+'_desc')));

if(required.length > 0){
	infodiv.grab(new Element('br'));
	infodiv.grab(document.createTextNode('Prerequisites: ' + required));
}

if(expires){
	infodiv.grab(new Element('br'));
	infodiv.grab(document.createTextNode('Deadline: ' + expires));
}
if(type){
	infodiv.grab(new Element('br'));
	infodiv.grab(document.createTextNode('Select type: ' + type));
}

/*
infodiv.grab(new Element('hr'));
infodiv.grab(new Element('b',{
	'html': 'Actions:'
}));
createMenuButtons(infodiv,id);
*/
$('content').grab(infodiv);
}

/* Turns box tree into form with hidden inputs*/
function submitTree(button){
if(button.value == "Cancel"){
	return true;
}
var form = $('submitform');
childBoxes.each(function(value,id){
        id_strip = id.replace('item','');

		childs = boxData.get('endPoints').contains(id) ? "end" : "";
		if(value){
		childs += childs.length > 1 && value.toString.length > 1 ? "," : "";
        childs += value.toString().replace(/item/g, '');
        }
		var req = boxData.get(id +'_required');
		var wrong = boxData.get(id+'_wrong');
		wrong = wrong == null ? null : wrong.replace('item','');

        if(id_strip){
form.adopt(new Element('input', {
            'type':'hidden',
            'name': id_strip+'_value',
            'value' : boxData.get(id)
            }),
        new Element('input',{
            'type' : 'hidden',
            'name' : id_strip+'_next',
            'value' : childs
            }),
        new Element('input', {
            'type' : 'hidden',
            'name' : id_strip+'_require',
            'value' : req
            }),
        new Element('input',{
            'type' : 'hidden',
            'name' : id_strip+'_type',
            'value' : boxData.get(id+'_type')
            }),
		new Element('input',{
            'type' : 'hidden',
            'name' : id_strip+'_deadline',
            'value' : boxData.get(id+'_expires')
            }),
		new Element('input',{
            'type': 'hidden',
            'name': id_strip+'_wrong',
            'value' : wrong
			})
    )}});
	if($('courseid').value.length < 1){
	alert('Please fill course id before saving');
	return false;
	}else if($('coursename').value.length < 1){
	alert('Please fill course name before saving');
	return false;
	}else{
	return true;
	}
}

