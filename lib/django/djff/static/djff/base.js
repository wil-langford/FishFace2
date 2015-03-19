$(document).ready(function(){

    window.ff.celery_async = function (task_name, success_function, kwargs,
                                       result_return, result_timeout) {
        if (result_timeout == undefined) { result_timeout = 0; }
        if (result_return == undefined) { result_return = false; }
        //console.log(task_name + ', ' + result_return + ', ' + result_timeout);
        //console.log('KWARGS');
        //console.log(kwargs);
        $.ajax({
            type: 'POST',
            url: window.ff.celery_proxy_url,
            data: {
                'task_name': task_name,
                'result_return': result_return,
                'result_timeout': result_timeout,
                'kwargs': JSON.stringify(kwargs)
            },
            success: success_function,
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(
                    "ERROR:\n  textStatus: " + textStatus +
                    "\n  text: " + jqXHR.text +
                    "\n  errorThrown: " + errorThrown
                );
                return false;
            },
            dataType: 'json'
        });
    };

    window.ff.text_to_seconds = function(text_value) {
        var values = text_value.split(':');
        var multipliers = [60, 1];

        switch(values.length) {
            case 1:
                return Number(text_value);
            case 2:
                break;
            case 3:
                multipliers.unshift(60*60);
                break;
            case 4:
                multipliers.unshift(60*60);
                multipliers.unshift(24*60*60);
                break;
            default:
                return 0;
        }

        var total_seconds = 0;
        for (var idx in values) {
            var multiplier = multipliers[idx];
            total_seconds = total_seconds + (Number(values[idx]) * multiplier);
            console.log('' + Number(values[idx]) + ' * ' + multipliers[values.length] + ' ... ' + total_seconds);
        }
        return total_seconds;
    };


    function csrfSafeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
       beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader('X-CSRFToken', window.ff.csrf_token);
            }
        }
    });

    // from fearphage on StackExchange
    if (!String.prototype.format) {
      String.prototype.format = function() {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function(match, number) {
          return typeof args[number] != 'undefined'
            ? args[number]
            : match
          ;
        });
      };
    }

    // from powtac on StackExchange
    if (!String.prototype.toHHMMSS) {
        String.prototype.toHHMMSS = function () {
            var sec_num = parseInt(this, 10); // don't forget the second param
            var hours   = Math.floor(sec_num / 3600);
            var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
            var seconds = sec_num - (hours * 3600) - (minutes * 60);

            if (hours   < 10) {hours   = "0"+hours;}
            if (minutes < 10) {minutes = "0"+minutes;}
            if (seconds < 10) {seconds = "0"+seconds;}
            return hours+':'+minutes+':'+seconds;
        }
    }
});