
@when_mini_colors_show = ->
	if after_mini_colors_show?
		after_mini_colors_show()

@when_mini_colors_hide = ->
	if after_mini_colors_hide?
		after_mini_colors_hide()


@install_mini_colors = ->
	$('.color_input').minicolors({show:when_mini_colors_show, hide: when_mini_colors_hide})

$(document).ready ->
	install_mini_colors()