

$(document).ready(function() {
    $('.card').hover(
        function() {
            $(this).addClass('highlighted');
        },
        function() {
            $(this).removeClass('highlighted');
        }
    );
});
