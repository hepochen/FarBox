

waterfall = new Waterfall({
                containerSelector: '#waterfall',
                boxSelector: '.item',
                minBoxWidth: 250
            })

@auto_load_page_callback = ->
	new_items = $('#waterfall > .item')
	for item in new_items
		waterfall.addBox(item)