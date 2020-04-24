/* JavaScript for index page */

var selected_function_id;
var selected_http_request_id;
var selected_function_call_id;

var truth_map = {1 : "No Violation", 0 : "Violation"};
var code_highlight_palette = ["#cae2dc", "#eee3cd", "#cad7f2", "#ded4e7", "#e3e3e3", "d6eff0"];

var process_subtree_accordion = function(path, subtree, dom_element) {
	// given a subtree, build the accordion.

	var padding = String(path.length * 2) + "px";
	if(Array.isArray(subtree)) {
		var html_string = ""
		for(var i=0; i<subtree.length; i++) {
			str = subtree[i][2];
			str = decodeHTML(str);

			html_string += ('<button type="button" class="list-group-item" function-id="' + subtree[i][0] +
				'" style="padding-left:' + padding + '">' + str + '</button>');
		}
		$(dom_element).html(html_string);
	} else {
		var keys = [];
		for (var key in subtree) {
			keys.push(key);
		}
		console.log("path="+path+"; keys="+ keys);

		for(var i=0; i<keys.length; i++) {
			var key = keys[i];
			// create list inside the current list in the dom
			var new_path = (path != "") ? (path + "-" + key) : key;
			if (path != ""){
				$(dom_element).append('<div class="panel panel-default" style="inherit">' +
			  	'<div class="panel-heading">' +
			    	'<h3 class="panel-title" id="external-' + new_path + '" style="padding-left: ' + padding + '">' + key + '</h3>' +
			  	'</div>' +
			  	'<div class="panel-body">' +
			    	'<div class="list-group" id="' + new_path + '">' +
					'</div>' +
			  	'</div>' +
					'</div>')
			//$(dom_element).append('<p>' + key + '</p><ul id="' + new_path + '"></ul>');
			}
			process_subtree_accordion(new_path, subtree[key], $("#" + new_path));
		}
	}
}

var build_accordion = function() {
	// get the data from the "#function-list-data" element, and
	// recursively construct an accordion.
	// the machine part of the path is shown as a tab

	var function_list_data = JSON.parse($("#function-list-data").html());
	var dom_elem = $("#function-list");
	var content = '<div class="tab">';

	// if we don't want the first tab to be open on the page load, set to 0
	var is_first = 1;

	//construct the tabs with machine names as buttons
	for(var key in function_list_data){
		key = String(key);
		if (is_first){
			content += ('<button id="default-open" class="tablinks">'+ key + '</button>');
		}
		else{
			content += ('<button class="tablinks">'+ key + '</button>');
		}
	}

	content += '</div>';

	$(dom_elem).append(content);

	//for each machine, build an accordion with the corresponding functions - from tree[key]
	for(var key in function_list_data){
		key = String(key);
		$(dom_elem).append('<div id="tab-' + key + '" class="tabcontent"> </div>');
		dom_elem2 = $("#tab-"+key);
		process_subtree_accordion(key, function_list_data[key], $(dom_elem2));
	}

	//add onclick event to the buttons
	var tablinks = document.getElementsByClassName("tablinks");
	for (i = 0; i < tablinks.length; i++) {
		console.log(tablinks[i]);
		tablinks[i].onclick = function(){show_functions(event,"tab-"+this.innerHTML);};
	}

	// if we want no functions to be shown on page load, just the tab buttons
		//uncomment following line and erase the one below it
	//show_functions("onclick", "")
	document.getElementById("default-open").click();

	apply_accordion_clicks();
}

var string_to_html = function(str){
	str = str.split('&lt;').join('<');
	str = str.split('&gt;').join('>');
	str = str.split('&amp;').join('&');
	return str
}

var decodeHTML = function (html) {
	var txt = document.createElement('textarea');
	txt.innerHTML = html;
	return txt.value;
}

