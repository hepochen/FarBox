posts_host = '/__web_editor_posts'+location.search
sync_gateway = '/__file_manager_api'+location.search
controls_width = 235

@canvas_allowed = Boolean(document.createElement('canvas').getContext)

raw_lang = window.navigator.language or window.navigator.userLanguage or window.navigator.browserLanguage or window.navigator.Language
@lang = raw_lang.toLowerCase().replace('-', '_')

if @lang == 'zh_cn'
	@simple_help = '欢迎使用 FarBox 的在线Editor，这是第一篇文章。
	\n\n第一行是使用 key: value 形式的，表示对文章的特殊定义，比如 Date: 2014-10-20 22:40 或者 Tags: Hello，当然，没有也没有关系。
	\n\FarBox 支持 Markdown语法，当然，不知道 Markdown 是什么，直接写也没有关系。
	\n\n如果需要插入图片，直接拖入到编辑区域就可以了。'
else
	@simple_help = 'Welcome to FarBox online Web Editor, this is your first post.
	 \n\nContents in first line like key: value, means the metadata of current post, like Date: 2014-10-20 22:40 or Tags: Hello. Of course, a post without metadata, it\'s ok.
	\n\nFarBox supports Markdown, but if you do not know Markdown, just write, it just works.
	\n\nIf you want to insert an image, just drag it into the textarea.'

$.fn.shake = (options) ->
	selector = this
	settings = $.extend({'speed':100,'margin':20,'onComplete': false,'onStart':false},options)
	speed = settings['speed']
	margin = settings['margin']
	margin_total = parseInt(margin) + parseInt(margin)
	onComplete = settings['onComplete']
	onStart = settings['onStart']
	if onStart
		eval(onStart)
	$(selector).animate {marginLeft:margin}, speed/2, ->
		$(selector).animate {marginLeft:'-'+margin_total}, speed, ->
			$(selector).animate {marginLeft:''+margin_total},speed, ->
				$(selector).animate {marginLeft:'-'+margin_total},speed, ->
					$(selector).animate {marginLeft:''+margin_total},speed, ->
						$(selector).animate {marginLeft:'-'+margin_total},speed, ->
							$(selector).animate {marginLeft:'-0'},speed, ->
								if onComplete
									eval(onComplete)

is_touch_device = ->
	return 'ontouchstart' of window




Post = (raw_post, editor) ->
	if raw_post.raw_path
		path_parts = raw_post.raw_path.split('/')
		@path = path_parts.slice(1).join('/')
	else
		@path = raw_post.path
	@title = ko.observable(raw_post.title)
	raw_content = raw_post['raw_content'] or ''
	prereged_title = raw_post.title
	for c in ['$','\\','{','}','[',']','(',')','^','.','*','+','?','|']
		prereged_title = prereged_title.replace(c,'\\'+c)
	title_reg = new RegExp('(?:^|([\r\n]))Title: ?'+ prereged_title + ' *[\r\n]', 'i')
	@content = raw_content.replace(title_reg, '$1')

	@edit = =>

		if is_touch_device() or $(window).width()<321
			editor.hide_controls()

		t_dom = $('#textarea')

		# 处理之前的post先
		if editor.current_post()
			editor.current_post()['content'] = t_dom.val()
			editor._sync(editor.get_path(), editor.get_content()) # 切换文章编辑的时候，先进行一次同步

		if not $.trim(@content)
			# 填充时间戳
			@content = 'Date: ' + $.format.date(new Date(), 'yyyy-MM-dd HH:mm')  + '\n\n'
			if editor.posts().length == 1
				@content += simple_help
			to_tail = true
		else
			to_tail = false

		t_dom.val(@content)
		t_dom.focus()

		if to_tail
			@to_text_tail()
		else
			@to_text_first_line_end()

		$('#posts li a.current').removeClass('current')
		index = $.inArray(this, editor.posts())
		current_post_dom = $($('#posts li a')[index])
		current_post_dom.addClass('current')
		editor.current_post(this)

	@to_text_tail = ->
		obj = $('#textarea')[0]
		obj.selectionStart = obj.selectionEnd = obj.value.length

	@to_text_first_line_end = ->
		obj = $('#textarea')[0]
		if obj.value.indexOf('\n')
			obj.selectionStart = obj.selectionEnd = obj.value.indexOf('\n')
		else
			obj.selectionStart = obj.selectionEnd = obj.value.length

	@remove = =>
		if confirm("are you sure to delete this post?")
				this.do_remove()

	@do_remove = =>
		$.post sync_gateway, {'path': @path, 'is_deleted': true}
		editor.posts.remove(this)
		if editor.posts().length
			if @path == editor.get_path() # 删除了当前的post，需要focus到第一篇
				current = editor.posts()[0]
				current.edit()
		else
			editor.create_first_post()

	return this


