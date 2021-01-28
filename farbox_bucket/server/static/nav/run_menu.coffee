@run_menu = =>
	$('.farbox_nav .sm').smartmenus
		markCurrentItem: true,
		subMenusSubOffsetX: 1,
		subMenusSubOffsetY: -8

	$('.farbox_nav').each ->
		nav_dom = $(this)
		pre_dom = nav_dom.prev()
		if not pre_dom.hasClass('menu_toggle')
			return false
		menu = pre_dom.find('.menu_state')
		if menu.length
			menu.change (e)->
				if this.checked
					nav_dom.hide().slideDown 250, ->
						nav_dom.css('display', 'block')
					nav_dom.find('.site_nav_wrap').css('padding-right', '40px')
				else
					nav_dom.show().slideUp 250, ->
						nav_dom.css('display', '')
					nav_dom.find('.site_nav_wrap').css('padding-right', '0')


$(document).ready ->
	try run_menu()
