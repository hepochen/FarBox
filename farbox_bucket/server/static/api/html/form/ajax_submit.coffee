@ajax_submit_installed = false
@g = this;

@install_ajax_submit = ->
	if ajax_submit_installed
		return false
	$('form button[type=submit]').click (event)->
		event.preventDefault()
		button_dom = $(this)
		form_dom = button_dom.parents('form')
		$(this).attr("disabled", true)

		# get other mixed field
		if get_form_extra_data?
			extra_data = get_form_extra_data(form_dom)
		else
			extra_data = {}
		extra_data['ajax'] = true

		if current_modal_click_button_value?
			extra_data['click_button_value'] = current_modal_click_button_value

		form_dom.ajaxSubmit
			data: extra_data
			beforeSubmit: ->
				if Essage
					Essage.show("send data to server now...")
			success: (text, status_text, xhr, _form_dom)->
				button_dom.removeAttr("disabled")
				$('.essage').css('position', 'fixed')
				if status_text == 'success'
					if after_ajax_submit?
						after_ajax_submit()
					if text and text.indexOf('url:')==0
						url_to_jump = text.slice(4)
						window.location.href = url_to_jump
						return false
					if text and text.indexOf('js:')==0
						js_content = text.slice(3)
						eval(js_content)
						if Essage?
							Essage.show("done", 2000)
							Essage.hide()
						return false
					if text and text.indexOf('info:') == 0
						info = text.slice(5)
						return Essage.show({status: "success", message:info}, 5000)
					if Essage?
						if text
							Essage.show({status:"error", message:text})
						else
							Essage.show({status: "success", message:"current data submit done"}, 3000)
				else
					if Essage?
						Essage.show({status:"error", message:status_text})
	g.ajax_submit_installed = true
	return

$(document).ready ->
	install_ajax_submit()



