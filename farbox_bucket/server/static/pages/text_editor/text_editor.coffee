@need_sync = false
@keep_sync_binded = false
@sync_per_seconds = 20 # 20秒同步一次



@keep_sync = =>
	if not @need_sync
		return false
	else if @last_sync_at
		diff_seconds = @sync_per_seconds - (new Date() - @last_sync_at)/1000
		$('.precess').css('width', 100*(1-diff_seconds/@sync_per_seconds)+'%')
		if diff_seconds > 0
			return # ignore
		else
			@save_doc()


@hit_sync = =>
	# 第一次按键，初始化
	if not @keep_sync_binded
		@keep_sync_binded = true
		setInterval(@keep_sync, 300)
		@last_sync_at = new Date()
		@need_sync = true

	if not @need_sync # 计时重置
		@last_sync_at = new Date()

	@need_sync = true
	$('#save_button').css('display', 'block')
	# @show_tip_info(true)




@save_doc = ->
	@need_sync = false
	$('.precess').css('width', 0)
	$('#save_button a').text('saving...')
	doc_path = $('#doc_path').val()
	content = $.trim($('textarea').val())
	$.ajax(
		url: '/__file_manager_api',
		method: 'post',
		data: {raw_content:content, path:doc_path},
		success: (sync_info)->
			$('#save_button').css('display', 'none')
			$('#save_button a').text('save')
		error: (error_data)->
			error_obj = error_data.responseJSON or error_data.responseText
			if typeof(error_obj)== 'string'
				error_obj=JSON.parse(error_obj)
			#console.log(error_obj)
	)


@save_doc_by_shortcut = =>
	if $('#save_button').css('display')!='none'
		@save_doc()


####################################


@fit_textarea = ->
	fixed_width = 780
	current_width = $(window).width()
	padding_width = (current_width-fixed_width)/2
	if padding_width < 15
		padding_width = 15
	textarea_dom = $('textarea')
	title_dom = $('#title')
	for dom in [textarea_dom, title_dom]
		dom.css('padding-left', padding_width+'px')
		dom.css('padding-right', padding_width+'px')


@fill_textarea = ->
	textarea_dom = $('textarea')
	default_content = $.trim($(textarea_dom).val())
	if not default_content
		now = new Date()
		header_content = 'title:  ' + $.format.date(now, 'yyyy-MM-dd') + '\ndate: ' + $.format.date(now, 'yyyy-MM-dd HH:mm')  + '\n\n'
		textarea_dom.val(header_content)

	textarea_dom.focus()




$(document).ready =>
	fit_textarea()
	$(window).resize(fit_textarea)

	fill_textarea()

	#$('textarea').keyup(hit_sync)
	$('textarea').bind('input propertychange', hit_sync)

	$(window).keydown =>
		if event.which in [83,115] and (event.ctrlKey or event.metaKey)
			event.preventDefault()
			@save_doc_by_shortcut()
			return false
		if event.which in [69,101] and (event.ctrlKey or event.metaKey) and window.parent and window.parent.toggle_files_manager
			event.preventDefault()
			window.parent.toggle_files_manager()
			return false
		else
			return true