/* JavaScript for index page */

var selected_function_id;
var selected_http_request_id;
var selected_function_call_id;

var truth_map = {1 : "No Violation", 0 : "Violation"};

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

	function_list_data = JSON.parse($("#function-list-data").html());
	dom_elem = $("#function-list");
	content = '<div class="tab">';

	// if we don't want the first tab to be open on the page load, set to 0
	is_first = 1;

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
	tablinks = document.getElementsByClassName("tablinks")
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
			$.get("/get_function_property_data/" + function_id, function(new_data) {
			    // here we will process the source code + property information and display on the page
			});
		});
	});
};

var apply_function_call_list_click = function() {
	$("#function-call-list").children(".list-group-item").click(function(e) {
		$("#function-list").slideUp();
		$("#http-request-list").slideUp();
		$("#function-call-list").slideDown();
		var function_call_id = $(e.target).closest(".list-group-item").attr("function-call-id");
		selected_function_call_id = function_call_id;
		$("#verdict-list").html("");
		// toggle the checkbox for the box that was clicked
		$(e.target).children("input[type=checkbox]").prop("checked",
		    !$(e.target).children("input[type=checkbox]").prop("checked"));
		// get all the checked boxes and, from there, get a list of function call IDs
		var function_call_ids = $(e.target).parent().parent().find("input:checked").map(function(i, d) {
		    return $(d).attr("function-call-id");
		}).get();
		// send a request to the server with the function call IDs that have been selected
		$.post("/get_function_calls_data/", {"ids" : function_call_ids}).done(function(data) {
		    // here we will process the information from the function calls and
		    // put it on the page with with the source code and property information
		});
	});
};

$("document").ready(function() {
	build_accordion();
	apply_function_list_click();
	apply_title_click();
});
