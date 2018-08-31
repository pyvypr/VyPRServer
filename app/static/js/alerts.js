/*

File for miscellaneous functions used in cmsDbServiceStats service.

*/

var view_rendering_error = function(error_message) {
	// find another way to do this
	return $('<div class="alert alert-info" role="alert">' + error_message + '</div>');
}