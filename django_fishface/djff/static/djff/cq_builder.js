$(document).ready(function(){
    function data_attrib_from_job_spec(job_spec) {
        return job_spec.voltage + "_" +
               job_spec.current + "_" +
               job_spec.startup_delay + "_" +
               job_spec.interval + "_" +
               job_spec.duration;
    }

    function job_spec_from_data_attrib(data_attrib) {
        var job_spec_array = data_attrib.split("_");
        var job_spec = {
            voltage: job_spec_array[0],
            current: job_spec_array[1],
            startup_delay: job_spec_array[2],
            interval: job_spec_array[3],
            duration: job_spec_array[4]
        };

        return job_spec;
    }


    function li_from_job_spec(job_spec) {
        return '<li class="job_queue_item" data-attrib_job_spec=' + data_attrib_from_job_spec(job_spec) + '>' +
               inner_li_from_job_spec(job_spec) +
               '</li>';
    }

    function inner_li_from_job_spec(job_spec) {
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
    }

    function get_queue_array() {
        var queue_attrib_array = $('#capture_queue_builder').sortable('toArray', {'attribute': 'data-attrib_job_spec'});
        var queue_array = [];
        for (var i in queue_attrib_array) {
            if (queue_attrib_array[i].length > 0) {
                queue_array.push(job_spec_from_data_attrib(queue_attrib_array[i]));
            }
        }
        if (queue_array.length > 0) {
            return queue_array;
        } else {
            return [];
        }
    }

    function clear_queue() {
        no_jobs_placeholder();
    }

    function no_jobs_placeholder() {
        if (get_queue_array().length == 0) {
            $('#capture_queue_builder').html(
                '<li id="queue_placeholder">No queued jobs.</li>'
            );

        }
    }

    /*
     * Add some jQuery UI magic
     */

    $('#capture_queue_builder').sortable({
        tolerance: 'pointer',
        cursor: 'pointer',
        revert: false,
        dropOnEmpty: true,
        cancel: "#queue_placeholder",
        placeholder: "ui_sortable_placeholder",

        start: function(event, ui) {
        },

        over: function(event, ui) {
            keep_job_in_queue = 1;
        },

        out: function(event, ui) {
            keep_job_in_queue = 0;
        },

        update: function(event, ui) {
            $('#queue_placeholder').remove();
            no_jobs_placeholder();
        },
        stop: function(event, ui) {
            if (ui.item.hasClass("fresh_cjt")) {
                ui.item.removeClass("fresh_cjt");
                ui.item.addClass("job_queue_item");
            }
        },
        beforeStop: function(event, ui) {
            if (keep_job_in_queue == 0) {
                ui.item.remove();
                no_jobs_placeholder();
            } else {
                newItem = ui.item;
                attrib_job_spec = ui.helper.attr('data-attrib_job_spec');
            }
        },
        receive: function(event, ui) {
            $(newItem).attr('data-attrib_job_spec', attrib_job_spec);
            keep_job_in_queue = 1;
        }
    });

    $(".fresh_cjt").draggable({
        connectToSortable: "#capture_queue_builder",
        helper: "clone",
        revert: false
    });

    /*
     * Bind functions to UI events.
     */

    $('#clear_queue_button').click(clear_queue);

    $("#save_queue_button").click(function() {
        var queue_array = get_queue_array();

        if (queue_array.length > 0 || window.ff.queue_id != '') {

            var queue_name = $('input#queue_name').val();
            var queue_comment = $('textarea#queue_comment').val();
            queue_name = queue_name == undefined? '': queue_name;
            queue_comment = queue_comment == undefined? '': queue_comment;

            if (queue_name == '') {
                console.log('no name!');
                return false;
            }

            var payload = {
                cq_id: window.ff.cq_id,
                name: queue_name,
                queue: queue_array,
                comment: queue_comment
            };

            console.log(payload);

            $.ajax({
                type: 'POST',
                url: window.ff.cq_saver_url,  // set by inline javascript on the main page
                data: { payload_json: JSON.stringify(payload) },
                success: function (data, status, jqXHR) {
                    if (data.cq_id > 0) {
                        window.ff.cq_id = data.cq_id;
                        $('input#queue_name').val(data.name);
                        $('textarea#queue_comment').val(data.comment);

                    }
                },
                error: function(jqXHR, status, error) {

                },
                dataType: 'json'
            });
        }
    });

    // Executable stuff
    date_format = 'YYYY-MM-DD HH:mm:ss.SSZZ';

    for (idx in window.ff.cjt_ids) {
        var cjt_id = window.ff.cjt_ids[idx];
        var cjt = $('#CJT_' + cjt_id);
        cjt.attr('data-attrib_job_spec', data_attrib_from_job_spec(window.ff.job_specs[cjt_id]));
        cjt.html(inner_li_from_job_spec(window.ff.job_specs[cjt_id]));
    }

    var main_loop = window.setInterval(
        function() {  // executed once per second to update displays with timers

        }, 1000);

});  // End of document.ready()