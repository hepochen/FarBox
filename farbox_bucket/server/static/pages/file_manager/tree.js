(function() {
  var g,
    __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

  this.files_data = {};

  this.current_data_url = '';

  this.current_dom_to_rename = null;

  this.current_context_node = null;

  this.allowed_exts = ["jade", "js", "coffee", "scss", "sass", "less", "md", "txt", "markdown", "mk", "html", "xml", "csv", "css", "json"];

  this.stated = false;

  this.filepath_to_focus = '';

  g = this;

  this.toggle_files_manager = (function(_this) {
    return function() {
      $('.manager_body_part').toggleClass('hidden');
      if ($('.manager_body_part').hasClass('hidden')) {
        return $('.manager_editor').addClass('full_width');
      } else {
        return $('.manager_editor').removeClass('full_width');
      }
    };
  })(this);

  this.get_selected_folder = function() {
    var folder_tree, selected_folder, selected_folders;
    folder_tree = $('#folders').jstree(true);
    selected_folders = folder_tree.get_selected();
    if (selected_folders) {
      selected_folder = selected_folders[0];
    } else {
      selected_folder = '';
    }
    return selected_folder;
  };

  this.get_tree_node_id_by_folder = function(folder) {
    var folder_tree, tree_node, tree_nodes, _i, _len;
    if (!folder) {
      return null;
    }
    folder_tree = $('#folders').jstree(true);
    tree_nodes = folder_tree.get_json('#', {
      flat: true
    });
    for (_i = 0, _len = tree_nodes.length; _i < _len; _i++) {
      tree_node = tree_nodes[_i];
      if (tree_node.a_attr.path === folder) {
        return tree_node.id;
      }
    }
    return null;
  };

  this.get_tree_node_id_by_filepath = function(filepath) {
    var folder_path;
    folder_path = filepath.split('/').slice(0, -1).join('/');
    return get_tree_node_id_by_folder(folder_path);
  };

  this.get_selected_filepath = function() {
    var current_filepath;
    current_filepath = $('#files li.selected').attr('data-path');
    return current_filepath;
  };

  this.get_file_dom_by_filepath = function(filepath) {
    var matched_doms;
    if (!filepath) {
      return null;
    }
    matched_doms = $('#files li[data-path="' + filepath + '"]');
    if (matched_doms.length) {
      return $(matched_doms[0]);
    } else {
      return null;
    }
  };

  this.show_create_func = (function(_this) {
    return function(dom_id) {
      var parent_path;
      if (!_this.current_context_node) {
        return false;
      }
      parent_path = _this.current_context_node.a_attr.path || '';
      $('#' + dom_id).modal();
      $('#' + dom_id + ' input[type=text]').focus();
      $('#current_folder').val(parent_path);
      return $('#' + dom_id + ' input[name="name"]').val('');
    };
  })(this);

  this.show_rename_dialog = (function(_this) {
    return function(name, dom) {
      var name_dom;
      $('#rename').modal();
      name_dom = $('#rename input[name="name"]');
      name_dom.focus();
      name_dom.val(name);
      _this.current_dom_to_rename = dom;
      return false;
    };
  })(this);

  this.focus_iframe = function() {
    var editor;
    if ($("#container iframe").length > 0) {
      $("#container iframe").focus();
      editor = $("#container iframe")[0].contentWindow.document.getElementById("editor");
      if (editor) {
        return editor.focus();
      }
    }
  };

  this.click_file_then_open = (function(_this) {
    return function(li_dom) {
      var filepath, iframe_src, new_hash, s_file;
      if (!li_dom) {
        return false;
      }
      $('.iframe_notes').css('display', 'none');
      li_dom = $(li_dom);
      filepath = li_dom.attr('data-path').replace(/^\//g, "");
      $('li.selected').removeClass('selected');
      li_dom.addClass('selected');
      iframe_src = '/__file_view/' + filepath + location.search;
      if ($('#container iframe').attr('src') !== iframe_src) {
        $('#container iframe').attr('src', iframe_src);
      }
      s_file = get_selected_filepath();
      new_hash = '#' + s_file;
      return window.location.hash = new_hash;
    };
  })(this);

  this.when_files_loaded = function() {
    var file_dom;
    if (filepath_to_focus) {
      file_dom = get_file_dom_by_filepath(filepath_to_focus);
      if (file_dom) {
        return click_file_then_open(file_dom);
      }
    }
  };

  this.init_select_folder = function() {
    var filepath, folder_node_id, folder_tree, hash_name;
    hash_name = window.location.hash.slice(1);
    if (hash_name) {
      filepath = decodeURI(hash_name);
      folder_node_id = get_tree_node_id_by_filepath(filepath);
      g.filepath_to_focus = filepath;
      folder_tree = $('#folders').jstree(true);
      if (folder_tree.select_node(folder_node_id) !== void 0) {
        return folder_tree.select_node('j1_1');
      }
    }
  };

  this.display_files_by_click_folder = (function(_this) {
    return function() {
      var files, files_dom, html;
      if (!_this.current_data_url) {
        return false;
      }
      if (!(_this.current_data_url in _this.files_data)) {
        return false;
      }
      files_dom = $('#files');
      files = _this.files_data[_this.current_data_url];
      if (!files.length) {
        return files_dom.html('<span class="info" style="display:block;text-align:center;"> no files yet</span>');
      }
      html = '<ul>';
      $.each(files, function(index, file_obj) {
        var filename, filepath, path_parts;
        filepath = file_obj.real_path || file_obj.path;
        path_parts = filepath.split('/');
        filename = path_parts[path_parts.length - 1];
        return html += '<li data-path="' + filepath + '">' + filename + '</a></li>';
      });
      files_dom.html(html);
      $('#files li').on('click', function() {
        return g.click_file_then_open(this);
      });
      return when_files_loaded();
    };
  })(this);

  this.folder_context_menu_items = (function(_this) {
    return function(node) {
      var delete_item, items, node_text;
      _this.current_context_node = node;
      node_text = node.text;
      items = {
        create_item: {
          label: "Create File",
          action: function() {
            return _this.show_create_func('new_file');
          }
        },
        create_folder_item: {
          label: "Create Folder",
          action: function() {
            return _this.show_create_func('new_folder');
          }
        }
      };
      delete_item = {
        label: "Delete",
        action: function() {
          var folder_path;
          folder_path = _this.current_context_node.a_attr.path || '';
          if (folder_path) {
            return $.ajax({
              url: '/__file_manager_api',
              method: 'post',
              data: {
                is_dir: true,
                path: folder_path,
                is_deleted: true
              },
              success: function() {
                $('#folders').jstree().delete_node(node);
                _this.current_context_node = null;
                return $('#files').html('<span class="info" style="display:block;text-align:center;"> this folder is deleted </span>');
              }
            });
          }
        }
      };
      if (node_text !== '~') {
        items['delete_item'] = delete_item;
      }
      if ($(node).hasClass("folder")) {
        delete items.delete_item;
      }
      return items;
    };
  })(this);

  this.remove_file = (function(_this) {
    return function(filepath_to_remove) {
      var files;
      files = _this.files_data[_this.current_data_url] || [];
      return $.each(files, function(index, file_obj) {
        var file_obj_index, filepath;
        filepath = file_obj.path;
        if (filepath === filepath_to_remove) {
          file_obj_index = files.indexOf(file_obj);
          if (file_obj_index !== -1) {
            files.splice(file_obj_index, 1);
          }
          return false;
        }
      });
    };
  })(this);

  this.add_file = (function(_this) {
    return function(filepath_to_add) {
      var file_obj, files, new_path, old_file, old_path, _i, _len;
      files = _this.files_data[_this.current_data_url];
      file_obj = {
        path: filepath_to_add
      };
      if (files && files.length) {
        for (_i = 0, _len = files.length; _i < _len; _i++) {
          old_file = files[_i];
          old_path = old_file.path.replace(/^\//g, '');
          new_path = filepath_to_add.replace(/^\//g, '');
          if (old_path === new_path) {
            return;
          }
        }
        return files.push(file_obj);
      } else {
        return _this.files_data[_this.current_data_url] = [file_obj];
      }
    };
  })(this);

  this.xhr_on_ready_state_changed = function(xhr, filepath) {
    var bound_func;
    bound_func = function() {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          add_file(filepath);
          display_files_by_click_folder();
          return $('#files_info').css('display', 'none');
        } else if (xhr.status > 200) {
          return $('#files_info').css('display', 'none');
        }
      }
    };
    return bound_func;
  };

  $(document).ready((function(_this) {
    return function() {
      $.contextMenu({
        selector: '#files li',
        callback: function(key, options) {
          var current_path, dom, name;
          dom = $(this);
          current_path = dom.attr('data-path');
          if (key === 'delete') {
            $.ajax({
              url: '/__file_manager_api',
              method: 'post',
              data: {
                is_dir: false,
                path: current_path,
                is_deleted: true
              },
              success: (function(_this) {
                return function() {
                  dom.remove();
                  $('#container iframe').attr('src', '');
                  return g.remove_file(current_path);
                };
              })(this)
            });
          } else if (key === 'rename' && current_path) {
            name = $(current_path.split('/')).last();
            show_rename_dialog(name[0], dom);
          }
          return $('.contextMenu').hide();
        },
        items: {
          "delete": {
            name: "Delete"
          }
        },
        events: {
          show: function(options) {
            return g.click_file_then_open(this);
          }
        }
      });
      $('#folders').on('loaded.jstree', function() {
        return init_select_folder();
      });
      $('#folders').on('select_node.jstree', function(node, selected, event) {
        var data_url, files_dom, tree;
        data_url = selected.node.a_attr.href;
        tree = $('#folders').jstree(true);
        if (tree.is_open(selected.node)) {
          tree.close_node(selected.node);
        } else {
          tree.open_node(selected.node);
        }
        _this.current_context_node = selected.node;
        if (data_url === _this.current_data_url) {
          return false;
        } else {
          _this.current_data_url = data_url;
        }
        if (data_url in _this.files_data) {
          return display_files_by_click_folder();
        } else {
          files_dom = $('#files');
          $.ajax({
            url: data_url,
            method: 'get',
            success: function(files_got) {
              _this.files_data[data_url] = files_got;
              return _this.display_files_by_click_folder();
            }
          });
          return files_dom.html('<span class="info"> wait... </span>');
        }
      });
      $('#files').parent().on({
        drop: function(e) {
          var f, fd, file_list, filename, filepath, folder_path, xhr, _i, _len, _results;
          e.preventDefault();
          $('#files').css('border', 'none');
          if (!_this.current_context_node) {
            return false;
          }
          file_list = e.originalEvent.dataTransfer.files;
          if (file_list.length) {
            folder_path = _this.current_context_node.a_attr.path || '';
            $('#files_info').css('display', 'block');
            _results = [];
            for (_i = 0, _len = file_list.length; _i < _len; _i++) {
              f = file_list[_i];
              filename = f.name;
              filepath = folder_path + '/' + filename;
              xhr = new XMLHttpRequest();
              xhr.onreadystatechange = xhr_on_ready_state_changed(xhr, filepath);
              xhr.open("post", '/__file_manager_api', true);
              fd = new FormData();
              fd.append(filepath, f);
              _results.push(xhr.send(fd));
            }
            return _results;
          }
        },
        dragleave: function(e) {
          e.preventDefault();
          return $('#files').css('border', 'none');
        },
        dragenter: function(e) {
          e.preventDefault();
          if (!_this.current_context_node) {
            return false;
          }
          return $('#files').css('border', '1px solid indianred');
        },
        dragover: function(e) {
          e.preventDefault();
          if (!_this.current_context_node) {
            return false;
          }
          return $('#files').css('border', '1px solid indianred');
        }
      });
      $('#new_file button[type=submit]').click(function() {
        var current_folder, ext, filename, filepath;
        current_folder = $('#current_folder').val();
        if (current_folder == null) {
          return false;
        }
        filename = $.trim($('#new_file input[name="name"]').val()) || '';
        if (filename.indexOf('.') === -1) {
          filename = filename + '.txt';
        }
        filepath = current_folder + '/' + filename;
        ext = filename.split('.').pop();
        if (__indexOf.call(_this.allowed_exts, ext) < 0 || filename.indexOf('/') !== -1) {
          $('#new_file input[type=text]').focus();
          $('#new_file h2').text("not allowed file type");
          return false;
        }
        _this.add_file(filepath);
        _this.display_files_by_click_folder();
        _this.click_file_then_open($('#files li').last(), filepath);
        $.modal.close();
        return false;
      });
      $('#new_folder button[type=submit]').click(function() {
        var current_folder, folder_name, folder_path;
        current_folder = $('#current_folder').val();
        if (current_folder == null) {
          return false;
        }
        folder_name = $.trim($('#new_folder input[name="name"]').val()) || '';
        if (current_folder) {
          folder_path = current_folder + '/' + folder_name;
        } else {
          folder_path = folder_name;
        }
        if (folder_name.indexOf('/') !== -1) {
          $('#new_folder input[type=text]').focus();
          return false;
        }
        $.ajax({
          url: '/__file_manager_api',
          method: 'post',
          data: {
            is_dir: true,
            path: folder_path
          },
          success: function(doc) {
            var parent_id, tree;
            doc['title'] = folder_name;
            doc['text'] = folder_name;
            doc['a_attr'] = {
              href: "/__file_info/" + folder_path + location.search,
              path: folder_path
            };
            tree = $('#folders').jstree(true);
            parent_id = _this.current_context_node.id;
            if (parent_id === 'j1_1') {
              parent_id = '#';
            }
            tree.create_node(parent_id, doc);
            tree.open_node(_this.current_context_node);
            return $.modal.close();
          },
          error: function(error_data) {
            var error_obj;
            error_obj = error_data.responseJSON || error_data.responseText;
            if (typeof error_obj === 'string') {
              return error_obj = JSON.parse(error_obj);
            }
          }
        });
        return false;
      });
      return $(window).keydown(function() {
        var _ref;
        if (((_ref = event.which) === 69 || _ref === 101) && (event.ctrlKey || event.metaKey)) {
          event.preventDefault();
          _this.toggle_files_manager();
          return false;
        } else {
          return true;
        }
      });
    };
  })(this));

}).call(this);