var show_functions = function(evt, key){
	//upon clicking on a button with id 'tab-machine_name', hide all functions
	//by setting the tabcontent element display to none
	//then, append 'active' to the id of the selected button
	//and make its tabcontent element visible

	console.log(key)
	var i, tabcontent, tablinks;
	tabcontent = document.getElementsByClassName("tabcontent");
	for (i = 0; i < tabcontent.length; i++) {
		tabcontent[i].setAttribute('style', 'display: none');
		console.log(tabcontent[i])
	}
	tablinks = document.getElementsByClassName("tablinks");
	for (i = 0; i < tablinks.length; i++) {
		tablinks[i].className = tablinks[i].className.replace(" active", "");
	}
	if (key != "") {
		document.getElementById(key).setAttribute('style', 'display = "block"');
		evt.currentTarget.className += " active";
	}

}

var apply_accordion_clicks = function() {
	$("#function-list").find(".panel-heading").click(function(e) {
		if(String($(e.target).attr("id")).indexOf("external-") == 0) {
			// get the name of the dom element to toggle
			var id_of_toggle_element = $(e.target).attr("id").replace("external-", "");
			$("#" + id_of_toggle_element).slideToggle();
		}
	});
}

var apply_title_click = function() {
	$("#function-title").click(function() {
		$("#function-list").slideToggle();
	});

	$("#function-call-title").click(function() {
		$("#function-call-list").slideToggle();
	});
}

var apply_function_list_click = function() {
	$("#function-list").find(".list-group-item").click(function(e) {
		$("#function-list").slideUp();
		$("#function-call-list").html("<p>Loading function calls.  This can take some time if there are many.</p>");
		$("#function-call-list").slideDown();
		var function_id = $(e.target).closest(".list-group-item").attr("function-id");
		selected_function_id = function_id;
		var specification_code = $(e.target).closest(".list-group-item").html();
		$.get("/list_function_calls/" + function_id, function(data) {
		    // load the list of function calls
			$("#function-call-list").html("");
			data = data["data"];
			for(var i=0; i<data.length; i++) {
				var button = document.createElement("button");
				button.className = "list-group-item";
				button.innerHTML = "<input type='checkbox' function-call-id='" + data[i][0]  + "'/><b>Start:</b> " +
				    data[i][2] + ", <b>lasting:</b> " + data[i][6] + " seconds";
				$(button).attr("function-call-id", data[i][0]);
				$("#function-call-list").append(button);
			}
			apply_function_call_list_click();
			// now load the function/property information in and put it on the page
			$.get("/get_source_code/" + function_id, function(code_data) {
			    // here we will process the source code + property information and display on the page
			    $("#verdict-list").html("<div id='specification_listing'>" + specification_code +
			        "</div><div class='code_listing'></div>");
					var code_data = JSON.parse(code_data);
					var code_lines = code_data["code"];
					var current_line = code_data["start_line"];

					// we also want to display binding reference at the end of each line
					// first, go through bindings and collect all line numbers they refer to
					var bindings_list = code_data["bindings"];
					var line_numbers = [];
					for (var i=0; i<bindings_list.length; i++){
						binding = bindings_list[i];
						line_numbers = line_numbers.concat(binding["binding_statement_lines"]);
					}

					// add each line as a div element, if it is in the list of binding statement lines,
					// also add a span element to the content of the line - later, we will add binding labels to it
					for(var i=0; i < code_lines.length; i++) {
						var line_div = document.createElement("div");
						var content = "<b>" + current_line + "</b> " + code_lines[i].replace(/\t/g, "&nbsp;&nbsp;&nbsp;").replace(/^[ \t]+/mg, html_space_replace);
						line_div.className = "code_listing_line";
						line_div.id = "line-number-" + current_line;

						//if (line_numbers.indexOf(current_line)!=-1)
						content += '<span class="span-binding" id="span-bindings-line-' + current_line + '"> </span>';
						content += '<p class="empty-line" id="empty-line-' + current_line + '"> ... <br> </p>';

						line_div.innerHTML = content;
						current_line++;
						$("#verdict-list").append(line_div);
					}

					// we want to highlight the quantification in the specification code
					// with the same color as the line of code it refers to
					// quantifier lines have ids stating the bind variable name
					// other lines in the specification don't have ids
					var quantification_ids = [];
					var spec = $("#specification_listing").children();
					for (i=0; i<spec.length; i++){
						if (spec[i].id!=""){
							quantification_ids.push(spec[i].id);
						}
					}

					// finally, for each binding, add that binding label
					// to the span elements of lines they refer to
					// then for each binding line go through the specification to find the quantification
					// that refers to that line and highlight it the same color as the line in the code
					for (var i=0; i<bindings_list.length; i++){
						var binding = bindings_list[i];
						var line_numbers = binding["binding_statement_lines"];

						for (var j=0; j<line_numbers.length; j++){
							var no = line_numbers[j]
							var color = code_highlight_palette[j];
							$("#line-number-"+no).attr('style',"background-color : " + color);
							$("#line-number-"+no).attr('save-background-color',color);
							//$("#span-bindings-line-"+no).append(" "+binding["id"]);
							for (k=0; k<spec.length; k++){
								var obj = spec[k];
								if (obj.id==quantification_ids[j]){
									$(obj).attr('style',"background-color : " + color);
								}
							}
						}
					}

			});
		});
	});
};

