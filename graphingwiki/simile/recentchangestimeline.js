function mydoit() {
  alert('Yes, it works!');
}

function onLoad() {
  var eventSource = new Timeline.DefaultEventSource();

  var focusobj = document.getElementById("recentchangestimelinefocus");

  if (focusobj)
    var focusval = focusobj.value;
  else
    var focusval = "";

  if (focusval == "")
    focusval = "Jan 1 1999 00:00:00 GMT";

  var sourceobj = document.getElementById("recentchangestimelinesource");

  if (sourceobj)
    var sourceval = sourceobj.value;
  else
    var sourceval = "";

  var bandInfos = [
    Timeline.createBandInfo({
        eventSource:    eventSource,
        date:           focusval,
        width:          "50%", 
        intervalUnit:   Timeline.DateTime.DAY, 
        intervalPixels: 100
    }),
    Timeline.createBandInfo({
        showEventText:  false,
        trackHeight:    0.5,
        trackGap:       0.2,
        eventSource:    eventSource,
        date:           focusval,
        width:          "25%", 
        intervalUnit:   Timeline.DateTime.WEEK, 
        intervalPixels: 200
    }),
    Timeline.createBandInfo({
        showEventText:  false,
        trackHeight:    0.5,
        trackGap:       0.2,
        eventSource:    eventSource,
        date:           focusval,
        width:          "25%", 
        intervalUnit:   Timeline.DateTime.MONTH, 
        intervalPixels: 300
    })
  ];
  bandInfos[1].syncWith = 0;
  bandInfos[1].highlight = true;
  bandInfos[2].syncWith = 0;
  bandInfos[2].highlight = true;
  
  tl = Timeline.create(document.getElementById("recentchangestimeline"), bandInfos);

  if (sourceval == "")
    alert("No timeline source input given!");
  else
    Timeline.loadXML(sourceval, function(xml, url) { eventSource.loadXML(xml, url); });
}

var resizeTimerID = null;

function onResize() {
    if (resizeTimerID == null) {
        resizeTimerID = window.setTimeout(function() {
            resizeTimerID = null;
            tl.layout();
        }, 500);
    }
}

window.onload = onLoad;
window.resize = onResize;
