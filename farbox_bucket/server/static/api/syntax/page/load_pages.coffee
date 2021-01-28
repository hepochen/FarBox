on_page_loading = false
finish_page_loading = false
next_page_number = 2

load_next_page = (container_id, loading_id, callback)=>
	container_dom_id = '#' + container_id
	loading_dom_id = '#' + loading_id
	on_page_loading = true
	$(loading_dom_id).css('display', 'block')
	url = location.pathname+'/page/'+next_page_number+location.search
	url = url.replace(/\/{2,}/g, '/')

	if auto_load_page_callback? and not callback
		callback = auto_load_page_callback

	$.get url, {pjax: true}, (data)->
		$(loading_dom_id).css('display', 'none')
		if data.length < 20
			finish_page_loading = true
		else
			try
				$(container_dom_id).append(data)
			next_page_number += 1
			on_page_loading = false
		if callback
			callback()

auto_load_pages = (container_id, loading_id, callback)->
	bottom_diff = $(document).height() - $(window).height() - $(window).scrollTop()
	if bottom_diff < 80 and not on_page_loading and not finish_page_loading and location.search.indexOf('?s=') == -1
		load_next_page(container_id, loading_id, callback)

load_more = ->
	if auto_load_page_container_id?
		dom_id = auto_load_page_container_id or 'list_container'
	else
		dom_id = 'list_container'
	auto_load_pages(dom_id, 'on_loading')

$(document).ready ->
	$(window).scroll(load_more)
	load_more()