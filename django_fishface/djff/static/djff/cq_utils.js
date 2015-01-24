$(document).ready(function(){
    var cq_util = {};

    cq_util.data_attrib_from_job_spec = function(job_spec) {
        return job_spec.voltage + "_" +
               job_spec.current + "_" +
               job_spec.startup_delay + "_" +
               job_spec.interval + "_" +
               job_spec.duration;
    };

    cq_util.job_spec_from_data_attrib = function(data_attrib) {
        var job_spec_array = data_attrib.split("_");
        return {
            voltage: job_spec_array[0],
            current: job_spec_array[1],
            startup_delay: job_spec_array[2],
            interval: job_spec_array[3],
            duration: job_spec_array[4]
        };
    };

    cq_util.li_from_queue = function(queue) {
        var output = '<li class="saved_queue" id="CJQ_' + queue.id + '">' +
            'Name: ' + queue.name + '<br>' +
            'Description: ' + queue.comment + '<br><br>' +
            '<span class="boxed queue_loader" id="CJQ_' + queue.id + '_LOAD">&larr;load</span>';
        if (window.ff.which_template == 'cq_builder') {
            output = output + ' <span class="boxed queue_deleter" id="CJQ_' + queue.id + '_DEL">delete</span>';
        }
        output = output + '</li>';
        return output;
    };

    cq_util.li_from_job_spec = function(job_spec) {
        return '<li class="job_queue_item" data-attrib_job_spec=' + cq_util.data_attrib_from_job_spec(job_spec) + '>' +
               cq_util.inner_li_from_job_spec(job_spec) +
               '</li>';
    };

    cq_util.inner_li_from_job_spec = function(job_spec) {
        var inner_li;
        if (job_spec.interval > 0) {
            inner_li =
                'Set (' + job_spec.voltage + 'V, ' + job_spec.current + 'A), ' +
                'wait ' + job_spec.startup_delay + 's, ' +
                'then <br /> capture every ' +
                job_spec.interval + 's for ' + job_spec.duration + 's';
        } else {
            inner_li = 'Set (' + job_spec.voltage + 'V, ' + job_spec.current + 'A) ' + 'for ' + job_spec.duration + 's';
        }
        return inner_li;
    };

    cq_util.refresh_queues = function() {
        $.ajax({
            type: 'GET',
            url: window.ff.cjqs_url,  // set by inline javascript on the main page
            success: function (data, status, jqXHR) {
                window.ff.cjqs = data.cjqs;
                window.ff.cjq_ids = data.cjq_ids;
                var cjq_list = $('#cjq_list');
                if (data.cjq_ids.length > 0) {
                    cjq_list.html('');
                    for (var i in data.cjq_ids) {
                        var queue = data.cjqs[data.cjq_ids[i]];
                        cjq_list.append(cq_util.li_from_queue(queue));
                    }
                } else {
                    cjq_list.html('<li>No saved queues.</li>');
                }
                
            },
            error: function(jqXHR, status, error) {

            },
            dataType: 'json'
        });
    };

    cq_util.get_queue_array = function() {
        var queue_attrib_array = $('#capture_job_queue').sortable('toArray', {'attribute': 'data-attrib_job_spec'});
        var queue_array = [];
        for (var i in queue_attrib_array) {
            if (queue_attrib_array[i].length > 0) {
                queue_array.push(cq_util.job_spec_from_data_attrib(queue_attrib_array[i]));
            }
        }
        if (queue_array.length > 0) {
            return queue_array;
        } else {
            return [];
        }
    };

    cq_util.no_jobs_placeholder = function() {
        if (cq_util.get_queue_array().length == 0) {
            $('#capture_job_queue').html(
                '<li id="queue_placeholder">No queued jobs.</li>'
            );
        }
    };

    cq_util.load_queue = function(id) {
        if (window.ff.which_template == 'cq_builder') {
            cq_util.clear_queue();
        }
        var cjq = $('#capture_job_queue');
        cjq.html('');

        window.ff.cjq_id = id;
        var queue = window.ff.cjqs[id];
        var queue_array = queue.queue;

        $('input#queue_name').val(queue.name);
        $('textarea#queue_comment').val(queue.comment);
        for (var j in queue_array) {
            var job_spec = queue_array[j];
            cjq.append(cq_util.li_from_job_spec(job_spec));
        }
    };

    cq_util.delete_queue = function(id) {
        if (window.ff.cjq_id == id) {
            window.ff.cjq_id = 0;
        }

        var payload = {
            cjq_id: id,
            delete: 1
        };

        $.ajax({
            type: 'POST',
            url: window.ff.cjq_saver_url,  // set by inline javascript on the main page
            data: { payload_json: JSON.stringify(payload) },
            success: function (data, status, jqXHR) {
                cq_util.refresh_queues();
            },
            dataType: 'json'
        });
    };

    window.ff.cq_util = cq_util;



});  // End of document.ready()