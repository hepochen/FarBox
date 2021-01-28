var cell_string = function(text){
    text = text.replace(/"/g, '\\"');
    text = text.replace(/\n/g, '\\n');
    if (text.indexOf(",")!=-1){
        text = '"'+text+'"'
    }
    return text
};

var get_csv_content = function() {
    var result = [];
    var head_row = [];
    $('table thead tr th').each(function(){
        head_row.push(cell_string($.trim($(this).text())))
    });
    if (head_row.length){
        result.push(head_row.join(','))
    }
    $('table tbody tr').each(function(){
        var row = [];
        $('td', this).each(function(){
                row.push(cell_string( $.trim(this.innerText || $(this).text())));
            }
        );
        result.push(row.join(','));
    });
    return result.join('\n')
};

var is_current_focused_dom_valid = function(){
    return current_focused_dom && current_focused_dom.parent().parent().length
};


var add_new_row = function(){
    var cell_length = $('table tbody tr').last().find('td').length;
    var html = '<tr>';
    for (var i=0; i<cell_length; i++){
        html += '<td contenteditable="true">&nbsp;</td>';
    }
    html += '</tr>';

    if (is_current_focused_dom_valid()){
        current_focused_dom.parent().after(html);
    }
    else{
        $('table tbody').append(html);
    }
    listen_focus_event();
};


var remove_row = function(){
    var trs = $('tbody tr');
    var rows_count = trs.length;
    if (rows_count <= 1) return false;
    if (is_current_focused_dom_valid() && !current_focused_dom.parent().parent().is('thead')){
        current_focused_dom.parent().remove();
    }
    else{
        trs.last().remove();
    }
};

var add_new_column = function(){
    var current_column_index = $('tbody tr:first-child td').length -1;
    if (is_current_focused_dom_valid()){
        current_column_index = current_focused_dom.parent().children().index(current_focused_dom);
    }
    $('table tbody tr,table thead tr').each(function(){
            var tr = $(this);
            if (tr.parent().is('thead')){
                var to_insert = '<th contenteditable="true">&nbsp;</th>'
            }
            else{
                to_insert = '<td contenteditable="true">&nbsp;</td>'
            }
            $(tr.children()[current_column_index]).after(to_insert)
     });
    listen_focus_event();
};


var delete_column = function(){
    var cell_count = $('tbody tr:first-child td').length;
    if (cell_count <=1) return false;
    var current_column_index = cell_count -1;
    if (is_current_focused_dom_valid()){
        current_column_index = current_focused_dom.parent().children().index(current_focused_dom);
    }
    $('table tbody tr,table thead tr').each(function(){
        var tr = $(this);
        $(tr.children()[current_column_index]).remove();
    });
};



var current_focused_dom;
var listen_focus_event = function(){
    var doms = $('td,th');
    doms.off('focus');
    doms.on('focus', function(){
        if (current_focused_dom){
            current_focused_dom.parent().children().removeAttr('style');
        }
        current_focused_dom=$(this);
        current_focused_dom.parent().children().css({'background':'#ffff99', 'border-top': '1px solid #eee', 'border-bottom':'1px solid #eee'});
    });
};


var save = function(){
    var info_dom = $('#info');
    var doc_path = $('#doc_path').val();
    var content = get_csv_content();
    data = {path: doc_path, raw_content:content};
    info_dom.text('uploading...');
    $.ajax({
        url: '/__file_manager_api',
        method: 'post',
        data: data,
        success: function(sync_info){
            console.log(sync_info);
            info_dom.text('');
        },
        error: function(error_data){
            var error_obj = error_data.responseJSON || error_data.responseText;
            if (typeof(error_obj)== 'string') {error_obj=JSON.parse(error_obj)}
            info_dom.text(error_obj.message);
        }
    });
};



$(document).ready(function(){
    listen_focus_event();


    $(window).keydown(function(event){
        if (event.which==13 && (event.ctrlKey || event.metaKey)){
            if (current_focused_dom && current_focused_dom.length){
                var next_dom = $(current_focused_dom).next();
                if (next_dom && next_dom.length){
                    next_dom.focus();
                }
                else{
                    // next line
                    var next_row_dom = current_focused_dom.parent().next();
                    if (next_row_dom.children().length){
                        next_dom = $(next_row_dom.children()[0]);
                        next_dom.focus();
                    }
                }
            }
            return false;
        }

        if ([83,115].indexOf(event.which) != -1 && (event.ctrlKey || event.metaKey)){
            event.preventDefault();
            save();
            return false
        }

        if ([69, 101].indexOf(event.which) != -1 && (event.ctrlKey || event.metaKey) && window.parent && window.parent.toggle_files_manager) {
          event.preventDefault();
          window.parent.toggle_files_manager();
          return false;
        }

        return true

    });

});


