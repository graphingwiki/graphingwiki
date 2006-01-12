#! /usr/bin/env python

import cgi, os, re, urllib, sys
import cgitb; cgitb.enable()
from base64 import b64encode

script = """
    <script type="text/ecmascript"><![CDATA[
// original contex menu retained
var origContext = contextMenu.documentElement;

// State variables (mapped to URL)
var selected = "";
var prune = "None";
var limit = "";
var path = "";
var cycles = "False";

// Saves the selected protocols in the current URL
var origSelected = "";

// context menu only state variable
var stateChanged = 0;

// Get the needed stuff from URL
function init() {
    var body = document.URL.split("?");

    if(body.length < 2)
        return;
        
    var items = body[1].split("&");

    for(var i in items) {
        if(items[i].indexOf("proto") != -1) {
            // Get existing limit string
            var startSelected = items[i].indexOf("=")+1;
            origSelected = items[i].substring(startSelected,items[i].length);
        }
        if(items[i].indexOf("limit") != -1) {
            // Get existing limit string
            var startLimit = items[i].indexOf("=")+1;
            limit = items[i].substring(startLimit,items[i].length);
        }
        if(items[i].indexOf("prune") != -1) {
            // Get existing limit string
            var startPrune = items[i].indexOf("=")+1;
            prune = items[i].substring(startPrune,items[i].length);
        }
        if(items[i].indexOf("path") != -1) {
            // Get existing limit string
            var startPath = items[i].indexOf("=")+1;
            path = items[i].substring(startPath,items[i].length);
        }
        if(items[i].indexOf("cycles") != -1) {
            // Get existing limit string
            var startCycles = items[i].indexOf("=")+1;
            if(items[i].substring(startCycles,items[i].length) == "True")
                cycles = "True";
        }
    }
}

function mouseDown(evt) {
    if(evt.button == 2) {
	// on right button down, make context menu
	buildContextMenu(evt);
    }
}

function mouseUp(evt) {
    if(evt.button == 2) {
	// on right button up, revert menu to original
        contextMenu.replaceChild(origContext, contextMenu.documentElement);
    }
}

function buildContextMenu(evt) {
    node = evt.target;

    var name = node.parentNode.getAttribute("xlink:title");
    if(name == '') {
	return;
    }

    var menu = contextMenu.createElement('menu');

    var headerNode = contextMenu.createElement('header');
    var headerText = contextMenu.createTextNode( 'uts' );
    headerNode.appendChild(headerText);
    menu.appendChild(headerNode);

    var itemNode = contextMenu.createElement('item');
    var itemText = contextMenu.createTextNode(name);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    menu.appendChild( contextMenu.createElement('separator') );

    var itemNode = contextMenu.createElement('item');
    var itemText = contextMenu.createTextNode('Parameters:');
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var subMenuNode = contextMenu.createElement('menu');
    var headerNode = contextMenu.createElement('header');
    if(prune == "-1") {
       var headerText = contextMenu.createTextNode('Most similar edges pruned');
    } else if(prune == "None") {
       var headerText = contextMenu.createTextNode('No edges pruned');
    } else {
       var headerText = contextMenu.createTextNode('More than ' + prune + ' similar edges pruned');
    }
    headerNode.appendChild(headerText);
    subMenuNode.appendChild(headerNode);

    var itemNode = contextMenu.createElement('item');
    var itemText = contextMenu.createTextNode('More edge pruning');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    itemAttribute.setValue('raisePrune()');
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    subMenuNode.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemText = contextMenu.createTextNode('Less edge pruning');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    itemAttribute.setValue('lowerPrune()');
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    subMenuNode.appendChild(itemNode);
    menu.appendChild(subMenuNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("S")) {
        var itemText = contextMenu.createTextNode('Limit Standard RFC:s');
        itemAttribute.setValue('addLimit("S")');
    } else {
        var itemText = contextMenu.createTextNode('Allow Standard RFC:s');
        itemAttribute.setValue('removeLimit("S")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("PS")) {
        var itemText = contextMenu.createTextNode('Limit Proposed Standard RFC:s');
        itemAttribute.setValue('addLimit("PS")');
    } else {
        var itemText = contextMenu.createTextNode('Allow Proposed Standard RFC:s');
        itemAttribute.setValue('removeLimit("PS")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("DS")) {
        var itemText = contextMenu.createTextNode('Limit Draft Standard RFC:s');
        itemAttribute.setValue('addLimit("DS")');
    } else {
        var itemText = contextMenu.createTextNode('Allow Draft Standard RFC:s');
        itemAttribute.setValue('removeLimit("DS")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("I")) {
        var itemText = contextMenu.createTextNode('Limit Informational RFC:s');
        itemAttribute.setValue('addLimit("I")');
    } else {
        var itemText = contextMenu.createTextNode('Allow Informational RFC:s');
        itemAttribute.setValue('removeLimit("I")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("E")) {
        var itemText = contextMenu.createTextNode('Limit Experimental RFC:s');
        itemAttribute.setValue('addLimit("E")');
    } else {
        var itemText = contextMenu.createTextNode('Allow Experimental RFC:s');
        itemAttribute.setValue('removeLimit("E")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("H")) {
        var itemText = contextMenu.createTextNode('Limit Historic RFC:s');
        itemAttribute.setValue('addLimit("H")');
    } else {
        var itemText = contextMenu.createTextNode('Allow Historic RFC:s');
        itemAttribute.setValue('removeLimit("H")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("N")) {
        var itemText = contextMenu.createTextNode('Limit RFC:s of no type');
        itemAttribute.setValue('addLimit("N")');
    } else {
        var itemText = contextMenu.createTextNode('Allow RFC:s of no type');
        itemAttribute.setValue('removeLimit("N")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("R")) {
        var itemText = contextMenu.createTextNode('Limit References');
        itemAttribute.setValue('addLimit("R")');
    } else {
        var itemText = contextMenu.createTextNode('Allow References');
        itemAttribute.setValue('removeLimit("R")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("U")) {
        var itemText = contextMenu.createTextNode('Limit Updates');
        itemAttribute.setValue('addLimit("U")');
    } else {
        var itemText = contextMenu.createTextNode('Allow Updates');
        itemAttribute.setValue('removeLimit("U")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    var itemNode = contextMenu.createElement('item');
    var itemAttribute = contextMenu.createAttribute('onactivate');
    if(!hasLimit("O")) {
        var itemText = contextMenu.createTextNode('Limit Obsoletes');
        itemAttribute.setValue('addLimit("O")');
    } else {
        var itemText = contextMenu.createTextNode('Allow Obsoletes');
        itemAttribute.setValue('removeLimit("O")');
    }
    itemNode.setAttributeNode(itemAttribute);
    itemNode.appendChild(itemText);
    menu.appendChild(itemNode);

    if((selected.split(",").length > 1) || (path != "")) {
        var itemNode = contextMenu.createElement('item');
        var itemAttribute = contextMenu.createAttribute('onactivate');
        if(cycles == "True") {
            var itemText = contextMenu.createTextNode('Limit path cycles');
            itemAttribute.setValue('stateChanged = 1; cycles = "False"');
        } else {
            var itemText = contextMenu.createTextNode('Allow path cycles');
            itemAttribute.setValue('stateChanged = 1; cycles = "True"');
        }
        itemNode.setAttributeNode(itemAttribute);
        itemNode.appendChild(itemText);
        menu.appendChild(itemNode);
    }

    if(stateChanged) {
        menu.appendChild( contextMenu.createElement('separator') );

        var itemNode = contextMenu.createElement('item');
        var itemText = contextMenu.createTextNode('Refresh with new parameters');
        var itemAttribute = contextMenu.createAttribute('onactivate');
        itemAttribute.setValue('refreshParams()');
        itemNode.setAttributeNode(itemAttribute);
        itemNode.appendChild(itemText);
        menu.appendChild(itemNode);
    }

    if(selected != "") {
        menu.appendChild( contextMenu.createElement('separator') );

        var itemNode = contextMenu.createElement('item');
        var itemText = contextMenu.createTextNode('Selected RFC:s: ' + selected);
        itemNode.appendChild(itemText);
        menu.appendChild(itemNode);

        var subMenuNode = contextMenu.createElement('menu');
        var headerNode = contextMenu.createElement('header');
        var headerText = contextMenu.createTextNode('Spread from selected protocols');
        headerNode.appendChild(headerText);
        subMenuNode.appendChild(headerNode);

        var itemNode = contextMenu.createElement('item');
        var itemText = contextMenu.createTextNode('With current parameters');
        var itemAttribute = contextMenu.createAttribute('onactivate');
        itemAttribute.setValue('newView(1, "")');
        itemNode.setAttributeNode(itemAttribute);
        itemNode.appendChild(itemText);
        subMenuNode.appendChild(itemNode);

        var itemNode = contextMenu.createElement('item');
        var itemText = contextMenu.createTextNode('Without parameters');
        var itemAttribute = contextMenu.createAttribute('onactivate');
        itemAttribute.setValue('newView(0, "")');
        itemNode.setAttributeNode(itemAttribute);
        itemNode.appendChild(itemText);
        subMenuNode.appendChild(itemNode);

        menu.appendChild(subMenuNode);
    }

    if(selected.split(",").length > 1) {
        var subMenuNode = contextMenu.createElement('menu');
        var headerNode = contextMenu.createElement('header');
        var headerText = contextMenu.createTextNode('Shortest paths between selected protocols');
        headerNode.appendChild(headerText);
        subMenuNode.appendChild(headerNode);

        var itemNode = contextMenu.createElement('item');
        var itemText = contextMenu.createTextNode('With current parameters');
        var itemAttribute = contextMenu.createAttribute('onactivate');
        itemAttribute.setValue('newView(1, "short");');
        itemNode.setAttributeNode(itemAttribute);
        itemNode.appendChild(itemText);
        subMenuNode.appendChild(itemNode);

        var itemNode = contextMenu.createElement('item');
        var itemText = contextMenu.createTextNode('Without parameters');
        var itemAttribute = contextMenu.createAttribute('onactivate');
        itemAttribute.setValue('newView(0, "short");');
        itemNode.setAttributeNode(itemAttribute);
        itemNode.appendChild(itemText);
        subMenuNode.appendChild(itemNode);

        menu.appendChild(subMenuNode);

        var subMenuNode = contextMenu.createElement('menu');
        var headerNode = contextMenu.createElement('header');
        var headerText = contextMenu.createTextNode('All paths between selected protocols');
        headerNode.appendChild(headerText);
        subMenuNode.appendChild(headerNode);

        subMenuNode.appendChild( contextMenu.createElement('separator') );

        var itemNode = contextMenu.createElement('item');
        var itemText = contextMenu.createTextNode('With current parameters');
        var itemAttribute = contextMenu.createAttribute('onactivate');
        itemAttribute.setValue('newView(1, "all");');
        itemNode.setAttributeNode(itemAttribute);
        itemNode.appendChild(itemText);
        subMenuNode.appendChild(itemNode);

        var itemNode = contextMenu.createElement('item');
        var itemText = contextMenu.createTextNode('Without parameters');
        var itemAttribute = contextMenu.createAttribute('onactivate');
        itemAttribute.setValue('newView(0, "all");');
        itemNode.setAttributeNode(itemAttribute);
        itemNode.appendChild(itemText);
        subMenuNode.appendChild(itemNode);

        menu.appendChild(subMenuNode);
    }

    contextMenu.replaceChild( menu, contextMenu.documentElement );
}

// query, add, remove protocol type limitations
function hasLimit(type) {
    var limitList = limit.split(",");

    if(limitList.length > 0) {
	for(var i in limitList) {
	    if(limitList[i] == type) {
               return 1;
            }
        }
    } 

    // No limits at all or no limit found
    return 0;
}

function addLimit(type) {
    stateChanged = 1;

    if(limit.length == 0) {
	limit = type; 
    }
    else if(!hasLimit(type)) {
  	limit = limit + "," + type;
    }
}

function removeLimit(type) {
    stateChanged = 1;

    // Remove type from limit
    var limitList = limit.split(",");
    limit = ""

    if(limitList.length > 0) {
	for(var i in limitList) {
	    if(limitList[i] != type) {
		limit = limit + limitList[i] + ',';
            }
        }
        // remove end comma
	limit = limit.substring(0,limit.length-1);
    }
}
	
// Toggle selection status of nodes, by inserting/removing stroke-dasharray
function setSelected(name, curstyle) {
    var style = ""

    if(selected.length == 0) {
	selected = name; 
        style = curstyle + "stroke-dasharray:5,3;";
    }
    else {
        if(selected.indexOf(name) == -1) {
  	    selected = selected + "," + name; 
            style = curstyle + "stroke-dasharray:5,3;";
        }
    }

    return style;
}

function removeSelected(name, curstyle) {
    var style = "";
    var items = curstyle.split(";");

    // remove stroke-dasarray from style
    for(var i in items) {
	if(items[i].indexOf("stroke-dasharray") == -1) { 
	    if(items[i].indexOf(":") != -1) {
		style = style + items[i] + ";";
	    }
	}
    }

    // Remove name from selected
    var selList = selected.split(",");
    selected = ""

    if(selList.length > 0) {
	for(var i in selList) {
	    if(selList[i] != name) {
		selected = selected + selList[i] + ',';
            }
        }
	selected = selected.substring(0,selected.length-1);
    }

    return style;
}

function selectNode(evt) {
    // on right click, jump to the link in the label
    // hrefs are not handy - activata on both left and middle button
    if(evt.button == 0) {
	var link = evt.target.parentNode.getAttribute("xlink:label");
        var number = evt.target.parentNode.parentNode.firstChild.firstChild.data;
	browserEval('window.open("' + link + '", "' + number + '", "location,scrollbars")' );
	return;
    } else if(evt.button == 2) {
	return;
    }

    // either text ^ a or polygon ^ a
    // otherwise clicking on text does not affect style
    var rect = evt.target.parentNode;

    var curstyle = rect.getAttributeNS(null, "style");

    // a ^ g > title > #text -> data (at least!)
    var name = rect.parentNode.firstChild.firstChild.data;

    // The name must be a number (legend nodes are not selected)
    if(!parseInt(name))
        return;

    //	    var name = rect.nodeName;

    var style = ""

	// if selected, remove; else, add
	if(selected.indexOf(name) != -1) {
	    style = removeSelected(name, curstyle); 
        }
	else {
	    style = setSelected(name, curstyle); 
        }

    rect.setAttributeNS(null, "style", style);
}

// Following functions change pruning parameter, nothing too fancy
function raisePrune() {
    stateChanged = 1;

    if(prune == "10")
	return;
    else if(prune == "None")
	prune = "-1";
    else if(prune == "-1")
	prune = "10";	
}

function lowerPrune() {
    stateChanged = 1;

    if(prune == "None") 
	return;
    else if(prune == "10")
	prune = "-1";
    else if(prune == "-1")
	prune = "None";
}

function changePrune(evt) {

    if(evt.button == 0) {
	lowerPrune()
    } else if(evt.button == 1) {
	raisePrune()
    } else {
	return;
    }
}

// get desired parameters
// if <  2 nodes are selected: give general params or nothing
// if >= 2 nodes are selected: either give path parameter (if correct)
//                             or give general params, path and cycle
function getParams(params) {
    var paramstring = "";

    // add general parameters if requested
    if(params)
    {
        if(prune != "None") 
	    paramstring = '&prune=' + prune;

        if(limit != "") 
            paramstring = paramstring + '&limit=' + limit;
    }

    // always add path, if applicable
    if((path == 'all' || path == 'short') && (selected.split(",").length > 1))
    {
        paramstring = paramstring + '&path=' + path;

        // add path parameter if requested and needed
        if(params && (cycles == "True")) {
            paramstring = paramstring + '&cycles=True';
        }
    }
    
    return paramstring
}

// New view of the same selection, but with new parameters
function refreshParams() {
    // If paths are refreshed, getParams need to know originally
    // (ie. in the URL,not interactively) selected nodes to function
    // correctly
    if(path == 'all' || path == 'short') {
        selected = origSelected;
    }

    var params = getParams(1);

    // Grab old parameters out of the URL, add new ones
    browserEval('window.location = window.location.href.split("&")[0]  + "' + params + '"');

}

// New view of a new selection with some or none parameters
function newView(params, desiredPath) {
    if(selected != '') {
        path = desiredPath;
        var paramstring = getParams(params);

        browserEval('window.location = "print2.cgi?proto=' + 
                     selected + paramstring + '"');
    }
}
    ]]></script>
"""

