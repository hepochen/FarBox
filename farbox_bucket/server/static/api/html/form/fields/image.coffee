

@image_inited_objs = []


placeholder_image = '/drop_image_here.png'

@init_image_field = (dom)->
	img_dom = $(dom)

	if img_dom.parents('.template').length
		# ignore
		# console.log('ignore template')
		return false

	if img_dom.hasClass('inited')
		return false

	image_block_dom = img_dom.parents('.image_block')
	percent_bar_dom = image_block_dom.find('.percent_bar')
	percent_dom = image_block_dom.find('.percent')

	img_dom.addClass('inited')

	post_url = $(dom).attr("data-post-url") or '/__file_manager_api'

	filepath = $(dom).attr("data-filepath") or ''
	image_extensions = 'gif,jpg,jpeg,bmp,png'
	if filepath.indexOf('.ico') != -1
		image_extensions = 'png,ico'

	picker_dom_id = 'img_picker_'+parseInt(Math.random()*1000000000000000)
	img_dom.parent().find('.upload_image_action').attr('id', picker_dom_id)
	img_dom_id = 'img_dropper_'+parseInt(Math.random()*1000000000000000)
	img_dom.attr('id', img_dom_id)
	uploader = WebUploader.create
		dnd: '#'+img_dom_id
		server: post_url
		pick: '#'+picker_dom_id
		resize: false
		chunked: false
		compress: false
		preserveHeaders: true
		accept:
			title: 'Images'
			extensions: image_extensions
			mimeTypes: 'image/*'
		thumb:
			quality: 90
			allowMagnify: true
			crop: true
			type: 'image/jpeg'

	uploader.on 'fileQueued', (file)->
		uploader.makeThumb(file, (error, rect)->
			if not error
				img_dom.attr('src', rect)
		img_dom.width()*2, img_dom.height()*2)

		# 确定图片保存的路径

		filepath = $(dom).attr("data-filepath")
		if filepath and filepath.indexOf('/fb_static/')==0
			filepath = ''
		if filepath == placeholder_image
			filepath = ''
		else if filepath and filepath.indexOf('://') != -1
			filepath = ''

		if not filepath
			filepath = "/_images/r"+parseInt(Math.random()*1000000000000000) + '.' + file.ext
			img_dom.attr('data-filepath', filepath)

		uploader.options.server = post_url+'?path='+filepath

		uploader.upload()

	uploader.on 'uploadProgress', (file, percentage)->
		percent = percentage * 100
		percent_bar_dom.css('display', 'block')
		percent_dom.css('width', percent+'%')
	uploader.on 'uploadSuccess', (file, response)->
		percent_bar_dom.css('display', 'none')

	return true

@do_clear_image_filepath = (action_dom)->
	image_field_dom = $(action_dom).parents('.image_block')
	img_dom = image_field_dom.find('img')
	image_filepath = img_dom.attr('data-filepath')
	img_dom.attr('src', placeholder_image)
	if img_dom.attr('data-clear-is-delete') == 'yes' and image_filepath
		$.ajax
			url: '/__file_manager_api',
			method: 'post',
			data: {is_dir: false,  path:image_filepath, is_deleted:true}
	else
		# reset the data-filepath if just clear
		img_dom.attr('data-filepath', '')

@clear_image_filepath = (action_dom)->
	swal_configs =
		title: "clear it as an empty image?",
		text: "",
		type: "info",
		animation: false,
		showCancelButton: true,
		closeOnConfirm: true,
		showLoaderOnConfirm: false
	if swal?
		swal swal_configs, (do_it)->
			if do_it
				do_clear_image_filepath(action_dom)
	else
		do_clear_image_filepath(action_dom)



@init_image_fields = ->
	_form_image_doms = $('.form_image_dom:not(.inited)')
	form_image_doms = []
	for form_image_dom in _form_image_doms
		if not $(form_image_dom).parents('.template').length
			form_image_doms.push(form_image_dom)
	if not form_image_doms.length
		return false
	init_image_field(form_image_doms[0])


$(document).ready ->
	#$('.form_image_dom').hover ->
	#	init_image_field($(this))
	init_image_fields()

	$('body').on 'DOMNodeInserted', 'div', ->
		# 算是 web-uploader的bug，异步初始化，多个之后，就会混淆，one by one...
		div_dom = $(this)
		image_block_dom = div_dom.parents('.image_block')
		if image_block_dom.length and div_dom.find('input.webuploader-element-invisible').length and not image_block_dom.hasClass('finished')
			image_block_dom.addClass('finished')
			# console.log('finished then next...')
			init_image_fields()