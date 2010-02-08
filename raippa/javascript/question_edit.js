/**
 * A MooTools class for creating question editor for raippa. 
 * Dependencies: mootools core and raippa-common.
 */
var QuestionEditor = new Class({
    Implements: [Options],
    Binds: ['submitCheck', 'changeType', 'addAnswer', 'addFileAnswer', 'clearRms'],
    options: {
        preventDoubleSubmit: true,
        type: 'checkbox',
        redo: false,
        answers: [],
		fileAddStyles : {
			'border': '1px solid gray',
			'padding': '0.8em',
			'margin-top' : '2px' 
		}
    },
    type: 'checkbox',
    saved: false,
    ansrows: [],
    filerows: [],
    initialize: function(el, options){
    
        if (!el) 
            return false;
        this.container = $(el);
        this.container.setStyles(this.options.containerStyles);
        
        this.setOptions(options);
        
        this.form = new Element('form', {
            'id': 'editForm',
			'enctype': 'multipart/form-data',
            'method': 'post'
        });
        
        var row = new Element('tr', {
            'id': 'optionrow'
        });
        this.table = new Element('table', {
            'id': 'editoTable'
        });
        this.anstable = new Element('tbody', {
            'id': 'ansTable'
        }).grab(row);
        ;
        
        this.filetable = new Element('tbody', {
            'id': 'fileTable'
        });
        
        var rm = new Element('td').grab(new Element('a', {
            'class': 'jslink',
            'title': 'Remove selected answers',
            'text': 'X',
            'styles': {
                'color': 'red'
            },
            'events': {
                'click': function(){
                    this.container.getElements('input.rmcheck').each(function(el){
                        if (el.get('checked') == true) {
                            $('row' + el.get('value')).destroy();
                        }
                    });
                }.bindWithEvent(this)
            }
        }));
        
        this.typesel = new Element('select', {
            'id': 'typeselect',
            'name': 'answertype',
            'events': {
                'change': function(){
                    this.changeType(this.typesel.get('value'));
                }.bindWithEvent(this)
            }
        });
        this.options.types.each(function(value){
            this.typesel.grab(new Element('option', {
                'value': value,
                'text': value
            }));
        }, this);
        
        var type = new Element('td').appendText("Answer type: ").grab(this.typesel);
        
        var newans = new Element('td').grab(new Element('input', {
            'type': 'button',
            'value': 'new answer',
            'events': {
                'click': function(){
                    if (this.type != "file") {
                        this.addAnswer();
                    }
                    else {
                        this.addFileAnswer();
                    }
                    this.showFields('last');
                    
                }.bindWithEvent(this)
            }
        }));
        var redo = new Element('td').adopt(new Element('input', {
            'type': 'checkbox',
            'id': 'redochk',
            'name': 'redo',
            'value': 'True',
            'checked': this.options.redo
        }), new Element('label', {
            'for': 'redochk',
            'text': 'Allow redoing question.'
        }), new Element('p',{
			'id': 'shuffleTd',
			}).adopt(new Element('input',{
			'type': 'checkbox',
			'id' : 'shufflechk',
			'name' : 'shuffle',
			'value' : 'True',
			'checked' : this.options.shuffle
		}),new Element('label', {
			'for': 'shufflechk',
			'text': 'Shuffle order.'
		})));
        row.adopt(rm, type, redo, newans)
        
        this.table.adopt(new Element('tbody').grab(row), this.anstable, this.filetable);
        this.form.grab(this.table);
        
        this.container.grab(this.form);
        
        var submit = new Element('input', {
            'type': 'submit',
            'value': 'Save',
            'events': {
                'click': function(){
                    return this.submitCheck();
                }.bindWithEvent(this)
            }
        });
        var cancel = new Element('input', {
            'type': 'button',
            'value': 'Cancel',
            'events': {
                'click': function(){
                    window.location.reload();
                }
            }
        });
        
        this.form.adopt(submit, cancel);
        //restore old answers
        this.options.answers.each(function(ans){
            if (this.options.type != "file") {
                this.addAnswer(ans.name, ans.value, ans.tip, ans.comment, ans.page, ans.options);
            }
            else {
                this.addFileAnswer(ans.name, ans.cmd, ans.input, ans.output, ans.infiles, ans.outfiles);
            }
        }, this);
        
        this.addAnswer();
        this.addFileAnswer();
        
        this.changeType(this.options.type);
        this.showFields('last');
        
    },
    
    /* Shows tip and comment fields in given row or n:th answer in current view*/
    showFields: function(index){
        var rows = ["file"].contains(this.typesel.get('value')) ? this.filerows : this.ansrows;
        if (index == 'last') 
            index = rows.length - 1;
        var elm = ($type(index) == 'element') ? index : rows[index] || false;
        if (elm) {
            
			$$($$(rows).getElements('tr.answerinfo')).addClass('hidden');
            elm.getElements('tr.hidden').removeClass('hidden');

			/*
			$$($$(rows).getElements('tr.answerinfo')).dissolve({'display': 'table-row'});
			elm.getElements('tr.answerinfo').reveal({'display': 'table-row'});
            */
        }
    },
    clearRms: function(){
        this.container.getElements('input.rmcheck').each(function(el){
            el.set('checked', '');
        });
    },
    
    addAnswer: function(ans, val, tip, comment, page, options){
		
		options = options || [];
    
        var tbody = this.anstable;
        var num = this.ansrows.length > 0 ? this.ansrows.getLast().retrieve('row') + 1 : 0;
        var row = new Element('tr', {
            'id': 'row' + num,
            'class': 'no_border'
        });
        row.store('row', num);
        
        row.grab(new Element('td').grab(new Element('input', {
            'type': 'checkbox',
            'class': 'rmcheck',
            'value': num,
            'name': 'rm' + num
        })));
        var tab = new Element('table', {
            'class': 'no_border'
        });
        var tabTbody = new Element('tbody');
        tab.grab(tabTbody);
        
        var ansRow = new Element('tr'), valRow = new Element('tr'), tipRow = new Element('tr', {
            'id': 'tiprow' + num,
            'class': 'answerinfo hidden'
        }), comRow = new Element('tr', {
            'id': 'comrow' + num,
            'class': 'answerinfo hidden'
        });
        
        var ansTd = new Element('td', {
            'rowspan': '2'
        }).grab(new Element('textarea', {
            'cols': 60,
            'text': ans,
            'name': 'answer' + num,
            'rows': 2,
            'events': {
                'focus': function(){
                    this.showFields(row);
                }.bindWithEvent(this)
            }
        }));
        var rightChk = !val || val == "right" ? true : false;
        var wrongChk = rightChk ? false : true;
        var valTd1 = new Element('td').adopt(new Element('input', {
            'type': 'radio',
            'name': 'value' + num,
            'value': 'right',
            'id': 'right' + num,
            'checked': rightChk
        }), new Element('label', {
            'for': 'right' + num,
            'text': 'right'
        }));
        var valTd2 = new Element('td').adopt(new Element('input', {
            'type': 'radio',
            'name': 'value' + num,
            'value': 'wrong',
            'id': 'wrong' + num,
            'checked': wrongChk
        }), new Element('label', {
            'for': 'wrong' + num,
            'text': 'wrong'
        }));
        
        ansRow.adopt(new Element('th', {
            'rowspan': '2',
            'text': 'Answer:'
        }), ansTd, valTd1);
        
        valRow.grab(valTd2);
	
		var reSpan = new Element('span',{ 
			'class': this.type == "text" ? 'regexp_span': "regexp_span hidden"
		}),latSpan = new Element('span',{
			'class': this.type != "text" ? 'latex_span': 'latex_span hidden'
		});
		
		reSpan.adopt(new Element('input',{
			'type': 'checkbox',
			'name': 'option' +num,
			'id' : 'regexp' + num,
			'value': 'regexp',
			'checked' : options.contains("regexp") ? true: false
		}),new Element('label',{
			'for':'regexp'+num,
			'text': 'Regexp'
		}));
		latSpan.adopt(new Element('input',{
			'type': 'checkbox',
			'name': 'option' +num,
			'id' : 'latex' + num,
			'value': 'latex',
			'checked' : options.contains("latex") ? true: false
		}),new Element('label',{
			'for':'latex'+num,
			'text': 'Latex'
		}));   

		ansRow.grab(new Element('td').adopt(reSpan, latSpan));
        
        tipRow.adopt(new Element('th', {
            'text': 'Tip:'
        }), new Element('td').grab(new Element('textarea', {
            'name': 'tip' + num,
            'text': tip,
            'cols': 60,
            'rows': 2
        })));
        
        comRow.adopt(new Element('th', {
            'text': 'Comment:'
        }), new Element('td').grab(new Element('textarea', {
            'name': 'comment' + num,
            'text': comment,
            'cols': 60,
            'rows': 2
        })));
        
        tabTbody.adopt(ansRow, valRow, tipRow, comRow);
        
        row.grab(new Element('td', {
            'colspan': 3
        }).grab(new Element('div').grab(tab)));
        
        if (page) {
            row.grab(new Element('input', {
                'type': 'hidden',
                'name': 'page' + num,
                'value': page
            }));
        }
        
        this.ansrows.push(row);
        tbody.grab(row);
        
    },
    
    addFileAnswer: function(name, cmd, input, output, infiles, outfiles){
		input = input || "";
		output = output || "";
		
        infiles = infiles || [];//["file1", "file2"];
        outfiles = outfiles || [];//["file3", "file4"];
        var tbody = this.filetable;
        
        var num = this.filerows.length > 0 ? this.filerows.getLast().retrieve('row') + 1 : 0;
        
        var row = new Element('tr', {
            'id': 'row' + num
        });
        row.store('row', num);
        
        var rm = new Element('td').grab(new Element('input', {
            'type': 'checkbox',
            'class': 'rmcheck',
            'value': num,
            'name': 'rm' + num
        }));
        
        var table = new Element('table', {
            'class': 'no_border'
        }), tab = new Element('tbody').inject(table), nameTr = new Element('tr'), cmdTr = new Element('tr').addClass('answerinfo'), inputTr = new Element('tr').addClass('answerinfo'), outputTr = new Element('tr').addClass('answerinfo'), infileTr = new Element('tr').addClass('answerinfo'), outfileTr = new Element('tr').addClass('answerinfo');
        
        nameTr.adopt(new Element('th').appendText('Test name: '), new Element('td').grab(new Element('textarea', {
            'name': 'name' + num,
            'text': name,
            'cols': 60,
            'rows': 1,
            'events': {
                'focus': function(){
                    this.showFields(row);
                }.bindWithEvent(this)
            }
        })));
        
        cmdTr.adopt(new Element('th').appendText('Run params: '), new Element('td').grab(new Element('textarea', {
            'name': 'cmd' + num,
            'text': cmd,
            'cols': 60,
            'rows': 1
        })));
        
        inputTr.adopt(new Element('th').appendText('Input: '), new Element('td').grab(new Element('textarea', {
            'name': 'input' + num,
            'text': input,
            'cols': 60,
            'rows': 5
        })));
        outputTr.adopt(new Element('th').appendText('Output: '), new Element('td').grab(new Element('textarea', {
            'name': 'output' + num,
            'text': output,
            'cols': 60,
            'rows': 5
        })));
        
        var infileTd = new Element('td'), outfileTd = new Element('td');
		
		var infileDiv = new Element('div').setStyles(this.options.fileAddStyles).inject(infileTd),
		 	outfileDiv = new Element('div').setStyles(this.options.fileAddStyles).inject(outfileTd);
        
        var rmlink = new Element('a', {
            'class': 'jslink',
            'html': '&#10006;',
            'styles': {
                'color': 'red'
            }
        });
        infiles.each(function(file, index){
            var span = new Element('span').setStyle('display', 'block');
            
            var field = new Element('input', {
                'name': 'old_infiles' + num,
                'readonly': 'true',
                'value': file
            });
            var rm = rmlink.clone().addEvent('click', function(){
                span.destroy();
            });
            
            span.adopt(rm, field);
            infileDiv.adopt(span);
        });
        
        outfiles.each(function(file, index){
            var span = new Element('span').setStyle('display', 'block');
            
            var field = new Element('input', {
                'name': 'old_outfiles' + num,
                'readonly': 'true',
                'value': file
            });
            var rm = rmlink.clone().addEvent('click', function(){
                span.destroy();
            });
            
            span.adopt(rm, field);
            outfileDiv.adopt(span);
        });
        var addFileField = function(basename, where){
            var span = new Element('span').setStyle('display', 'block');
            var currentfields = $$('input[name^=' + basename + ']');
            var index = 0;
            if (currentfields.length > 0) {
                index = currentfields.getLast().retrieve('index') +1;
            }
                     
            var field = new Element('input', {
                'type': 'file',
                'name': basename + '_' + index
            }).addEvent('change', function(){
                addFileField(basename, where);
                this.removeEvents('change');
            });
			
            var rm = rmlink.clone().addEvent('click', function(){
				/* Calling change event before destroying file input so that we are
				 * not going to run out of fields.
				 */
                field.fireEvent('change');
                span.destroy();

            });
            
			field.store('index', index);
            where.grab(span.adopt(rm, field));
        };
        
        addFileField("infile" + num, infileDiv);
        addFileField("outfile" + num, outfileDiv);
        
        infileTr.adopt(new Element('th').appendText('Infiles: '), infileTd);
        
        outfileTr.adopt(new Element('th').appendText('Outfiles: '), outfileTd);
        tab.adopt(nameTr, cmdTr, inputTr, outputTr, infileTr, outfileTr);
        
        row.adopt(rm, new Element('td', {
            'colspan': 3
        }).grab(table));
        this.filerows.push(row);
        tbody.grab(row);
    },
    changeType: function(newtype){
        if (newtype != this.typesel.get('value')) {
            this.typesel.set('value', newtype);
        }
        this.type = newtype;
        var filerows = $$(this.filerows);
        var ansrows = $$(this.ansrows);
        this.clearRms();
		
		var shuffle = $('shuffleTd')
        
        if (newtype == "file") {
            filerows.removeClass('hidden');
            ansrows.addClass('hidden');
			shuffle.addClass('hidden');
        }
        else {
            filerows.addClass('hidden');
            ansrows.removeClass('hidden');
            if (newtype == "text") {
				shuffle.addClass('hidden');
                $$(ansrows.getElements('span.regexp_span')).removeClass('hidden');
                $$(ansrows.getElements('span.latex_span')).addClass('hidden');

            }
            else {
				shuffle.removeClass('hidden');
                $$(ansrows.getElements('span.regexp_span')).addClass('hidden');
                $$(ansrows.getElements('span.latex_span')).removeClass('hidden');

            }
            
        }
    },
    
    submitCheck: function(){
    
        var form = this.form;
        var type = this.typesel.get('value');
        if (type != 'file') {
            var ans = this.anstable.getElements('textarea[name^=answer]');
            hasAnswer = ans.some(function(a){
                if (!a.get('name') || a.getParent('tr').hasClass('hidden')) {
                    return false;
                }
                var name = a.get('name');
                var value = $(name.replace(/answer/, 'right')).checked;
                var pass = a.value.length > 0 && value;
                return pass == true;
            });
            if (!hasAnswer) {
                var msg = "There is no right answer! Do you still want to save the question?";
                return confirm(msg);
            }
			if (this.type == "text"){
				$$('span.latex_span').destroy();
			}else{
				$$('span.regexp_span').destroy();
			}
			$$(this.filetable).destroy();
        }else{
			var ans = this.filetable.getElements('textarea[name^=name]');
			var hasName = ans.every(function(txt){
				//has name
				if (txt.get('value') != "") return true;
				
				//it's ok to not have a name if all the fields are empty
				var i = txt.get('name').replace('name','');
				var vals = this.filetable.getElements('textarea[name$='+i+'], input[name^=infile'+i+'], input[nam^=outfile'+i+']')
							.get('value').erase("");
				return vals.length == 0;
			}, this);
			
			if (!hasName){
				alert('Name field is required for every test!');
				return false;
			}
			
            $$(this.anstab).destroy();
        }
        //trying to prevent double saves
        if (this.saved && this.options.preventDoubleSubmit) {
            return false;
        }
        
        this.form.grab(new Element('input', {
            'type': 'hidden',
            'value': 'editQuestion',
            'name': 'action'
        }));
        this.saved = true;
        return true;
    }
    
});