# TODO
# - nicer structure
# - options for using other visualisers (neato, fdp, twopi, circo)
# - Maybe workaround IE like this:
#   http://www.lsc.ufsc.br/~luizd/base64-to-mhtml/workaround.html 

def sanitise_dict(dict):
    safechars = re.compile('[^a-zA-Z0-9,-]')
    # leaves only desired values, Warning: inplace modification!
    for key in dict.keys():
        newitems = []
        olditems = dict[key]
        dict[key] = newitems
        for item in olditems:
            val_item = safechars.sub('', item)
            newitems.append(val_item)
        val_key = safechars.sub('', key)
        if val_key != key:
            dict[val_key] = dict[key]
            del dict[key]

def grab_cmdline_from_cgi():
    cmdline = ""

    rawcgi = cgi.parse()
    sanitise_dict(rawcgi)
    url = urllib.urlencode(rawcgi, 'doseq')
    url = re.sub('(%2c)|(%2C)', ',', url)

    if len(url) > 0:
        for i in url.split('&'):
            cmdline += '--' + i + ' '

    return cmdline

#print "Content-type: text/plain\n\n"
#print grab_cmdline_from_cgi()
#form = cgi.FieldStorage()
#sys.exit(1)

cmdline = grab_cmdline_from_cgi()

r = os.popen("./drawdot.cgi " + cmdline)
dot = r.read()
stat = r.close()

if stat:
    print "Content-type: text/plain\n\n" + dot
    sys.exit(2)

w,r = os.popen2("dot -T svg")
w.write(dot)
w.close()
img = r.read()
r.close()

# Amazing error handling
if not img:
    print "Content-Type: text/plain\n\nError forming graph\n";
    sys.exit(2)

#img = re.sub(r'width=".+" height=".+"\s+viewBox = ".+"', r'onmousedown="mouseDown(evt)" onmouseup="mouseUp(evt)"', img)

img = re.sub(r'<svg ', r'<svg onmousedown="mouseDown(evt)" onmouseup="mouseUp(evt)" onload="init()" ', img)

img = re.sub(r'xlink:href', r'onclick="selectNode(evt)" xlink:label', img)

img = re.sub(r'(<g id="graph)', script + r'\n\1', img, 1)

page = "Content-Type: image/svg+xml\n\n" + img

print page
