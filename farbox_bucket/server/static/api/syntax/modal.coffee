g = this
@current_modal_click_button_value = null
@current_modal_click_button_value2 = null
@current_modal_click_button_value3 = null

$(document).ready ->
	$(document).on 'modal:close', (event, modal)->
		try Essage.hide()


	$('input.modal_with_selector').each (i,dom)->
		dom = $(dom)
		modal_dom = $(dom.attr('data-modal-dom'))
		click_dom = $(dom.attr('data-click-dom'))
		click_dom.click ->
			modal_dom.modal()
			current_click_dom = $(this)
			g.current_modal_click_button_value = current_click_dom.attr('data-value')
			g.current_modal_click_button_value2 = current_click_dom.attr('data-value2')
			g.current_modal_click_button_value3 = current_click_dom.attr('data-value3')
			if after_modal_display?
				try after_modal_display(current_click_dom, modal_dom)
			return false