EditorModel = ->
	self = this
	controls = $('#controls')
	@posts = ko.observableArray([])
	@current_post = ko.observable({})
	@current_title = ko.observable('')
	@need_sync = ko.observable(false)
	@sync_per_seconds = 20 # 20秒同步一次

	@show_tip_info = ko.observable(false)
	@tip_info = ko.observable('Save')
	@wait_to_sync_precess = ko.observable(0)


	@load_posts = =>
		# load the posts data
		$.getJSON posts_host, {}, (posts)=>
			for post in posts
				@posts.push(new Post(post, self))
			# 进入编辑模式
			if @posts().length
				@posts()[0].edit()
			else
				@create_first_post()

	@create_first_post = =>
		title = $.format.date(new Date(), 'yyyy-MM-dd')
		path = title + '.txt'
		new_post = new Post({path: path, title: title}, self)
		@.posts.unshift(new_post)
		new_post.edit(true)


	@open_new_window = ->
		$('#new_window').css('display', 'block')
		$('#window_bg').css('background', '#000')
		$('#window_bg').css('opacity', '0.6')
		$('#new_window input').val('')
		$('#new_window input').focus()

	@hide_new_window = ->
		$('#new_window').css('display', 'none')

	@create_new_one = =>
		new_path = $.trim($('#new_path').val())
		if new_path
			if not new_path.match(/\.(md|markdown|txt|mk)$/gi)
				new_path = new_path+'.txt'
			paths = $.map @posts(), (post) -> post.path
			if $.inArray(new_path, paths) == -1
				title = new_path.replace(/\.(md|markdown|txt|mk)$/gi, '')
				new_post = new Post({path: new_path, title: title}, self)
				@.posts.unshift(new_post)
				new_post.edit()
				@hide_new_window()
			else
				$('#new_window_body').shake()
		else
			$('#new_window_body').shake()
		$('#new_window input').focus()

	@show_controls = ->
		if is_touch_device()
			$('#show_controls_button').css('display', 'none')
			controls.css('display', 'block')


		if controls.position().left <= -controls_width
			controls.animate({
				left: 0,
				opacity: 1
			}, 350, 'swing', make_textarea_center)
		if $.browser.msie
			$('#textarea').blur()

	@hide_controls = ->
		if is_touch_device() or $(window).width()<321
			controls.css('display', 'none')
			controls.css('left', -controls_width)
			$('#show_controls_button').css('display', 'block')
			return false

		if controls.position().left == 0
			controls.animate({
				left: -controls_width,
				opacity: 0.3
			}, 500, 'swing', make_textarea_center)
			#setTimeout(make_textarea_center, 501)

		$('#textarea').focus()

	@toggle_controls = ->
		hide_controls_button = $('#hide_controls')
		button_left = hide_controls_button.offset().left
		if button_left > -10
			self.hide_controls()
		else
			self.show_controls()




	if not is_touch_device()
		controls.mouseenter(@show_controls)

	if is_touch_device()
		@hide_controls()


	@get_content = =>
		title = $.trim($('#title').val())
		title_value = 'Title: ' + title + '\n'
		raw_content = $.trim($('#textarea').val())
		if raw_content.match(/^\s*---\s*[\r\n]/)
			content = raw_content.replace(/^\s*---\s*[\r\n]/, '---\n'+title_value)
		else
			content = title_value + raw_content
		return content

	@get_path = =>
		return @current_post().path

	@sync = (e)=>
		# 第一次按键，初始化
		if not @keep_sync_binded
			@keep_sync_binded = true
			setInterval(@keep_sync, 1000) # 键盘闲置1秒的时候，检测
			@last_sync_at = new Date()
			@need_sync(true)

		if not @need_sync() # 计时重置
			@last_sync_at = new Date()

		@need_sync(true)
		@show_tip_info(true)

		diff_seconds = @sync_per_seconds - (new Date() - @last_sync_at)/1000
		@wait_to_sync_precess(100*(1-diff_seconds/@sync_per_seconds)+'%')

		if diff_seconds > 0
			return false # ignore
		else
			@_sync()

	@keep_sync = =>
		if not @need_sync()
			return false
		else
			@sync()


	@_sync = (path, content)=>
		if typeof(path) != 'string'
			path = ''
		if typeof(content) != 'string'
			content = ''

		if not @need_sync()
			return false # ignore
		else
			@last_sync_at = new Date()
			@need_sync(false) # reset
			$('#textarea').focus()

		@tip_info('Saving...')
		path = path or @get_path()
		content = content or @get_content()
		data = {
			path: path,
			raw_content: content
		}
		$.post sync_gateway, data, =>
			@tip_info('Save')
			if not @need_sync()
				@show_tip_info(false)


	@insert_image_allowed = =>
		if not canvas_allowed
			return false
		dom = $('#textarea')
		$(dom)[0].addEventListener  'drop', (event)=>
			files = event.dataTransfer.files

			for file in files
				if file.type.indexOf( 'image' ) == -1
					continue

				reader = new FileReader()
				reader.readAsDataURL(file)
				reader.onload = (ev)=>
					@upload_image(ev.target.result)
			event.preventDefault()
		, false

		$(dom)[0].addEventListener 'dragover', (event)->
			event.preventDefault()
		, false


	@canvas =  document.createElement( 'canvas' )
	if canvas_allowed
		@cx = @canvas.getContext('2d')
	else
		@cx = null

	@upload_image = (file)=>
		if not canvas_allowed
			return false

		img = new Image()
		img.src = file

		# get the image data and upload to server
		$(img).one 'load', ->
			width = @naturalWidth or @width
			height = @naturalHeight or @height
			thumb_height = 2560
			thumb_width = 1280
			width_r = width/thumb_width
			height_r = height/thumb_height
			max_r = Math.max(width_r, height_r)
			w = if max_r>1 then width/max_r else width
			h = if max_r>1 then height/max_r else height

			self.canvas.width = w
			self.canvas.height = h
			self.cx.drawImage(this, 0, 0, w, h)

			image_path = '/_image' + $.format.date(new Date(), '/yyyy-MM-dd/HH-mm-ss') + '.jpg'

			request_data = {path: image_path, base64: self.canvas.toDataURL( 'image/jpeg' , 0.96)}

			Essage.show({message: 'Image Uploading, Wait or keep writing...', status: 'success'}, 30000)
			$.post sync_gateway, request_data, (response_data, status)->
				if status == 'success'
					Essage.show({message: 'Image Uploaded, Done!', status: 'success'}, 5000)

			to_insert = '![Image]('+ image_path + ')\n'
			dom = $('#textarea')
			cursorPos = dom.prop('selectionStart')
			old_value = dom.val()
			text_before = old_value.substring(0,  cursorPos )
			text_after = old_value.substring(cursorPos, old_value.length)
			dom.val(text_before+to_insert+text_after)
			dom.focus()



	return this




