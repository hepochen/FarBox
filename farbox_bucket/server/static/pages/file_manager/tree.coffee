@files_data = {}
@current_data_url = ''
@current_dom_to_rename = null
@current_context_node = null
@allowed_exts = ["jade", "js", "coffee", "scss", "sass", "less", "md", "txt", "markdown", "mk", "html", "xml", "csv", "css", "json"]
@stated = false
@filepath_to_focus = ''
g = this

@toggle_files_manager = =>
	$('.manager_body_part').toggleClass('hidden')
	if $('.manager_body_part').hasClass('hidden')
		$('.manager_editor').addClass('full_width')
	else
		$('.manager_editor').removeClass('full_width')


@get_selected_folder = ->
	folder_tree = $('#folders').jstree(true)
	selected_folders = folder_tree.get_selected()
	if selected_folders
		selected_folder = selected_folders[0]
	else
		selected_folder = ''
	return selected_folder

@get_tree_node_id_by_folder = (folder)->
	if not folder
		return null
	folder_tree = $('#folders').jstree(true)
	tree_nodes = folder_tree.get_json('#', {flat:true})
	for tree_node in tree_nodes
		if tree_node.a_attr.path==folder
			return tree_node.id
	return null


@get_tree_node_id_by_filepath = (filepath)->
	folder_path = filepath.split('/').slice(0,-1).join('/')
	return get_tree_node_id_by_folder(folder_path)



@get_selected_filepath = ->
	current_filepath = $('#files li.selected').attr('data-path')
	return current_filepath


@get_file_dom_by_filepath = (filepath)->
	if not filepath
		return null
	matched_doms = $('#files li[data-path="'+filepath+'"]')
	if matched_doms.length
		return $(matched_doms[0])
	else
		return null



@show_create_func = (dom_id)=>
	if not @current_context_node
		return false
	parent_path = @current_context_node.a_attr.path or ''
	$('#'+dom_id).modal()
	$('#'+dom_id+ ' input[type=text]').focus()
	$('#current_folder').val(parent_path)
	$('#'+dom_id+' input[name="name"]').val('')


@show_rename_dialog = (name, dom)=>
	$('#rename').modal()
	name_dom = $('#rename input[name="name"]')
	name_dom.focus()
	name_dom.val(name)
	@current_dom_to_rename = dom
	return false

@focus_iframe = ->
  if $("#container iframe").length > 0
    $("#container iframe").focus()
    editor = $("#container iframe")[0].contentWindow.document.getElementById("editor")
    if editor
      editor.focus()

