var process_subtree_accordion = function(path, subtree, dom_element, level) {
	// given a subtree, build the accordion.
	var padding = String(path.length * 2) + "px";
	if(Array.isArray(subtree)) {
		/*var radio_value = path + "-" + subtree[2];
		$(dom_element).html(subtree);
		$(dom_element).html('<button type="button" class="list-group-item" function-id="' + subtree[0] + '" style="padding-left:' + padding + '">' + 
				  	//'<h4 class="list-group-item-heading">' + subtree[1] + '</h4>' + 
				  	'<p class="list-group-item-text"><input type="radio" name="code" value="' + radio_value + '" />' + subtree[5] + ':</p>' + 
				  	'<p class="list-group-item-text">' + subtree[4] + '</p>' + 
				  '</button>');*/
	} else {
		var keys = [];
		for (var key in subtree) {
			keys.push(key);
		}
		console.log(keys);
		for(var i=0; i<keys.length; i++) {
			var key = keys[i];
			var checked = (i == 0 && level == 0) ? "checked" : "";
			// create list inside the current list in the dom
			var new_path = (path != "") ? (path + "-" + key) : key;
			$(dom_element).append('<div class="panel panel-default">' + 
			  '<div class="panel-heading">' +
			    '<h3 class="panel-title" id="external-' + new_path + '" style="padding-left: ' + padding + '"><input type="radio" ' + checked + ' name="code" value="' + new_path + '" />' + key + '</h3>' + 
			  '</div>' + 
			  '<div class="panel-body">' + 
			    '<div class="list-group" id="' + new_path + '">' + 
				'</div>' + 
			  '</div>' + 
			'</div>')
			//$(dom_element).append('<p>' + key + '</p><ul id="' + new_path + '"></ul>');
			process_subtree_accordion(new_path, subtree[key], $("#" + new_path), level+1);
		}
	}
}

var build_accordion = function() {
	// get the data from the "#function-list-data" element, and
	// recursively construct an accordion.

	function_list_data = JSON.parse($("#function-list-data").html());

	for(var key in function_list_data) {
		process_subtree_accordion("", function_list_data, $("#function-list"), 0);
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

var search_click = function() {
	$("#trigger-search").click(function(e) {
		var verdict = $("input[name='verdict']:checked").val();
		var code_path =  $("#function-list").find("input[name=code]:checked").val();
		// replace - with . globally in the code path
		code_path = code_path.replace(/-/g, ".");

		// now we have the verdict and the code path to use to select properties, we can request data from the server
		$.get("/list_function_calls_from_verdicts/" + verdict + "/" + code_path + "/", function(data) {
			$("#results-list").html(data);
		});
	});
}

$("document").ready(function() {
	build_accordion();
	search_click();
});