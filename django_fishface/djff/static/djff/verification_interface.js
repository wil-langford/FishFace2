/**
 * Created by wil on 12/2/14.
 */

$(document).ready(function() {

    if (window.ff == undefined) { window.ff = {}; }

    ff.HORIZONTAL_TILES = 3;
    ff.VERTICAL_TILES = 6;

    $('#change_res').click(function (event) {
        window.location.reload();
    });

    /*
     * Fabric.js code below
     */

    fabric.FFWindow = fabric.util.createClass(fabric.Canvas, {
        ffType: 'FFWindow',
        initialize: function(canvas_id, hor_tiles, vert_tiles) {
            this.callSuper('initialize', canvas_id);

            this.hor_tiles = hor_tiles;
            this.vert_tiles = vert_tiles;

            this.tile_scale_x = false;
            this.tile_scale_y = false;
        },
        add_image: function(url, data, tile_index) {
            fabric.Image.fromURL(url, this.image_added, {
                ff_window: this,
                data: data,
                tile_index: tile_index
            });
        },
        tile_coords: function(tile_index) {
            var idx = {
                x: tile_index % this.hor_tiles,
                y: (tile_index - (tile_index % this.hor_tiles)) / this.vert_tiles
            }
            var w = this.width / this.hor_tiles;
            var h = this.height / this.vert_tiles;

            return {
                x: w * idx.x + (w / 2),
                y: h * idx.y + (h / 2)
            }
        },
        image_added: function(img) {
            var wdw = img.ff_window;
            
            wdw.add(img);
            wdw.tile[img.tile_index] = img;
            wdw.tile_data[img.tile_index] = img.data;
            var orig = img.getOriginalSize()

            if (!wdw.tile_scale_x) {
                wdw.tile_scale_x = (wdw.width = orig.width) / wdw.hor_tiles;
                wdw.tile_scale_y = (wdw.height = orig.height) / wdw.vert_tiles;
            }

            var tc = this.tile_coords(img.tile_index);

            img.set({
                scaleX: wdw.tile_scale_x,
                scaleY: wdw.tile_scale_y,
                x: tc.x,
                y: tc.y
            });

            img.setCoords();
            wdw.calcOffset();
        },
        replace_image: function(url, data, tile_index) {
            fabric.Image.fromURL(url, this.image_replaced, {
                ff_window: this,
                data: data,
                tile_index: tile_index
            });
        },
        image_replaced: function(img) {
            var wdw = img.ff_window;
            img.set({
                scaleX: wdw.tile_scale_x,
                scaleY: wdw.tile_scale_y,
                x: wdw.tile[img.tile_index].x,
                y: wdw.tile[img.tile_index].y
            });
            
            wdw.tile[img.tile_index].remove();
            wdw.tile[img.tile_index] = img;
            wdw.add(wdw.tile[img.tile_index]);
            wdw.tile[img.tile_index].sendToBack();
            wdw.tile[img.tile_index].setCoords();

            wdw.calcOffset();
        }
    });
    
    //fabric.FFArrow = fabric.util.createClass({
    //    AAAffType: 'FFArrow',
    //    initialize: function (canvas) {
    //        var center = canvas.getCenter();
    //
    //        this.line = new fabric.Line([0, 0, 0, 0], {
    //            originX: 'center',
    //            originY: 'center',
    //            stroke: window.ff.ARROW_COLOR,
    //            strokeWidth: 1,
    //            selectable: false,
    //            visible: false
    //        });
    //
    //        canvas.add(this.line);
    //
    //        this.line.setCoords();
    //    }
    //});
    //

    ff.window = new fabric.FFWindow('verification_canvas');

    //over.on('mouse:down', function(options) {
    //    window.ff.OVER_MOUSE_IS_DOWN = true;
    //    var pointer = over.getPointer(options.e);
    //    var point = new fabric.Point(pointer.x, pointer.y);
    //    over.zoom_move(point);
    //    over.renderAll();
    //});

    function get_new_tags(do_post) {
        if (do_post == false) {
            $('input#tag_ids').attr('value', 'DO_NOT_POST');
            $('input#tags_verified').attr('value', 'DO_NOT_POST');
        }

        var form = $('#verification_form');
        var data = form.serialize();
        $.ajax({
            type: 'POST',
            url: ff.verification_submit_url,  // set by inline javascript on the main page
            data: data,
            success: function (data, status, jqXHR) {
                if (data != 0) {
                    $('input#tag_ids').attr('value', data.tag_ids_text);
                    $('input#tags_verified').attr('value', data.tags_verified_text);

                    console.log("got new tags: " + data.tag_ids_text);
                }
            },
            dataType: 'json'
        });

        ff.window.renderAll();
    }

    $('form#tag_form').submit(function (event) {
        event.preventDefault();
        get_new_tags(true);
    });

    $('#researcher_dropdown').change(function (event) {
        var researcher_id = $(this).val();
        if (researcher_id != 'NONE') {
            var researcher_name = $('#researcher_dropdown option:selected').text();

            $('input#researcher_id').attr('value', researcher_id);

            $('#res_name').html(researcher_name);
            $('#res_name2').html(researcher_name);

            $('#researcher_selection_wrapper').css('display', 'none');
            $('#select_researcher_text').css('display', 'none');
            $('#greet_researcher').css('display', 'block');
            $('#canvas_wrapper').css('display', 'block');
            $('#verification_form_wrapper').css('display', 'block');

            get_new_tags(false);

            ff.window.renderAll();
        }
    });


});  // end $(document).ready()