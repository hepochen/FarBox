set_comment_error = (error)->
	$('.comment_error').css('display', 'block')
	$('.comment_error').html(error)


@refresh_verification_code = ->
	$('#verification_code_image').attr('src', '/service/verification_code?s='+Math.random())
	$('.verification_code input').val('')
	$('.verification_code input').focus()


@scroll_to_comment_form = ->
	comment_content_dom = $('#new_comment_form textarea')
	scroll_to_top_position = comment_content_dom.offset().top - 80
	if scroll_to_top_position < 0
		scroll_to_top_position = 0
	$('body,html').animate({
		  scrollTop: scroll_to_top_position
		}, 800)
	comment_content_dom.focus()

@reply_comment = (nickname, reply_to) ->
	content_dom = $('#new_comment_form textarea')
	old_content = content_dom.val() or ''
	if nickname.indexOf(' ') == -1
		to_append = '@' + nickname + ' '
	else
		to_append = '@' + nickname + ', '
	if old_content.indexOf(to_append) != -1
		to_append = ''
	new_content = old_content + to_append

	reply_to = reply_to or ''
	$('#reply_to_id').val(reply_to)

	if reply_to
		origin_comment_dom = $('#'+reply_to)
		if origin_comment_dom.length
			origin_comment_dom.append($('#new_comment_form'))

	content_dom.click()

	content_dom.val(new_content)

	scroll_to_comment_form()

	return false



$(document).ready ->
	author_dom = $('#new_comment_form input[name="author"]')
	email_dom = $('#new_comment_form input[name="email"]')
	site_dom = $('#new_comment_form input[name="site"]')
	path_dom = $('#new_comment_form input[name="path"]')
	verification_code_dom = $('#new_comment_form input[name="verification_code"]')
	content_dom = $('#new_comment_form textarea')

	$('#verification_code_image').click(refresh_verification_code)

	$(".new_comment").click ->
		if not $('#verification_code_image').attr('src')
			$('#verification_code_image').attr('src', '/service/verification_code')
		$(".comment_trigger").hide()
		# $(".new_comment textarea").css("height","auto")
		$(".comment_triggered").fadeIn("slow")

		# load information from cookie
		if author_dom.length
			author_dom.val(author_dom.val() or Cookies.get('comment_author') or '')
		if email_dom.length
			email_dom.val(email_dom.val() or Cookies.get('comment_email') or '')
		if site_dom.length
			site_dom.val(site_dom.val() or Cookies.get('comment_site') or '')


	$('.new_comment textarea').keyup (event)->
		current_height = $(this).height()
		if current_height < this.scrollHeight and current_height<350
			$(this).height(this.scrollHeight)

		# 不处于 reply 的状态
		if event.which == 27
			new_comment_form = $('#new_comment_form')
			if not new_comment_form.parent().hasClass('new_comment_form_container')
				$('.new_comment_form_container').append(new_comment_form)
				$('#reply_to_id').val('')
				scroll_to_comment_form()


	$('.comment_submit_button').click ->
		author = author_dom.val() or ''
		email = email_dom.val() or ''
		site = site_dom.val() or ''
		content = content_dom.val()
		parent_comment_id = $('#reply_to_id').val() or ''
		verification_code = verification_code_dom.val() or ''
		new_comment_form = $('#new_comment_form')
		data_to_post =
			author: author
			email: email
			site: site
			content: content
			path: path_dom.val()
			reply: parent_comment_id
			verification_code: verification_code
			return_html: true
		if verification_code.length<4
			set_comment_error('length of verification_code is 4!')
		if content.length < 5
			set_comment_error('min length of comment is 5!')
			content_dom.focus()
			return false
		if not email and email_dom.length
			set_comment_error('email is required')
			content_dom.focus()
			return false

		# set cookies
		if author
			Cookies.set('comment_author', author, { expires: 9999 })
		if email
			Cookies.set('comment_email', email, { expires: 9999 })
		if site
			Cookies.set('comment_site', site, { expires: 9999 })


		$.ajax
			url: new_comment_form.attr('action')
			type: 'post'
			data: data_to_post
			success: (data)->
				$('.comment_error').css('display', 'none')
				if data.error
					if data.error == 'verification code is error'
						refresh_verification_code()
					set_comment_error(data.error)
				else
					if typeof(data) == 'string'
						content_dom.val('') # clear the content
						if parent_comment_id and $('#'+parent_comment_id).length
							parent_comment_dom = $('#'+parent_comment_id)
							sub_comments_filter = '#'+parent_comment_id + ' ul.sub_comments'
							if not $(sub_comments_filter).length
								parent_comment_dom.append('<ul class="sub_comments"></ul>')
							sub_comments_dom = $(sub_comments_filter)
							sub_comments_dom.append(data)
							new_comment_dom = $(sub_comments_filter+' .comment').last()
							$('.new_comment_form_container').append(new_comment_form)
						else
							$('.comments').append(data)
							new_comment_dom = $('.comments .comment').last()
							$('#reply_to_id').val('')
							refresh_verification_code()

						$('html, body').animate
							scrollTop: new_comment_dom.offset().top
							, 500, 'swing', ->
								new_comment_dom.fadeIn(150).fadeOut(150).fadeIn(150)

					console.log(data)
			fail: (data)->
				console.log(data)
				console.log('failed')

		return false