make_textarea_center = ->
	# textarea width is 750
	# 用textarea作为主布局，可以综合body的滚动条
	textarea_width = 780
	dom = $('#textarea')
	title_dom = $('#title')

	if is_touch_device() or $(window).width() < textarea_width
		dom.css('width', '96%')
		dom.css('margin', ' 0 auto')
		title_dom.css('padding', '0')
		title_dom.css('width', '96%')
		title_dom.css('left', '2%')
	else
		padding = ($(document).width() - textarea_width)/2;
		controls = $('#controls')
		if controls.position().left == 0
			padding -= controls_width/2

		dom.css({"padding-right": padding+'px', 'width': textarea_width + padding + 'px'});
		title_dom.css({"right": padding+'px', 'width': textarea_width + 'px'})
		if $.browser.mozilla and $.browser.version and $.browser.version.indexOf('32.')!=-1 # firefox 320以前的版本有问题...
			dom.css({'width': textarea_width + 'px'})



@hide_wechat_parts = ->
	onBridgeReady = ->
		WeixinJSBridge.call('hideToolbar')
		WeixinJSBridge.call('hideOptionMenu')

	if typeof WeixinJSBridge == "undefined"
		if document.addEventListener
			document.addEventListener('WeixinJSBridgeReady', onBridgeReady, false)
		else if document.attachEvent
			document.attachEvent('WeixinJSBridgeReady', onBridgeReady)
			document.attachEvent('onWeixinJSBridgeReady', onBridgeReady)
	else
		onBridgeReady()


@run_editor = =>

	#@hide_wechat_parts()

	editor_model = new EditorModel()
	@editor = editor_model
	window.onresize = make_textarea_center

	$(document).ready ->
		text_dom = $('#textarea')
		title_dom = $('#title')

		if is_touch_device()
			$('#contorls').css('opacity', 0)
			$('#show_controls_button').css('display', 'block')

		make_textarea_center()
		ko.applyBindings(editor_model)
		editor_model.load_posts()
		editor_model.insert_image_allowed()

		text_dom.scroll ->
			if text_dom.scrollTop() > 25
				title_dom.css('display', 'none')
			else
				title_dom.css('display', 'block')

		title_dom.keyup (event)->
			editor_model.current_post().title(title_dom.val())
			if event.which == 13
				text_dom.focus()

		window.onbeforeunload = =>
			if editor_model.need_sync()
				return 'Contents not saved yet, Please wait for a moment!'
			return null

		$(window).keydown =>
			if event.which in [83,115] and (event.ctrlKey or event.metaKey)
				event.preventDefault()
				editor._sync()
				return false

			if event.which in [69,101] and (event.ctrlKey or event.metaKey)
				event.preventDefault()
				editor.toggle_controls()
				return false

		$(document).on 'input propertychange', 'textarea', =>
			editor.sync()



