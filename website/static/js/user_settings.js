


$(document).ready(function() {
    // Apply hover effect to cards
    $('.card').hover(
        function() {
            $(this).addClass('highlighted');
        }, 
        function() {
            $(this).removeClass('highlighted');
        }
    );
});