var html_space_replace = function(){
	var leadingSpaces = arguments[0].length;
  var str = '';
  while(leadingSpaces > 0) {
    str += '&nbsp;';
    leadingSpaces--;
  }
  return str;
}

var apply_function_call_list_click = function() {
	$("#function-call-list").children(".list-group-item").click(function(e) {
		$("#function-list").slideUp();
		$("#http-request-list").slideUp();
		$("#function-call-list").slideDown();
		var function_call_id = $(e.target).closest(".list-group-item").attr("function-call-id");
		selected_function_call_id = function_call_id;
		//$("#verdict-list").html("");
		// toggle the checkbox for the box that was clicked
		$(e.target).children("input[type=checkbox]").prop("checked",
		    !$(e.target).children("input[type=checkbox]").prop("checked"));
		// get all the checked boxes and, from there, get a list of function call IDs
		var function_call_ids = $(e.target).parent().parent().find("input:checked").map(function(i, d) {
		    return $(d).attr("function-call-id");
		}).get();
		console.log(function_call_ids)
		// send a request to the server with the function call IDs that have been selected
		$.post("/get_function_calls_data/", {"ids" : function_call_ids}).done(function(data) {
		    // here we will process the information from the function calls and
		    // put it on the page with with the source code and property information
				console.log(data);
				tree = JSON.parse(data);

				code_lines = document.getElementsByClassName("code_listing_line");
				var start_line = parseInt(code_lines[0].id.split("-").slice(-1));
				var show_lines = [];

				// clean up the bindings present before selection
				for (var i=0; i<code_lines.length; i++){
					var line_id = code_lines[i].id.split("-");
					var id_line_number = line_id[line_id.length-1];
					$("#span-bindings-line-"+id_line_number).html("");
					$("#line-number-"+id_line_number).attr('style',"background-color : transparent");
				}

				// clean up binding labels from previous calls selection
				remove_bindings = $('[binding="yes"]');
				for (var i=0; i<remove_bindings.length; i++){
					$(remove_bindings[i]).attr('binding', "");
				}
				// clean up subatom links from previous calls selection
				remove_subatoms = $(".subatom-clickable");
				if (typeof(remove_subatoms) != 'string'){
				for (var i=0; i<remove_subatoms.length; i++){
					$(remove_subatoms[i]).attr("onclick", "");
					$(remove_subatoms[i]).attr('class', "subatom");
				}}
				$($(".subatom-clickable-active")[0]).attr("onclick","");
				$($(".subatom-clickable-active")[0]).attr("class", "subatom");

				// clean up the existing dropdowns
		 	 remove_dropdowns = $(".code_listing_line-clickable");
		 	 console.log(remove_dropdowns.length)
		 	 for (var i=0; i<remove_dropdowns.length; i++){
		 		 $(remove_dropdowns[i]).attr('class', "code_listing_line");
		 	 }

				// add span elements which indicate the binding at inst points:
				// for each binding, collect the relevant line numbers from the leaves
				// add the binding id to the html of the span element
				for (binding in tree){
					var line_numbers = [];
					var lines_points = [];
					for (atom in tree[binding]){
						for (subatom in tree[binding][atom]){
							list = tree[binding][atom][subatom];
							for (var i=0; i<list.length; i++){
								if (line_numbers.indexOf(list[i]["code_line"])==-1){
									line_numbers.push(list[i]["code_line"]);
								}
								if (atom=="-1" && lines_points.indexOf(list[i]["code_line"])==-1){
									lines_points.push(list[i]["code_line"]);
								}

							}
						}
					}
					console.log(line_numbers)
					console.log(lines_points)
					for (var i=0; i<line_numbers.length; i++){
						var no = line_numbers[i];
						$("#line-number-"+no).attr('binding',"yes");
						$("#line-number-"+no).attr('style',"background-color : #ebf2ee");
						color = $("#line-number-"+no).attr('save-background-color');
						if (!(color)){
							// todo: pair colours of lines generated by a part of a specification for lines not saved in binding_statement_lines
							$("#line-number-"+no).attr('save-background-color', "#def1fc");
						}
					}
					for (var i=0; i<lines_points.length; i++){
						var no = lines_points[i];
						var tree_string=JSON.stringify(tree[binding]);
						console.log(tree_string)
						$("#span-bindings-line-"+no).append('<button class="binding-button" binding-button=' +
							binding + '>' + binding + '</button>');
						var bind_buttons = $('[binding-button='+binding+']');
						for (var j=0; j<bind_buttons.length; j++){
							//bind_buttons[j].onclick=function(){highlight_lines(line_numbers,tree_string)}
							$(bind_buttons[j]).attr('tree',tree_string);
							$(bind_buttons[j]).attr('onClick','highlight_lines(['+line_numbers+'],this)');
						}
					}
					// show_lines stores all relevant line_numbers - we will hide the rest
					show_lines = show_lines.concat(line_numbers);
				}

				show_lines = show_lines.sort();

				//in addition to the lines stored in leaves, we want to display the first line
				// and in this case, three lines around each instrumentation point
				var more_lines = [start_line];
				for (var i=0; i<show_lines.length; i++){
					var current_line_number = show_lines[i];
					for (var j=1; j<3; j++){
						more_lines.push(current_line_number+j);
						more_lines.push(current_line_number-j)
					}
				}
				show_lines = show_lines.concat(more_lines);

				for (var i=0; i<code_lines.length; i++){
					var line_id = code_lines[i].id.split("-");
					var id_line_number = line_id[line_id.length-1];
					if (show_lines.indexOf(parseInt(id_line_number))==-1){
						$("#line-number-"+id_line_number).hide();
					}
					else{
						$("#line-number-"+id_line_number).show();
					}
				}

				// insert a spacing where there is a jump in line numbers
				show_lines = show_lines.sort(function(a, b){return a - b});

				for (var i=0; i<show_lines.length; i++){
					if (show_lines[i] < (show_lines[i+1] - 1)){
						$("#empty-line-"+show_lines[i]).show();
					}
				}

		});
	});
};

