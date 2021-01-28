@run_ajax_backend = (url, method, callback_func, data)->
	if typeof(data)=='string'
		data = $.parseJSON(data)
	if typeof(callback_func)=='string'
		callback_func = window[callback_func]
	ajax_data =
		url: url
		method: method
		success: (response_data)->
			if callback_func
				callback_func(true, response_data)
		error: (response_data)->
			if callback_func
				callback_func(false, response_data)
	if data
		$.extend(ajax_data, data)
	$.ajax(ajax_data)
	return false
