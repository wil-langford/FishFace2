$(document).ready(function(){
    var cq_util = window.ff.cq_util;

    function repopulate_fields(data, textStatus, jqXHR) {
        var temp_xp_id = data.xp_id;
        if (temp_xp_id != undefined && data.current_job != undefined) {
            $('#xp_display_wrapper').attr('data-xp_id', temp_xp_id);
        }

        var repop_xp_id = check_xp_id();

        if (repop_xp_id != false) {
            $('#capturejob_queue_wrapper').css('display', 'block');

            if (data.current_job != undefined) {
                var cj = data.current_job;
                $('#current_job_wrapper').css('display', 'block');
                $('#current_job_status').html(cj.status);
                $('#current_job_remaining_total').html(cj.remaining + "/" + cj.total);
                $('#current_job_psu_setting').html(cj.voltage + "V with a maximum of " + cj.current + "A");
                $('#current_job_seconds_left').html("" + cj.seconds_left);

                var slug = '';
                if (cj.cjr_id != undefined) {slug = '(XP_' + cj.xp_id + "_CJR_" + cj.cjr_id + ')'}
                $('#current_job_slug').html(slug);

                window.fishface_push_queue_on_update = true;

                start_periodic_monitor();
            } else {
                window.fishface_push_queue_on_update = false;
                $('#current_job_wrapper').css('display', 'none');
                $('#go_button').css('background-color', '');
                if (data.staged_job == undefined) { stop_periodic_monitor(); }
            }

            if (data.staged_job != undefined) {
                var sj = data.staged_job;
                $('#staged_job_wrapper').css('display', 'block');
                $('#staged_job_status').html(sj.status);
                $('#staged_job_psu_setting').html(
                    sj.voltage + "V with a maximum of " + sj.current + "A"
                );
            } else {
                $('#staged_job_wrapper').css('display', 'none');
            }

            if (data.queue.length > 0 && repop_xp_id) {
                var cjq = $('#capture_job_queue');
                cjq.empty();
                var dq = data.queue;
                for (var i in data.queue) {
                    var job_spec = dq[i];
                    cjq.append(cq_util.cjt_li_chunk_from_job_spec(job_spec));
                }
                $('#queue_placeholder').remove();
            } else {
                $('#capture_job_queue').html('<li id="queue_placeholder">No queued jobs.</li>');
            }

        }
    }

    function change_experiment() {
        if ($('#current_job_wrapper').css('display') == 'none') {
            $('#xp_display_wrapper').attr('data-xp_id', '');
            check_xp_id();
        } else {
            $('#xp_display_wrapper').append(
                '<div id="no_change_during_run" class="bad boxed">Can\'t' +
                ' change experiments while job is running.</div>');

                window.setTimeout(
                    function() {$('#no_change_during_run').remove();},
                    3000
            );
        }
    }

    function get_xp_id() {
        var get_xp_id = $('#xp_display_wrapper').attr('data-xp_id');
        if (get_xp_id == "") { return false; } else { return get_xp_id; }
    }

    function check_xp_id() {
        var check_xp_id = get_xp_id();
        if (check_xp_id != "" && check_xp_id != 'false') {
            $('#capturejob_queue_wrapper').css('display', 'block');
            $('#xp_id_header').html(window.ff.xp_names[check_xp_id]);
            $('#xp_display_wrapper').css('display', 'block');
            $('#xp_select_wrapper').css('display', 'none');
        } else {
            $('#capturejob_queue_wrapper').css('display', 'none');
            $('#xp_display_wrapper').css('display', 'none');
            $('#xp_select_wrapper').css('display', 'block');
            check_xp_id = false;
        }
        return check_xp_id;
    }

    function start_queue() {
        $('#go_button').css('background-color', 'green');

        push_entire_queue_to_raspi();
    }

    function push_entire_queue_to_raspi() {
        queue_array = cq_util.get_queue_array();
        if (queue_array != []) {
            xp_id = get_xp_id();
            window.ff.send_to_raspi({
                'command': 'set_queue',
                'queue': JSON.stringify(queue_array),
                'xp_id': xp_id,
                'species': window.ff.xp_species[xp_id]
            }, repop_in_milliseconds(1000))
        }
    }

    window.ff.cq_util.clear_queue = function() {
        var xp_id = get_xp_id();
        window.ff.send_to_raspi({
            'command': 'set_queue',
            'queue': JSON.stringify([]),
            'xp_id': xp_id,
            'species': window.ff.xp_species[xp_id]
        }, repop_in_milliseconds(1000))
    };

    function repop() {
        window.ff.send_to_raspi({'command': 'job_status'}, repopulate_fields);
    }

    function repop_in_milliseconds(msec) {
        window.setTimeout(repop, msec);
        return function() {};
    }

    function pause_queue() {
        window.ff.send_to_raspi({'command': 'pause_queue'}, repop_in_milliseconds(1000))
    }

    function abort_all() {
        window.ff.send_to_raspi({'command': 'abort_all'}, repop_in_milliseconds(2000))
    }

    function start_periodic_monitor() {
        if (window.fishface_monitoring == false) {
            window.fishface_update_loop = window.setInterval(
                    function () {  // executed once every 500 ms to request fresh data
                        repop();
                    }, 500);
            window.fishface_monitoring = true;
        }
    }

    function stop_periodic_monitor() {
        clearInterval(window.fishface_update_loop);
        window.fishface_monitoring = false;
    }

    // Bind functions to events

    $('#change_xp_button').click(change_experiment);

    $('#go_button').click(start_queue);
    $('#clear_queue_button').click(cq_util.clear_queue);
    $('#abort_all_button').click(abort_all);

    $('#refresh_button').click(repop);
    $('#monitor_button').click(start_periodic_monitor);
    $('#monitor_stop_button').click(stop_periodic_monitor);

    $('#cjq_list').on('click', '.queue_loader', function() {
        if (cq_util.get_queue_array().length == 0) {
            cq_util.load_queue($(this)[0].id.split('_')[1]);
        }
    });

    $('#xp_select_form').submit(function() {
        var xp_id = +$('input[name=xp]:checked').val();
        $('#xp_display_wrapper').attr('data-xp_id', xp_id);
        check_xp_id();
        repop();
        return false;
    });

    /*
     * Add some jQuery UI magic
     */

    $('#capture_job_queue').sortable({
        tolerance: 'pointer',
        cursor: 'pointer',
        revert: false,
        dropOnEmpty: true,

        start: function(event, ui) {
            stop_periodic_monitor()
        },

        over: function(event, ui) {
            keep_job_in_queue = 1;
        },

        out: function(event, ui) {
            keep_job_in_queue = 0;
        },

        update: function(event, ui) {
            $('#queue_placeholder').remove();

            if (window.fishface_push_queue_on_update == true) {
                push_entire_queue_to_raspi();
                repop();
                start_periodic_monitor();
            }

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

                if (cq_util.get_queue_array().length == 0) {
                    cq_util.no_jobs_placeholder();
                }
                if (window.fishface_push_queue_on_update == true) {
                    push_entire_queue_to_raspi();
                    repop();
                    start_periodic_monitor();
                }
            } else {
                newItem = ui.item;
                attrib_job_spec = ui.helper.attr('data-attrib_job_spec');
            }
        },
        receive: function(event, ui) {
            $(newItem).attr('data-attrib_job_spec', attrib_job_spec);
            keep_job_in_queue = 1;
        },
        placeholder: "ui_sortable_placeholder"
    });

    // Executable stuff
    date_format = 'YYYY-MM-DD HH:mm:ss.SSZZ';

    window.fishface_monitoring = false;

    $("#xp_select_form input:radio:last").attr('checked', true);

    repop();

    cq_util.refresh_queues();

    var main_loop = window.setInterval(
        function() {  // executed once per second to update displays with timers

        }, 1000);

});  // End of document.ready()