var highlight_lines = function(list, obj = undefined){
	/* obj is an optional argument and differs the calls to this function
	 made by clicking a binding (parses the binding button element as obj)
	 from the calls made by clicking on a subatom (parses only the list of line numbers) */

	 // first, remove highlighting from any previously highlighted lines
	var unhighlight = $('[binding="yes"]');
	for (var i=0; i<unhighlight.length; i++){
		$(unhighlight[i]).attr('style',"background-color : #ebf2ee");
	}

	// highlight the lines whose number is in the given list
	// background colour is saved as an attribute to be corresponding to the
	// color of the part of the specification which generated the instrumentation point
	for (var i=0; i<list.length; i++){
		var no = list[i];
		var color = $("#line-number-"+no).attr('save-background-color');
		$("#line-number-"+no).attr('style',"background-color : " + color);
	}

	// end the function here if it was called by a subatom
	if (typeof(obj)=='undefined') return;

	// clean up the existing dropdowns
	remove_dropdowns = $(".code_listing_line-clickable");
	console.log(remove_dropdowns.length)
	for (var i=0; i<remove_dropdowns.length; i++){
		$(remove_dropdowns[i]).attr('class', "code_listing_line");
	}

	// emphasise the selected binding id by bolding the labels with the same id
	var bind_buttons = $(".binding-button");
	var binding_id = $(obj).attr('binding-button');
	for (var i=0; i<bind_buttons.length; i++){
		if ($(bind_buttons[i]).attr('binding-button') == binding_id){
			$(bind_buttons[i]).attr('style',"font-weight: bold");
		}
		else{
			$(bind_buttons[i]).attr('style',"font-weight: normal");
		}
	}

	// iterate through the atoms observed by the selected binding
	// make the subatoms clickable
	var tree_string = $(obj).attr('tree');
	var tree = JSON.parse(tree_string);

	for (atom in tree){
		var subtree = tree[atom];
		var subs = $($("#specification_listing").find('span.atom[atom-index="' + atom + '"]')[0]).children();
		for (var i=0; i<subs.length; i++){
			$(subs[i]).attr('class', "subatom-clickable");
			$(subs[i]).attr('subtree', JSON.stringify(subtree));
			$(subs[i]).attr('onclick', 'subatom_click(this)');
		}
	}

}

