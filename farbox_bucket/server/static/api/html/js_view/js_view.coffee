

@display_js_view_player = (dom)->
	player = $(dom)
	width = player.attr('data-width') or $(window).width()*0.8
	height = player.attr('data-height') or $(window).height()*0.8
	width = parseInt(width)
	height = parseInt(height)
	max_width = parseInt($(window).width()*0.9)
	if width > max_width
		height = parseInt(max_width/width*height)
		width = max_width
	real_player = $(player.attr('href')).find('video').parent()
	player_button = real_player.find('.vjs-big-play-button')
	player_left = (width-player_button.width())/2
	player_top = (height-player_button.height())/2
	player_button.css('left', player_left)
	player_button.css('top', player_top)
	real_player.css('width', width)
	real_player.css('height', height)
	player.colorbox({inline:true, innerWidth:width, innerHeight:height, onComplete:->
		player = $(this)
		video = videojs('#player_'+player.attr('href').slice(1))
		video.play()
		real_player = $(player.attr('href')).find('video').parent()
		real_player.css('width', width)
		real_player.css('height', height)
	onClosed:->
		player = $(this)
		video = videojs('#player_'+player.attr('href').slice(1))
		video.pause()
	})
	return false

@display_js_view_html = (dom)->
	inner_html = $(dom).children('.js_view_inner_html').html()
	$.colorbox({html:inner_html});
	return false


@display_js_view_iframe = (dom)->
	dom = $(dom)
	iframe_src = $(dom).attr('href')
	$.colorbox({iframe:true, width:'80%', height:'80%', href:iframe_src})
	return false


@display_js_view_image = (dom)->
	dom = $(dom)
	link_url = dom.attr('href')
	title = dom.attr('title') or ''
	group_id = dom.attr('data-group-id')
	if not group_id
		$.colorbox({photo:true, maxWidth: '100%', maxHeight: '100%', href:link_url, title: title, rel: group_id})
	return false



@show_js_view = (dom)->
	dom = $(dom)
	if dom.hasClass('js_view_video')
		display_js_view_player(dom)
	else if dom.hasClass('js_view_html')
		display_js_view_html(dom)
	else if dom.hasClass('js_view_iframe')
		display_js_view_iframe(dom)
	else if dom.hasClass('js_view_image')
		display_js_view_image(dom)


$(document).ready ->
	$('.js_view_group').each ->
		group_id = $(this).attr('data-group-id')
		if group_id
			$(this).colorbox({rel:group_id, transition:"fade"})
