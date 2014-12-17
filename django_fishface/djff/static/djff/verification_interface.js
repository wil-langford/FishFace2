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

            this.tile_width = this.width / this.hor_tiles;
            this.tile_height = this.height / this.vert_tiles;
        },
        index_to_coords: function(tile_index) {
            var idx = {
                x: tile_index % this.hor_tiles,
                y: (tile_index - (tile_index % this.hor_tiles)) / this.hor_tiles
            };

            return {
                x: this.tile_width * idx.x + (this.tile_width / 2),
                y: this.tile_height * idx.y + (this.tile_height / 2)
            }
        },
        coords_to_index: function(point) {
            var idx = {
                x: (point.x - (point.x % this.tile_width)) / this.tile_width,
                y: (point.y - (point.y % this.tile_height)) / this.tile_height
            };

            return idx.y * this.hor_tiles + idx.x;
        },
        add_tile: function(tag, tile_index) {
            fabric.Image.fromURL(tag.url, this.image_added, {
                window: this,
                tag: tag,
                tile_index: tile_index
            });
        },
        image_added: function(img) {
            var wdw = img.window;
            
            wdw.add(img);
            wdw.tile[img.tile_index] = img;
            wdw.tile_data[img.tile_index] = img.data;
            var orig = img.getOriginalSize()

            if (!wdw.tile_scale_x) {
                wdw.tile_scale_x = (wdw.tile_width / orig.width) ;
                wdw.tile_scale_y = (wdw.tile_height / orig.height);
            }

            var tc = this.index_to_coords(img.tile_index);

            img.set({
                scaleX: wdw.tile_scale_x,
                scaleY: wdw.tile_scale_y,
                x: tc.x,
                y: tc.y
            });

            img.setCoords();
            wdw.calcOffset();
        },
        replace_tile: function(url, data, tile_index) {
            fabric.Image.fromURL(url, this.image_replaced, {
                window: this,
                data: data,
                tile_index: tile_index
            });
        },
        image_replaced: function(img) {
            var wdw = img.window;
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

    ff.window.on('mouse:down', function(options) {
        var pointer = ff.window.getPointer(options.e);
        var point = new fabric.Point(pointer.x, pointer.y);
        var tile_index = ff.window.coords_to_index(point);
        ff.DOWN_MOUSE_TILE_INDEX = tile_index;
    });

    ff.window.on('mouse:up', function(options) {
        var pointer = ff.window.getPointer(options.e);
        var point = new fabric.Point(pointer.x, pointer.y);
        var tile_index = ff.window.coords_to_index(point);
        if (tile_index == ff.DOWN_MOUSE_TILE_INDEX) {
            // TODO: implement the red flag toggling
            alert("Not yet implemented.")
        }
        ff.window.renderAll();
        ff.window.calcOffset();
    });


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

                    for (var tile_index in data.verify_these) {
                        ff.window.replace_tile(data.verify_these[tile_index], tile_index);
                    }
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

    for (var i = 0; i < (ff.window.hor_tiles * ff.window.vert_tiles); i++) {
        ff.window.add_tile({
            id: 'NONE',
            url: '/static/djff/sample-CAL.jpg',
            rotate_angle: 0,
            start: '0,0',
            end: '0,0'
        }, i);
    }

    fabric.

    ff.window.set({
        backgroundColor: 'white'
    });
    ff.window.renderAll();
    ff.window.calcOffset();

});  // end $(document).ready()