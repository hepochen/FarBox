@install_sliders = ->
	$('.bitcron_slider').each ->
		slider_dom = $(this)
		autoplay = if slider_dom.attr('data-autoplay')=='true' then true else false
		show_arrows = if slider_dom.attr('data-show-arrows')=='true' then true else false
		animation = slider_dom.attr('data-animation') or 'horizontal'
		unslider_configs = {autoplay:autoplay, arrows:show_arrows, animation:animation}
		slider_dom.unslider(unslider_configs)

$(document).ready ->
	install_sliders()