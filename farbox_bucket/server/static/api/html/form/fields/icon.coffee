

@pick_icon_for_field = (click_dom)->
	parent_dom = $(click_dom).parent()
	icon_input_dom = parent_dom.find('.icon_input')
	icon_input_dom.inputIconSelector()

@when_icon_inserted = (icon_input_dom)->
	if icon_input_dom.hasClass('icon_input')
		field_dom = icon_input_dom.parent()
		i_dom = field_dom.find('span i')
		i_dom.html('')
		i_dom.attr('class', icon_input_dom.val())
