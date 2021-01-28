g = this
@sidebar_width = 300
sidebar_in_left = true

show_sidebar = ->
	$("body").css("overflow-x", "hidden")

	if sidebar_in_left
		$("body").animate {marginLeft: g.sidebar_width+'px'}, 'fast'
		sidebar_dom.animate({left: '0'}, 'fast')
	else
		$("body").animate {marginRight: g.sidebar_width+'px'}, 'fast'
		sidebar_dom.animate({right: '0'}, 'fast')

	$("body .auto_header").animate {width: $(window).width()-g.sidebar_width+'px'}, 'fast'


	$(".sidebar_clicker").removeClass("click_to_open_sidebar").addClass("click_to_close_sidebar")


hide_sidebar = ->
	if sidebar_in_left
		$("body").animate {left: '0', marginLeft: '0'}, 'fast'
		sidebar_dom.animate({left: -g.sidebar_width*1.1+'px'}, 'fast')
	else
		$("body").animate {right: '0', marginRight: '0'}, 'fast'
		sidebar_dom.animate({right: -g.sidebar_width*1.1+'px'}, 'fast')

	$("body .auto_header").animate {width: $(window).width()+'px'}, 'fast'



	$(".sidebar_clicker").removeClass("click_to_close_sidebar").addClass("click_to_open_sidebar")
	$("body").css("overflow-x", "visible")


@run_sidebar = (side, sidebar_name, width, default_status)=>
	@sidebar_width = width or @sidebar_width
	side = side or 'left'
	sidebar_name = sidebar_name or 'sidebar'
	default_status = default_status or 'hide'
	$(document).ready =>
		if sidebar_name.indexOf('#') == 0
			@sidebar_dom = $(sidebar_name)
		else
			@sidebar_dom = $('.'+sidebar_name)
		if not @sidebar_dom.length
			@sidebar_dom = $('#'+sidebar_name)

		if side == 'left'
			sidebar_in_left = true
		else
			sidebar_in_left = false

		sidebar_css = {}

		if sidebar_in_left
			if default_status == 'hide'
				sidebar_css['left'] = -g.sidebar_width*1.1+'px'
		else
			if default_status == 'hide'
				sidebar_css['right'] = -g.sidebar_width*1.1+'px'

		sidebar_dom.css(sidebar_css)

		if @sidebar_dom.css("display") in ['hidden', 'none', null]
			@sidebar_dom.css("display", "block")



		$('body').delegate '.click_to_open_sidebar', 'click', show_sidebar
		$('body').delegate '.click_to_close_sidebar', 'click', hide_sidebar
		$('.main').click(hide_sidebar)

		if $(window).width()< 480
			hide_sidebar()
