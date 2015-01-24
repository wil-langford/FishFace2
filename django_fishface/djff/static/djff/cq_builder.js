$(document).ready(function(){
    var cq_util = window.ff.cq_util;
    
    cq_util.clear_queue = function() {
        $('#capture_job_queue').html('');
        $('input#queue_name').val('');
        $('textarea#queue_comment').val('');
        cq_util.no_jobs_placeholder();
        window.ff.cjq_id = 0;
    }

    function delete_queue(id) {
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
    }



    /*
     * Add some jQuery UI magic
     */

    $('#capture_job_queue').sortable({
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
            cq_util.no_jobs_placeholder();
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
                cq_util.no_jobs_placeholder();
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
        connectToSortable: "#capture_job_queue",
        helper: "clone",
        revert: false
    });

    /*
     * Bind functions to UI events.
     */

    $('#cjq_list').on('click', '.queue_loader', function() {
        cq_util.load_queue($(this)[0].id.split('_')[1]);
    });

    $('#cjq_list').on('click', '.queue_deleter', function() {
        delete_queue($(this)[0].id.split('_')[1]);
    });

    $('#clear_queue_button').click(cq_util.clear_queue);

    $("#save_queue_button").click(function() {
        var queue_array = cq_util.get_queue_array();

        if (queue_array.length > 0 || window.ff.queue_id > 0) {

            var queue_name = $('input#queue_name').val();
            var queue_comment = $('textarea#queue_comment').val();
            queue_name = queue_name == undefined? '': queue_name;
            queue_comment = queue_comment == undefined? '': queue_comment;

            if (queue_name == '') {
                console.log('tried to save with no name!');
                return false;
            }

            var payload = {
                cjq_id: window.ff.cjq_id,
                name: queue_name,
                queue: queue_array,
                comment: queue_comment
            };

            $.ajax({
                type: 'POST',
                url: window.ff.cjq_saver_url,  // set by inline javascript on the main page
                data: { payload_json: JSON.stringify(payload) },
                success: function (data, status, jqXHR) {
                    if (data.cjq_id > 0) {
                        window.ff.cjq_id = data.cjq_id;
                        $('input#queue_name').val(data.name);
                        $('textarea#queue_comment').val(data.comment);

                    }

                    cq_util.refresh_queues();
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
        cjt.attr('data-attrib_job_spec', cq_util.data_attrib_from_job_spec(window.ff.job_specs[cjt_id]));
        cjt.html(cq_util.inner_li_from_job_spec(window.ff.job_specs[cjt_id]));
    }

    cq_util.refresh_queues();

    var main_loop = window.setInterval(
        function() {  // executed once per second to update displays with timers

        }, 1000);

});  // End of document.ready()