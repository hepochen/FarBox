@remove_dom_list_item = (dom)->
	action_dom = $(dom)
	list_item_dom = action_dom.parents('.dom_list_item')
	list_item_dom.remove()
	return false

@add_dom_list_item = (dom)->
	action_dom = $(dom)
	list_dom = action_dom.parents('.dom_list')
	template_dom = list_dom.find('.template')
	new_item_dom = template_dom.clone()
	new_item_dom.removeClass('template')
	new_item_dom.insertBefore(template_dom)
	new_item_dom.css('display', 'block')

	if init_image_fields?
		init_image_fields()
	return false

@to_json = (obj)->
	if JSON?
		result = JSON.stringify(obj, null, 4)
	else
		result = $.toJSON(obj)
	return result

@auto_set_key_value = (obj, key, value)->
	# {"a.b": "c"} -> {"a":{"b": "c"}}
	if not key
		return
	if key.indexOf('.') != -1
		key_parts = key.split(".")
		key1 = key_parts[0]
		key2 = key_parts[1]
		if not obj[key1]
			obj[key1] = {}
		obj[key1][key2] = value
	else
		obj[key] = value


@auto_obj_by_auto_key = (obj)->
	new_obj = {}
	for key of obj
		value = obj[key]
		auto_set_key_value(new_obj, key, value)
	return new_obj



@dom_to_data = (dom, as_list)->
	dom = $(dom)
	if not dom.length
		return null

	value_dom = null
	dom_finders = ['img.form_image_dom', '.form_file_dom', 'textarea', 'select', 'input']
	for finder in dom_finders
		dom_found = dom.find(finder)
		if dom_found.length
			value_dom = dom_found
			break

	if not value_dom
		if dom[0].tagName in ['INPUT', 'TEXTAREA', 'SELECT']
			value_dom = dom
	if not value_dom
		return null

	key = value_dom.attr('name')
	if value_dom.hasClass('form_image_dom') or value_dom.hasClass('form_file_dom')
		value = value_dom.attr('data-filepath')
	else
		value = value_dom.val()
	if not key
		return null
	if as_list
		return [key, value]
	else
		data = {}
		data[key] = value
		return data


@list_dom_to_data = (list_dom)->
	list_dom = $(list_dom)
	data_list = []
	list_dom.find('.dom_list_item').each ->
		item_dom = $(this)
		data = {}
		item_dom.find('.field').each ->
			element_data = dom_to_data(this)
			if element_data
				$.extend(data, element_data)
		if not item_dom.hasClass('template')
			data = auto_obj_by_auto_key(data)
			data_list.push(data)
	return data_list


@get_form_extra_data = (form_dom)->
	form_dom = $(form_dom)
	data = {}
	for list_dom in form_dom.find('.field .dom_list')
		# 处理list逻辑，比如 links/ images
		list_dom = $(list_dom)
		key = list_dom.attr("data-value")
		auto_set_key_value(data, key, list_dom_to_data(list_dom))
	for key of data
		data[key+'@json'] = to_json(data[key])
	return data


$(document).ready ->
	try $('.dom_list_body').sortable()