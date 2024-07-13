


$(document).ready(function() {
    // Hover effect for card
    $('.card').hover(
        function() {
            // Mouse enters the card area
            $(this).addClass('highlighted');
            $(this).find('svg').css('transform', 'scale(1.5)');
        },
        function() {
            // Mouse leaves the card area
            $(this).removeClass('highlighted');
            $(this).find('svg').css('transform', 'scale(1)');
        }
    );
});