@click_file_then_open = (li_dom) =>
	if not li_dom
		return false
	$('.iframe_notes').css('display', 'none')
	li_dom = $(li_dom)
	filepath = li_dom.attr('data-path').replace(/^\//g, "")
	$('li.selected').removeClass('selected')
	li_dom.addClass('selected')
	iframe_src = '/__file_view/'+filepath+location.search
	if $('#container iframe').attr('src') != iframe_src
		$('#container iframe').attr('src', iframe_src)

	s_file = get_selected_filepath()
	new_hash = '#'+s_file
	window.location.hash = new_hash


@when_files_loaded = ->
	if filepath_to_focus
		file_dom = get_file_dom_by_filepath(filepath_to_focus)
		if file_dom
			return click_file_then_open(file_dom)

			# file_doms = $('#files li')
			# if file_doms.length
			#	return click_file_then_open(file_doms[0])


@init_select_folder = ->
	hash_name = window.location.hash.slice(1)
	if hash_name
		filepath = decodeURI(hash_name)
		folder_node_id = get_tree_node_id_by_filepath(filepath)
		g.filepath_to_focus = filepath
		folder_tree = $('#folders').jstree(true)
		if folder_tree.select_node(folder_node_id) != undefined
			folder_tree.select_node('j1_1')


@display_files_by_click_folder = =>
	if not @current_data_url
		return false
	if @current_data_url not of @files_data
		return false
	files_dom = $('#files')
	files = @files_data[@current_data_url];
	if not files.length
		return files_dom.html('<span class="info" style="display:block;text-align:center;"> no files yet</span>')
	html = '<ul>'
	$.each files, (index, file_obj)=>
		# 全小写
		filepath = file_obj.real_path or file_obj.path
		path_parts = filepath.split('/')
		filename = path_parts[path_parts.length-1]
		html += '<li data-path="'+filepath+'">' + filename + '</a></li>'
	files_dom.html(html)
	$('#files li').on 'click', ->
		g.click_file_then_open(this)

	when_files_loaded()

@folder_context_menu_items = (node)=>
	@current_context_node = node
	node_text = node.text
	items =
		create_item:
			label: "Create File",
			action: =>
				@show_create_func('new_file')

		create_folder_item:
			label: "Create Folder",
			action: =>
				@show_create_func('new_folder')

	delete_item =
		label: "Delete",
		action: =>
			folder_path = @current_context_node.a_attr.path or ''
			if folder_path
				$.ajax
					url: '/__file_manager_api',
					method: 'post',
					data: {is_dir: true,  path:folder_path, is_deleted:true},
					success: =>
						$('#folders').jstree().delete_node(node)
						@current_context_node = null
						$('#files').html('<span class="info" style="display:block;text-align:center;"> this folder is deleted </span>')
	if node_text != '~'
		items['delete_item'] = delete_item

	if $(node).hasClass("folder")
		## Delete the "delete" menu item
		delete items.delete_item

	return items



@remove_file = (filepath_to_remove)=>
	files = @files_data[@current_data_url] or []
	$.each files, (index, file_obj)=>
		filepath = file_obj.path
		if filepath == filepath_to_remove
			file_obj_index = files.indexOf(file_obj)
			if file_obj_index != -1
				files.splice(file_obj_index, 1)
			return false

@add_file = (filepath_to_add)=>
	files = @files_data[@current_data_url]
	file_obj = {path: filepath_to_add}

	if files and files.length
		for old_file in files
			old_path = old_file.path.replace(/^\//g, '')
			new_path = filepath_to_add.replace(/^\//g, '')
			if old_path == new_path
				# ignore
				return
		files.push(file_obj)
	else
		@files_data[@current_data_url] = [file_obj]



@xhr_on_ready_state_changed = (xhr, filepath)->
	bound_func = ->
		if xhr.readyState == 4 # loaded
			if xhr.status == 200 # ok
				#console.log('upload finished')
				add_file(filepath)
				display_files_by_click_folder()
				$('#files_info').css('display', 'none')
			else if xhr.status > 200
				$('#files_info').css('display', 'none')
	return bound_func

$(document).ready =>

	# 处理文件列表的右键
	$.contextMenu
		selector: '#files li'
		callback: (key, options)->
			dom = $(this)
			current_path = dom.attr('data-path')
			if key == 'delete'
				$.ajax
					url: '/__file_manager_api',
					method: 'post',
					data: {is_dir: false,  path:current_path, is_deleted:true},
					success: =>
						dom.remove()
						$('#container iframe').attr('src', '')
						g.remove_file(current_path)
			else if key == 'rename' and current_path
				name = $(current_path.split('/')).last()
				show_rename_dialog(name[0], dom)
			$('.contextMenu').hide()
		items:
			delete:
				name: "Delete"
		events:
			show: (options)->
				g.click_file_then_open(this)

	$('#folders').on 'loaded.jstree', ->
		init_select_folder()

	$('#folders').on 'select_node.jstree', (node, selected, event)=>
		data_url = selected.node.a_attr.href

		tree = $('#folders').jstree(true)
		if tree.is_open(selected.node)
			tree.close_node(selected.node)
		else
			tree.open_node(selected.node)
		@current_context_node = selected.node
		if data_url == @current_data_url
			return false
		else
			@current_data_url = data_url

		if data_url of @files_data
			display_files_by_click_folder()
		else
			files_dom = $('#files')
			$.ajax
				url: data_url,
				method: 'get',
				success: (files_got)=>
					@files_data[data_url] = files_got
					@display_files_by_click_folder()
			files_dom.html('<span class="info"> wait... </span>')


	$('#files').parent().on
		drop: (e)=>
			e.preventDefault()
			$('#files').css('border', 'none')
			if not @current_context_node # not selected
				return false
			file_list = e.originalEvent.dataTransfer.files
			if file_list.length
				folder_path = @current_context_node.a_attr.path or ''
				$('#files_info').css('display', 'block')
				for f in file_list
					filename = f.name
					filepath = folder_path+'/'+filename
					xhr = new XMLHttpRequest()
					xhr.onreadystatechange = xhr_on_ready_state_changed(xhr, filepath)
					xhr.open("post", '/__file_manager_api', true)
					fd = new FormData();
					fd.append(filepath, f)
					xhr.send(fd)
		dragleave: (e)=>
			e.preventDefault()
			$('#files').css('border', 'none')
		dragenter: (e)=>
			e.preventDefault()
			if not @current_context_node # not selected
				return false
			$('#files').css('border', '1px solid indianred')
		dragover: (e)=>
			e.preventDefault()
			if not @current_context_node # not selected
				return false
			$('#files').css('border', '1px solid indianred')


	# 创建新文件
	$('#new_file button[type=submit]').click =>
		current_folder = $('#current_folder').val()
		if not current_folder?
			return false
		filename = $.trim($('#new_file input[name="name"]').val()) or ''
		if filename.indexOf('.') == -1
			filename = filename+'.txt'
		filepath = current_folder+'/'+filename
		ext = filename.split('.').pop()
		if ext not in @allowed_exts or filename.indexOf('/')!=-1
			$('#new_file input[type=text]').focus()
			$('#new_file h2').text("not allowed file type")
			return false
		@add_file(filepath)
		@display_files_by_click_folder()
		@click_file_then_open($('#files li').last(), filepath)
		$.modal.close()
		return false

	# 创建新文件夹
	$('#new_folder button[type=submit]').click =>
		current_folder = $('#current_folder').val()
		if not current_folder?
			return false
		folder_name = $.trim($('#new_folder input[name="name"]').val()) or ''
		if current_folder
			folder_path = current_folder+'/'+folder_name
		else
			folder_path = folder_name
		if folder_name.indexOf('/')!=-1
			$('#new_folder input[type=text]').focus()
			return false

		$.ajax(
			url: '/__file_manager_api',
			method: 'post',
			data: {is_dir: true,  path:folder_path},
			success: (doc)=>
				doc['title'] = folder_name
				doc['text'] = folder_name
				doc['a_attr'] =
					href: "/__file_info/" + folder_path + location.search
					path: folder_path
				tree = $('#folders').jstree(true)
				parent_id = @current_context_node.id
				if parent_id == 'j1_1'
					parent_id = '#'
				tree.create_node(parent_id, doc)

				tree.open_node(@current_context_node)
				$.modal.close()
			error: (error_data)->
				error_obj = error_data.responseJSON or error_data.responseText
				if typeof(error_obj)== 'string'
					error_obj=JSON.parse(error_obj)
				# console.log(error_obj)
		)

		# finally
		return false


	$(window).keydown =>
		if event.which in [69,101] and (event.ctrlKey or event.metaKey)
			event.preventDefault()
			@toggle_files_manager()
			return false
		else
			return true



