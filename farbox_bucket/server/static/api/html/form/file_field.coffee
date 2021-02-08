

file_field_init = (dom, filepath, post_url, auto_reload) ->
	dom = $(dom)
	filepath = filepath or 'data.zip'
	post_url = post_url or '/__file_manager_api'
	old_border_style = dom.css('border')
	hover_border_style = '1px solid indianred'
	if typeof(auto_reload) == "undefined"
		auto_reload = false
	dom.on
		drop: (e)=>
			e.preventDefault()
			file_list = e.originalEvent.dataTransfer.files
			if file_list.length == 1
				if Essage
					Essage.show('uploading file now...')
				f = file_list[0] # get the file obj
				xhr = new XMLHttpRequest()
				xhr.onreadystatechange = =>
					if xhr.readyState == 4 # loaded
						if xhr.status == 200 # ok
							dom.css('border', old_border_style)
							if Essage
								Essage.show('uploading finished', 3000)
							if auto_reload
								do_reload = confirm('file is uploaded, are you sure to refresh current page (make sure your contents are saved before refreshing)?')
								if do_reload
									window.location.reload()
						else if xhr.status > 200
							dom.css('border', old_border_style)
							if Essage
								Essage.show('uploading failed!!', 5000)
				xhr.open("post", post_url, true)
				fd = new FormData();
				fd.append(filepath, f)
				xhr.send(fd)
		dragleave: (e)=>
			e.preventDefault()
			dom.css('border', old_border_style)
		dragenter: (e)=>
			e.preventDefault()
			dom.css('border', hover_border_style)
		dragover: (e)=>
			e.preventDefault()
			dom.css('border', hover_border_style)


$(document).ready ->
	$('.form_file_dom').each ->
		dom = $(this)
		filepath = $.trim(dom.attr('data-filepath'))
		post_url = $.trim(dom.attr('data-post-url'))
		auto_reload = $.trim(dom.attr('data-auto-reload'))
		file_field_init(dom, filepath, post_url, auto_reload)