// Generated by CoffeeScript 1.8.0
(function() {
  var ends_with, update_change, update_css,
    __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

  ends_with = function(str, suffix) {
    return str.indexOf(suffix, str.length - suffix.length) !== -1;
  };

  update_change = function(path) {
    var css_exts, ext, parts, _ref;
    if (!path) {
      return;
    }
    parts = path.split(/\./);
    ext = parts[parts.length - 1];
    css_exts = ['css', 'scss', 'sass', 'less'];
    if (__indexOf.call(css_exts, ext) >= 0) {
      return update_css(path);
    } else {
      if ((_ref = document.activeElement.type) === 'textarea' || _ref === 'text') {
        return false;
      }
      if ((typeof no_reload !== "undefined" && no_reload !== null) && no_reload) {
        return false;
      }
      return location.reload();
    }
  };

  update_css = function(path) {
    var href, href_path, link, _i, _len, _ref;
    _ref = document.getElementsByTagName('link');
    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
      link = _ref[_i];
      href = link.href || '';
      href_path = href.split('?')[0].toLowerCase();
      href_path = href_path.replace(/^\/t\//, '/template/');
      if (ends_with(href_path, path)) {
        href = href.replace(/[?&]changed=.*?$/, '');
        if (href.indexOf('?') === -1) {
          href = href + '?changed=' + Math.random();
        } else {
          href = href + '&changed=' + Math.random();
        }
        link.href = href;
        break;
      }
    }
    return false;
  };

  this.listen_files_callback = function(note) {
      var filepaths, path, _i, _len, _results;
      filepaths = note.changed_filepaths || [];
      _results = [];
      for (_i = 0, _len = filepaths.length; _i < _len; _i++) {
        path = filepaths[_i];
        _results.push(update_change(path));
      }
      return _results;
    };

}).call(this);
