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
	content = @doc.getValue()
	$.ajax(
		url: '/__file_manager_api',
		method: 'post',
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




$(document).ready =>
	ext = location.pathname.split('.').pop()
	if ext == 'jade'
		mode = {name: "jade", alignCDATA: true}
	else if ext in ['html', 'xml']
		mode = 'text/html'
	else if ext in ['js', 'json']
		mode = 'javascript'
	else if ext == 'less'
		mode = "text/x-less"
	else if ext in ['sass', 'scss']
		mode = "text/x-scss"
	else if ext == 'css'
		mode = 'text/css'
	else if ext == 'coffee'
		mode = 'text/x-coffeescript'
	else if ext in ['txt', 'md', 'markdown', 'mk']
		mode = 'text/x-markdown'
	else
		mode = ''


	@code_editor = CodeMirror(document.getElementById("editor"), {
		value: $('#content_container').val(),
		lineNumbers: true,
		lineWrapping: true,
		matchBrackets: true,
		mode: mode,
		theme: 'solarized',
		indentWithTabs: true,
	})
	@doc = @code_editor.getDoc()
	@doc.on 'change', (the_doc, change_obj) =>
		@hit_sync()

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





	#$(document).bind('keydown', 'ctrl+s', @save_doc_by_shortcut)
	#$(document).bind('keydown', 'meta+s', @save_doc_by_shortcut)
