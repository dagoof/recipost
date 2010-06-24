function imageinput(){
    // change this to input[class=new] and thing accordingly
    $('input[type=file]').live('change', function(){
        var name=['image', $('input[type=file]').length].join('');
        $('<input type="file">').attr('name',name).attr('id', name).insertAfter($('dd:last')).wrap('<dd/>');
    });
}

$(function(){
    imageinput();
});
