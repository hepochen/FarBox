
get_toc_default_top = ->
	return $('.doc_toc').offset().top or 0

$(document).ready =>
	toc_selector = '.doc_toc'
	current_active_class = 'current_active'
	toc_element = $(toc_selector)

	$('.doc_toc a').click ->
		toc_content_dom_id = $(this).attr('href').slice(1)
		if toc_content_dom_id
			toc_content_dom = $('#'+toc_content_dom_id)
			y = toc_content_dom.offset().top
			scroll_to_y = y
			if scroll_to_y < 0
				scroll_to_y = 0
			$('body,html').animate {scrollTop: scroll_to_y }, 800
			new_hash_name = '#'+toc_content_dom_id
			if history.pushState
				history.pushState(null, null, new_hash_name);
			else
				window.location.hash = new_hash_name
			return false

	remove_current_toc_active_class = ->
		$(toc_selector+' .'+current_active_class).removeClass(current_active_class)

	toc_element.on 'activate.bs.scrollspy', ->
		current_active_element = $(toc_selector+' .active').last()
		remove_current_toc_active_class()
		current_active_element.addClass(current_active_class)

	toc_element.on 'clear.bs.scrollspy', remove_current_toc_active_class


	$('.doc_toc_container').affix({
		offset: {
			top: (toc_offset_top if toc_offset_top?) or get_toc_default_top(),
			bottom: (toc_offset_bottom if toc_offset_bottom?) or 0
		}
	});

	$(document).on 'affixed.bs.affix', ->
		height = (document.body.clientHeight - 100) or 'auto'
		$('.doc_toc').css('max-height', height)


	$('body').scrollspy({target: toc_selector})

	if $(window).width()< 480
		$('.doc_toc').css('display', 'none')
