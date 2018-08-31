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
			html_string += ('<button type="button" class="list-group-item" function-id="' + subtree[i][0] + '" style="padding-left:' + padding + '">' + 
					  	//'<h4 class="list-group-item-heading">' + subtree[1] + '</h4>' + 
					  	'<p class="list-group-item-text">' + subtree[i][5] + ':</p>' + 
					  	'<p class="list-group-item-text">' + subtree[i][4] + '</p>' + 
					  '</button>');
		}
		$(dom_element).html(html_string);
	} else {
		var keys = [];
		for (var key in subtree) {
			keys.push(key);
		}
		console.log(keys);
		for(var i=0; i<keys.length; i++) {
			var key = keys[i];
			// create list inside the current list in the dom
			var new_path = (path != "") ? (path + "-" + key) : key;
			$(dom_element).append('<div class="panel panel-default">' + 
			  '<div class="panel-heading">' +
			    '<h3 class="panel-title" id="external-' + new_path + '" style="padding-left: ' + padding + '">' + key + '</h3>' + 
			  '</div>' + 
			  '<div class="panel-body">' + 
			    '<div class="list-group" id="' + new_path + '">' + 
				'</div>' + 
			  '</div>' + 
			'</div>')
			//$(dom_element).append('<p>' + key + '</p><ul id="' + new_path + '"></ul>');
			process_subtree_accordion(new_path, subtree[key], $("#" + new_path));
		}
	}
}

var build_accordion = function() {
	// get the data from the "#function-list-data" element, and
	// recursively construct an accordion.

	function_list_data = JSON.parse($("#function-list-data").html());

	for(var key in function_list_data) {
		process_subtree_accordion("", function_list_data, $("#function-list"));
	}

	apply_accordion_clicks();
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

	$("#http-request-title").click(function() {
		$("#http-request-list").slideToggle();
	});

	$("#function-call-title").click(function() {
		$("#function-call-list").slideToggle();
	});
}

var apply_function_list_click = function() {
	$("#function-list").find(".list-group-item").click(function(e) {
		$("#function-list").slideUp();
		$("#http-request-list").slideDown();
		$("#function-call-list").slideUp();
		var function_id = $(e.target).closest(".list-group-item").attr("function-id");
		selected_function_id = function_id;
		$.get("/list_http_requests/" + function_id, function(data) {
			$("#http-request-list").html("");
			for(var i=0; i<data.length; i++) {
				var button = document.createElement("button");
				button.className = "list-group-item";
				button.innerHTML = data[i][1];
				$(button).attr("http-request-id", data[i][0]);
				$("#http-request-list").append(button);
			}
			apply_http_request_list_click();
		});
	});
};

var apply_http_request_list_click = function() {
	$("#http-request-list").children(".list-group-item").click(function(e) {
		$("#function-list").slideUp();
		$("#http-request-list").slideUp();
		$("#function-call-list").slideDown();
		var http_request_id = $(e.target).closest(".list-group-item").attr("http-request-id");
		selected_http_request_id = http_request_id;
		$.get("/list_function_calls/" + http_request_id + "/" + selected_function_id, function(data) {
			$("#function-call-list").html("");
			for(var i=0; i<data.length; i++) {
				var button = document.createElement("button");
				button.className = "list-group-item";
				button.innerHTML = data[i][2];
				$(button).attr("function-call-id", data[i][0]);
				$("#function-call-list").append(button);
			}
			apply_function_call_list_click();
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
		$.get("/list_verdicts/" + function_call_id, function(data) {
			for(var i=0; i<data.length; i++) {
				var li = document.createElement("div");
				li.className = "list-group-item";
				li.innerHTML = '<h4 class="list-group-item-heading">Lines ' + data[i][0] + '<span class="badge ' + truth_map[Number(data[i][1])] + '">' + truth_map[Number(data[i][1])] + '</span></h4>' +
				'<p class="list-group-item-text">reached at ' + data[i][2] + '</p>';
				$("#verdict-list").append(li);
			}
		});
	});
};

$("document").ready(function() {
	build_accordion();
	apply_function_list_click();
	apply_title_click();
});