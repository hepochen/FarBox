# coding: utf8

#coding: utf8
from __future__ import absolute_import


bucket_web_template = {
    '_route': {
        '': 'index.html',
    },
    'index.html': u"""<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en-us">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta name="renderer" content="webkit">
    <meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0" name="viewport"/>
    <meta content="yes" name="apple-mobile-web-app-capable"/>
    <meta content="black" name="apple-mobile-web-app-status-bar-style"/>
    <meta content="telephone=no" name="format-detection"/>
    <meta name="renderer" content="webkit"/>
    <title>Server Status</title>
    {{ h.load('jquery') }}
    {{ h.load('/fb_static/lib/markdown_js/echarts.min.js') }}
    {{ h.load('/fb_static/datatables/datatables.min.css') }}
    {{ h.load('/fb_static/datatables/datatables.min.js') }}
</head>
<body>
    <style type="text/css">
        body{
            font-size: 14px;
            color: #555;
            padding: 0 20px 50px 20px;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        }
        .basic_info{
            text-align: center;
        }
        .basic_info span{
            padding: 0 10px;
        }

        h1, h2, h3{
            text-align: center;
        }
        h2{
            margin-top: 60px;
            margin-bottom:20px;
        }

        table, .dataTables_wrapper{
            font-size: 12px;
        }

    </style>

    <script>
        var chart_colors = ['#18A67A','#E14B78','#3B8FBD','#FAB432','#4D79B9','#92C6AE','#AD314D','#F7A63F','#41B882','#D28268','#395DAD','#1B9FCF'];

        var show_network_status = function(date_values, recv_speed_values, send_speed_values ){
            var my_chart = echarts.init(document.getElementById('network_echart'));
            var option = {
                animation: false,
                color: chart_colors,
                tooltip : {
                    trigger: 'axis'
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },

            xAxis: {
                boundaryGap: false,
                data: date_values,
                axisLine:{
                    lineStyle:{
                        color: '#ccc'
                    }
                },
                axisLabel:{
                    color: '#555'
                },
                splitLine:{
                    lineStyle: {
                        color: '#f0f0f0'
                    }
                }
            },
            yAxis:{
                axisLine:{
                    lineStyle:{
                        color: '#ccc'
                    }
                },
                axisLabel:{
                    color: '#555'
                },
                splitLine:{
                    lineStyle: {
                        color: '#f0f0f0'
                    }
                }
            },

            legend: {
                    data: ["Send" , "Recv"]
                },
            series:[
                {
                    name: 'Send',
                    type: 'line',
                    areaStyle: {normal: {}},
                    data: send_speed_values
                },
                {
                    name: 'Recv',
                    type: 'line',
                    areaStyle: {normal: {}},
                    data: recv_speed_values
                }
            ]};
            my_chart.setOption(option);
        };

        var show_echarts_status = function(date_values, cpu_values, mem_values, disk_values, io_values, record_ids){
            var my_chart = echarts.init(document.getElementById('status_echart'));
            my_chart.on('click', function(param){
                var record_id = record_ids[param.dataIndex];
                window.location = '?icursor='+record_id;
            });
            var option = {
                animation: false,
                triggerOn: "click",
                color: chart_colors,
                tooltip : {
                    trigger: 'axis'
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },

            xAxis: {
                boundaryGap: false,
                data: date_values,
                axisLine:{
                    lineStyle:{
                        color: '#ccc'
                    }
                },
                axisLabel:{
                    color: '#555'
                },
                splitLine:{
                    lineStyle: {
                        color: '#f0f0f0'
                    }
                }
            },
            yAxis:{
                max: 100,
                axisLine:{
                    lineStyle:{
                        color: '#ccc'
                    }
                },
                axisLabel:{
                    color: '#555'
                },
                splitLine:{
                    lineStyle: {
                        color: '#f0f0f0'
                    }
                }
            },

                legend: {
                        data: ["CPU" , "Mem" , "Disk", "IO"]
                    },
                series:[
                    {
                        name: 'CPU',
                        type: 'line',
                        areaStyle: {normal: {}},
                        data: cpu_values
                    },
                    {
                        name: 'Mem',
                        type: 'line',
                        areaStyle: {normal: {}},
                        data: mem_values
                    },
                    {
                        name: 'Disk',
                        type: 'line',
                        areaStyle: {normal: {}},
                        data: disk_values
                    },
                    {
                        name: 'IO',
                        type: 'line',
                        areaStyle: {normal: {}},
                        data: io_values
                    }
                ]
            };
            my_chart.setOption(option);

        };

        var show_processes_table = function(table_data_set){
            $('#processes_table').DataTable( {
                "iDisplayLength": 100,
                data: table_data_set,
                columns: [
                        { title: "Name" },
                        { title: "Docker" },
                        { title: "Cpu" },
                        { title: "Mem" },
                        { title: "MemPercent" },
                        { title: "PID" },
                        { title: "Parent PID" },
                        { title: "Command" },
                        { title: "Read" },
                        { title: "Write" },
                        { title: "Created" }
                    ]
            });
        }

    </script>



    {% set date_values=[] %}
    {% set cpu_values=[] %}
    {% set mem_values=[] %}
    {% set disk_values=[] %}
    {% set io_values=[] %}
    {% set record_ids=[] %}
    {% set recv_speed_values=[] %}
    {% set send_speed_values=[] %}

    {% set rs = rrecords_1000 %}
    {% if rs %}
        {% set latest_record = rs[0] %}
        {% if rs|length >= 2 %} {% set oldest_record = rs[-1] %} {%endif%}
    {% endif %}

    {% for record  in rs|reverse %}
        {% do record_ids.append(record._id) %}
        {% do date_values.append((record.date or '').split(':')[:-1] | join(':')) %}
        {% do cpu_values.append(record.cpu.used or 0) %}
        {% do io_values.append(record.io.util|round or 0) %}
        {% do disk_values.append((100*record.disk.used/record.disk.total) | round) %}
        {% if record.mem.total_n %}
            {% do mem_values.append((100*record.mem.used_n/record.mem.total_n) | round) %}
        {% else %}
            {% do mem_values.append(0) %}
        {% endif %}
        {% if record.net %}
            {% set speed_info= record.net.values()[0] %}
            {%do recv_speed_values.append(speed_info.recv_speed_m or 0) %}
            {%do send_speed_values.append(speed_info.send_speed_m or 0) %}
        {% else %}
            {%do recv_speed_values.append(0) %}
            {%do send_speed_values.append(0) %}
        {% endif %}
    {% endfor %}

    {% if latest_record %}
        <h2> Basic Information (latest record)</h2>
        <div class="basic_info">
            <span>{{latest_record.date}}</span>
            <span>Disk: {{latest_record.disk.used_for_human}}/{{latest_record.disk.total_for_human}}</span>
            {% if latest_record.disk2%}
            <span>Disk2: {{latest_record.disk2.used_for_human}}/{{latest_record.disk2.total_for_human}}</span>
            {% endif %}
            <span>IO: {{latest_record.io.util|round or 0}}</span>
            <span>Mem: {{latest_record.mem.used}}/{{latest_record.mem.total}}</span>
            <span>Cpu: {{latest_record.cpu.used}}% {{latest_record.cpu.cores}} cores {{latest_record.cpu.max_freq}}hz</span>
            <span>Load: {{latest_record.load_info.load_1}} {{latest_record.load_info.load_5}} {{latest_record.load_info.load_15}} (1 5 15 mins)</span>
        </div>
        <div class="basic_info">


        </div>
    {% endif %}

    <h2> Status Percent</h2>
    <div class="md_echarts"  id="status_echart" style="width:100%;min-width: 600px;height:400px;"></div>
    <script type="text/javascript">
        show_echarts_status(
                {{date_values | tojson}},
                {{cpu_values | tojson}},
                {{mem_values | tojson}},
                {{disk_values | tojson}},
                {{io_values | tojson}},
                {{record_ids | tojson}}
        )
    </script>


    <h2> Network Speed (Mb/Second)</h2>
    <div class="md_echarts"  id="network_echart" style="width:100%;min-width: 600px;height:400px;"></div>
    <script type="text/javascript">
        show_network_status(
                {{date_values | tojson}},
                {{recv_speed_values | tojson}},
                {{send_speed_values | tojson}}
        )
    </script>



    {% if latest_record %}
        <h2> Processes (latest record)</h2>
        <table id="processes_table" class="display" width="100%"></table>
        {% set table_data_set = [] %}
        {% for p in latest_record.processes %}
            {% set table_record = [p.name, p.docker or '', p.cpu, p.mem, p.mem_percent|round, p.pid, p.ppid, p.cmd or '', p.read_bytes or 0, p.write_bytes or 0, p.created_at or ''] %}
            {% do table_data_set.append(table_record) %}
        {% endfor %}



        <script>
            $(document).ready(function() {
                show_processes_table({{ table_data_set | tojson}});
            })
        </script>

    {% endif %}


    <div class="page_info" style="margin-top:50px; margin-bottom: 50px;">
        {% if request.values.cursor or request.values.icursor%}
            <a class="home_page" href="?" style="">Home</a>
        {% endif %}
        {% if oldest_record %}
            <a class="older_page" href="?cursor={{oldest_record._id}}" style="float:right">Older Page</a>
        {% endif %}


    </div>


</body>
</html>"""
}