$(document).ready(function() {
    // Check if the element exists before attaching the event listener
    if ($('#confirmSubmit').length > 0) {
        $('#confirmSubmit').on('click', function() {
            $('form').submit(); // Submit the form
        });
    }

    // Attaching click event listeners to all .dropdown-item elements, if any exist
    $('.dropdown-item').each(function() {
        $(this).on('click', function() {
            var filename = $(this).data('filename'); // Using jQuery's .data() method
            var downloadLink = $('#downloadLink');
            if(downloadLink.length > 0) {
                downloadLink.attr('href', `/download_plate/${filename}`);
            }
            var dropdownButton = $('#dropdownMenuButton');
            if(dropdownButton.length > 0) {
                dropdownButton.text($(this).text());
            }
        });
    });

    // Apply highlight effect to cards on hover
    $('.card').hover(
        function() {
            // Mouse enters the card area
            $(this).addClass('highlighted');
        },
        function() {
            // Mouse leaves the card area
            $(this).removeClass('highlighted');
        }
    );
});
