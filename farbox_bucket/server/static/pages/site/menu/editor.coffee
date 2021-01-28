@get_GET_arg = (name) ->
	reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)")
	r = window.location.search.substr(1).match(reg)
	if r
		return unescape(r[2])

@delete_nav = (button_dom)->
	button_dom = $(button_dom)
	nav_item_dom = button_dom.parents('li')
	# .removeData("mjs-nestedSortable").removeData("ui-sortable")
	nav_item_dom.remove()
	return false


@get_page_md_filepath_from_item = (inner_dom)->
	inner_dom = $(inner_dom)
	nav_item_dom = inner_dom.parents('li')
	url = nav_item_dom.find('input[name=url]').val()
	url = $.trim(url)
	md_filepath = ''
	if url
		url_path = url.split('?')[0]
		if /^[a-z0-9/]+\.(md|markdown|mk|txt)$/i.test(url_path)
			md_filepath = url_path
	return md_filepath


@show_or_hide_edit_button = (inner_dom)->
	inner_dom = $(inner_dom)
	md_filepath = get_page_md_filepath_from_item(inner_dom)
	nav_item_dom = inner_dom.parents('li')
	edit_button = nav_item_dom.find('.edit_page')
	if md_filepath
		url = "/system/site/pages?path="+md_filepath
		if site_id?
			url += '&site_id='+site_id
		edit_button.attr('href', url)
		edit_button.css('display', 'inline')
	else
		edit_button.css('display', 'none')


add_new_item = ->
	do_fix_editor()
	$('.sortable').append($('.li_template').html())
	return false

do_editor = ->
	$('.sortable').nestedSortable
		handle: 'div',
		items: 'li',
		toleranceElement: '> div'
		maxLevels: 3

do_fix_editor = ->
	if not $('.sortable > li').length and $('.sortable > ol').length
		$('.sortable').html($('.sortable > ol').html())


dump_item_dom = (dom)->
	item = {}
	dom = $(dom)
	dom.children('div').children('input').each ->
		input_dom = $(this)
		input_dom_name = input_dom.attr('name')
		input_dom_value = input_dom.val()
		if input_dom_name
			item[input_dom_name] = input_dom_value
	if dom.children('ol').length or dom.next('ol').length
		item['children'] = []
		if dom.children('ol').length
			children_doms = dom.children('ol').children('li')
		else
			children_doms = dom.next('ol').children('li')
		children_doms.each ->
			sub_item = dump_item_dom(this)
			if sub_item
				item['children'].push(sub_item)
	return item


dump_items_dom = (dom)->
	items = []
	$(dom).children('li').each ->
		item = dump_item_dom(this)
		if 'name' of item
			items.push(item)
	return items



dump_items = ->
	do_fix_editor()
	result = dump_items_dom('ol.sortable')
	if JSON?
		result = JSON.stringify(result, null, 4)
	else
		result = $.toJSON(result)
	if post_url?
		url_to_post = post_url
	else
		url_to_post = location.href

	if Essage
		Essage.show('sending data now...')

	user_nav_disabled = $("#nav_disable").prop('checked')

	$.ajax
		method: 'post',
		url: url_to_post,
		data: {raw_content: result, user_nav_disabled: user_nav_disabled}
		success: ->
			if Essage
				Essage.show({message: "Navigation configs are saved", status: "success"}, 2000)
	# console.log(result)
	return false


$(document).ready ->
	do_editor()
	$('#new_item').click(add_new_item)

	$('#save_nav').click(dump_items)

	$('.sortable').nestedSortable
		handle: 'div',
		items: 'li',
		tolerance: 'pointer',
		# placeholder: 'placeholder',
		toleranceElement: '> div'
		isAllowed: (placeholder, placeholderParent, currentItem)->
			pre_dom = placeholder.prev()
			if pre_dom.hasClass('sortable')
				return false
			return true

	$('input[name=url]').each ->
		url_input_dom = $(this)
		show_or_hide_edit_button(url_input_dom)
