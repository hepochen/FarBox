
var markmap_obj = markmap('svg#mindmap', map_data, {
    preset: 'colorful', // or default
    linkShape: 'diagonal' // or bracket
 });


var nodes = d3.selectAll('#mindmap g.markmap-node');
var toggleHandler = nodes.on('click');
nodes.on('click', null);
nodes.selectAll('circle').on('click', toggleHandler);

d3.select('#mindmap').call(d3.behavior.zoom()).on("wheel.zoom", null);

var tip = d3.tip()
  .attr('class', 'd3-tip')
  .offset([-20, 0])
  .html(function(d) {
    if (d.html){
        return "<div class='d3_tip_header'>" + d.name + "</div><div class='d3_tip_container markdown'>" + d.html + "</div>";
    }
    else{
        return ''
    }
  })


d3.select('#mindmap').call(tip)
d3.select('body').on('click', tip.hide)

var when_click_dom = function(d){
    // console.log('click')
    // console.log(d)
    if (d.is_root){
        return
    }
    if (d.children && d.children.length){
        markmap_obj.click(d);
    }
    else if (d._children && d._children.length){
        markmap_obj.click(d);
        install_text_handler();
    }
    else{
        if (d.link){
            if (typeof(send_to_app_client) == "undefined") {
                window.open(d.link, "_blank")
            } else {
                send_to_app_client({'action': 'open_url', 'url':d.link})
            }
        }
        // console.log('click a node without children');
        // console.log(d)
    }
}

var install_text_handler = function(){
    d3.selectAll('#mindmap g.markmap-node').selectAll('text')
        .on('click', function(d) {
            when_click_dom(d)
        })
        .on('mouseover', function(d){
            var now = Date.parse( new Date());
            if (d3UpdatedAt && now-d3UpdatedAt<750) {
                return
            }
            else{
                tip.show(d)
            }
        });
    d3.selectAll('#mindmap g.markmap-node').selectAll('circle')
        .on('click', function(d) {
            when_click_dom(d)
        })

}

install_text_handler()