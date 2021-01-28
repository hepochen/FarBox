this.connect_to_ws_by_listen_files = (function(_this) {
  return function(ws_url, callback_func) {
    var connect_to_server, keep_live, socket, ws_protocol;
    if (typeof callback_func === 'string') {
      if (callback_func !== 'reload') {
        callback_func = window[callback_func];
      }
    }
    callback_func = callback_func || window['listen_files_callback'];
    if ((typeof WebSocket !== "undefined" && WebSocket !== null) && (typeof JSON !== "undefined" && JSON !== null)) {
      if (document.location.protocol === 'https:') {
        ws_protocol = 'wss:';
      } else {
        ws_protocol = 'ws:';
      }
      ws_url = ws_protocol + ws_url;
      socket = null;
      connect_to_server = function() {
        var connected_at;
        socket = new WebSocket(ws_url);
        connected_at = new Date();
        socket.onmessage = function(message) {
          var note;
          note = JSON.parse(message.data);
          if (callback_func === 'reload') {
            if (window.location.href.indexOf('/service/') === -1 && window.location.href.indexOf('/system/') === -1) {
              window.location.reload();
            }
            return;
          }
          if (callback_func) {
            try {
              return callback_func(note);
            } catch (_error) {
              try {
                return callback_func();
              } catch (_error) {}
            }
          }
        };
        return socket.onclose = function() {
          if ((new Date() - connected_at) / 1000 > 10) {
            return connect_to_server();
          }
        };
      };
      keep_live = function() {
        if (socket) {
          return socket.send('ping');
        }
      };
      connect_to_server();
      return setInterval(keep_live, 60000);
    }
  };
})(this);