var subatom_click = function(obj){
	$(".subatom-clickable-active").attr('class', "subatom-clickable");
	$(obj).attr('class', "subatom-clickable-active");
	var sub_index = $(obj).attr('subatom-index');
	var subtree = JSON.parse($(obj).attr('subtree'));
	var inst_points_list = subtree[sub_index];

	var lines_list = [];
	for (var i=0; i<inst_points_list.length; i++){
		var no = inst_points_list[i]["code_line"];
		//$("#line-number-"+no).attr('save-background-color',color);
		lines_list.push(no);
	}
	highlight_lines(lines_list);
	make_lines_clickable(lines_list, subtree, $(obj).parent());
}

var make_lines_clickable = function(lines_list, subtree, obj){
	/* lines_list contain line numbers of inst points at which observations
	 were generated by the chosen subatom - this subatom, but also other subatoms
	 which belong to the same atom are stored as keys in the subtree
	 the atom is given as obj but we only really need its index*/

	 // clean up the existing dropdowns
	 remove_dropdowns = $(".code_listing_line-clickable");
	 console.log(remove_dropdowns.length)
	 for (var i=0; i<remove_dropdowns.length; i++){
		 $(remove_dropdowns[i]).attr('class', "code_listing_line");
	 }

	// send the parameters to the server in order to determine the type of the atom and proceed accordingly
	var atom_index = $(obj).attr('atom-index');
	var inst_point_id = subtree["0"][0]["id"];
	var dropdown_content;
	$.get("/get_atom_type/"+atom_index+"/"+inst_point_id+"/", function(atom_type) {
		console.log(atom_type)
		atom_type = JSON.parse(atom_type);
		if (atom_type == "simple"){
			dropdown_content = '<p> Plot observed values from this point </p>';
		}
		else if (atom_type == "timeBetween") {
			dropdown_content = '<p> Fix this point and select the other one</p>';
		}
		else if (atom_type == "mixed") {
			dropdown_content = '<p> Fix this point and select the other one</p>';
		}
		for (var i=0; i<lines_list.length; i++){
			var no = lines_list[i];
			$("#line-number-"+no).attr('class', "code_listing_line code_listing_line-clickable")
			// TODO this may display the dropdown below multiple lines - fix
			$("#line-number-"+no).append('<div class="dropdown-content">'+dropdown_content+'</div>');
		}



	});




}


$("document").ready(function() {
	build_accordion();
	apply_function_list_click();
	apply_title_click();
});
